import json
from pathlib import Path

import httpx
import pytest
import respx

from chilango_bench.cli import main

SEED = "datasets/v1/chilango-bench.jsonl"


def test_requires_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main([])
    assert "COMMAND" in capsys.readouterr().err


def test_validate_success(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", SEED]) == 0
    out = capsys.readouterr().out
    assert "168 valid items" in out
    assert "longest in 25%" in out


def test_validate_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"bad": "data"}\n', encoding="utf-8")

    assert main(["validate", str(bad)]) == 1
    assert "invalid" in capsys.readouterr().err


def test_eval_mock_writes_a_reproducible_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "mock.json"

    assert main(["eval", "-d", SEED, "-m", "mock", "-p", "mock", "-o", str(out)]) == 0

    report = json.loads(out.read_text(encoding="utf-8"))
    assert len(report["dataset"]["sha256"]) == 64
    assert report["settings"]["prompt_template"] == "es-v1"
    assert report["metrics"]["eval_types"]["multiple_choice"]["accuracy"] == 0.2537
    captured = capsys.readouterr()
    assert "skipping 11 rubric item(s)" in captured.err
    assert "[157/157]" in captured.err


def test_eval_limit(tmp_path: Path) -> None:
    out = tmp_path / "small.json"

    assert main(["eval", "-d", SEED, "-m", "m", "-p", "mock", "--limit", "5", "-o", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["dataset"]["items"] == 5


@respx.mock
def test_eval_against_ollama_records_runner_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHILANGO_MAX_RETRIES", "0")
    calls = {"n": 0}

    def reply(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 2:
            return httpx.Response(400, text="bad request")
        return httpx.Response(200, json={"choices": [{"message": {"content": "A"}}]})

    respx.post("http://localhost:11434/v1/chat/completions").mock(side_effect=reply)
    out = tmp_path / "ollama.json"

    code = main(["eval", "-d", SEED, "-m", "qwen", "-p", "ollama", "--limit", "3", "-o", str(out)])

    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["settings"]["base_url"] == "http://localhost:11434/v1"
    assert report["metrics"]["errored_items"] == 1
    assert report["metrics"]["graded_items"] == 2


def test_eval_missing_dataset(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", "-d", "nope.jsonl", "-m", "m", "-p", "mock"]) == 1
    assert "error:" in capsys.readouterr().err


def test_leaderboard(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["eval", "-d", SEED, "-m", "mock-a", "-p", "mock", "-o", str(tmp_path / "a.json")])
    capsys.readouterr()

    assert main(["leaderboard", "-r", str(tmp_path)]) == 0
    assert "`mock-a`" in capsys.readouterr().out


def test_leaderboard_reports_invalid_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "broken.json").write_text("{}", encoding="utf-8")

    assert main(["leaderboard", "-r", str(tmp_path)]) == 1
    assert "skipped:" in capsys.readouterr().err


def test_leaderboard_missing_dir(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["leaderboard", "-r", "no_such_dir"]) == 1
    assert "not found" in capsys.readouterr().err
