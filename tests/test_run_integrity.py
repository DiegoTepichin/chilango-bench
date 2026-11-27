from pathlib import Path

import httpx
import pytest
import respx

from chilango_bench.cli import main
from chilango_bench.core.exceptions import RunnerError
from chilango_bench.dataset.review import review_dataset
from chilango_bench.runners.openai import OpenAIRunner

SEED = "datasets/v1/chilango-bench.jsonl"


def _runner(response: httpx.Response) -> OpenAIRunner:
    transport = httpx.MockTransport(lambda _: response)
    client = httpx.Client(base_url="http://model.test/v1", transport=transport)
    return OpenAIRunner("m", base_url="http://model.test/v1", max_retries=0, client=client)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>Sign in</html>"),
        httpx.Response(200, json=[1]),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": ["A"]}),
        httpx.Response(200, json={"choices": [{}]}),
        httpx.Response(200, json={"choices": [{"message": None}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": [1]}}]}),
    ],
)
def test_malformed_responses_are_runner_errors(response: httpx.Response) -> None:
    with pytest.raises(RunnerError, match="Unexpected response format"):
        _runner(response).generate("hola")


@pytest.mark.parametrize("usage", [None, [], {"prompt_tokens": None, "completion_tokens": "x"}])
def test_unusable_token_counts_are_zero(usage: object) -> None:
    body = {"choices": [{"message": {"content": "A"}}], "usage": usage}

    result = _runner(httpx.Response(200, json=body)).generate("hola")

    assert (result.text, result.prompt_tokens, result.completion_tokens) == ("A", 0, 0)


@respx.mock
def test_a_run_with_no_graded_items_fails_and_writes_no_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CHILANGO_MAX_RETRIES", "0")
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    output = tmp_path / "down.json"

    code = main(["eval", "-d", SEED, "-m", "m", "-p", "ollama", "--limit", "3", "-o", str(output)])

    captured = capsys.readouterr()
    assert code == 1
    assert not output.exists()
    assert "no item could be graded" in captured.err
    assert "connection refused" in captured.err
    assert "accuracy" not in captured.out


@pytest.mark.parametrize("limit", ["0", "-5", "many"])
def test_limit_must_be_a_positive_number(limit: str) -> None:
    with pytest.raises(SystemExit):
        main(["eval", "-d", SEED, "-m", "m", "-p", "mock", "--limit", limit])


def test_a_selection_with_no_items_fails_before_calling_the_model(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["eval", "-d", SEED, "-m", "m", "-p", "mock", "--accepted-only"]) == 1
    assert "no items to evaluate" in capsys.readouterr().err


def test_an_unwritable_report_path_fails_before_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("")
    output = blocker / "report.json"

    assert main(["eval", "-d", SEED, "-m", "m", "-p", "mock", "-o", str(output)]) == 1
    err = capsys.readouterr().err
    assert "cannot write the report" in err
    assert "[1/" not in err


@pytest.mark.parametrize(
    "command",
    [
        ["validate", "{file}"],
        ["eval", "-d", "{file}", "-m", "m", "-p", "mock"],
        ["review", "{file}", "--reviewer", "someone"],
    ],
)
def test_a_dataset_that_is_not_utf8_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], command: list[str]
) -> None:
    dataset = tmp_path / "binary.jsonl"
    dataset.write_bytes(b"\xff\xfe junk")

    assert main([part.format(file=dataset) for part in command]) == 1
    assert "UTF-8" in capsys.readouterr().err


def test_review_reports_a_broken_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dataset = tmp_path / "broken.jsonl"
    dataset.write_text("{nope\n", encoding="utf-8")

    assert main(["review", str(dataset), "--reviewer", "someone"]) == 1
    assert "line 1" in capsys.readouterr().err


def test_leaderboard_reports_a_report_that_is_not_utf8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "binary.json").write_bytes(b"\xff\xfe")

    assert main(["leaderboard", "-r", str(tmp_path)]) == 1
    assert "skipped:" in capsys.readouterr().err


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, EOFError])
def test_interrupting_a_review_keeps_earlier_decisions(
    tmp_path: Path, interruption: type[BaseException]
) -> None:
    dataset = tmp_path / "data.jsonl"
    lines = [
        line for line in Path(SEED).read_text(encoding="utf-8").splitlines() if line[:1] == "{"
    ]
    dataset.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    answers = iter(["a"])

    def ask(_: str) -> str:
        try:
            return next(answers)
        except StopIteration:
            raise interruption from None

    summary = review_dataset(dataset, "someone", ask=ask, say=lambda _: None)

    assert (summary.accepted, summary.remaining) == (1, 1)
    assert list(tmp_path.iterdir()) == [dataset]
