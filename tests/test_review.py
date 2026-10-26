import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from chilango_bench.cli import main
from chilango_bench.dataset.review import review_dataset

ITEM = {
    "id": "slang-x{n}",
    "category": "slang",
    "eval_type": "multiple_choice",
    "prompt": "¿Qué significa 'chido'?",
    "choices": {"A": "Bueno", "B": "Malo"},
    "target": "A",
    "explanation": "'Chido' es bueno.",
}


def dataset(tmp_path: Path, n: int = 3) -> Path:
    path = tmp_path / "d.jsonl"
    rows = ["# canary line"] + [json.dumps({**ITEM, "id": f"slang-x{i}"}) for i in range(n)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def answers(*replies: str) -> Iterator[str]:
    return iter(replies)


def test_review_records_decisions_and_keeps_comments(tmp_path: Path) -> None:
    path = dataset(tmp_path)
    replies = answers("a", "r", "falso", "s")
    shown: list[str] = []

    summary = review_dataset(path, "diego", ask=lambda _: next(replies), say=shown.append)

    assert (summary.accepted, summary.rejected, summary.skipped, summary.remaining) == (1, 1, 1, 1)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# canary line"
    first, second, third = (json.loads(line) for line in lines[1:])
    assert first["review_status"] == "accepted"
    assert first["metadata"]["reviewer"] == "diego"
    assert second["review_status"] == "rejected"
    assert second["metadata"]["rejection_reason"] == "falso"
    assert "review_status" not in third or third["review_status"] == "unreviewed"
    assert "→ A) Bueno" in shown[0]
    assert "why: 'Chido' es bueno." in shown[0]


def test_quit_keeps_progress_and_reprompts_on_bad_input(tmp_path: Path) -> None:
    path = dataset(tmp_path)
    replies = answers("x", "a", "q")

    summary = review_dataset(path, "d", ask=lambda _: next(replies), say=lambda _: None)

    assert summary.accepted == 1
    assert summary.remaining == 2


def test_rejected_items_are_not_evaluated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = dataset(tmp_path)
    replies = answers("r", "", "a", "a")
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    assert main(["review", str(path), "--reviewer", "d"]) == 0
    out = tmp_path / "run.json"

    assert main(["eval", "-d", str(path), "-m", "m", "-p", "mock", "-o", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["dataset"]["items"] == 2


def test_accepted_only(tmp_path: Path) -> None:
    path = dataset(tmp_path)
    replies = answers("a", "q")
    review_dataset(path, "d", ask=lambda _: next(replies), say=lambda _: None)
    out = tmp_path / "run.json"

    assert (
        main(["eval", "-d", str(path), "-m", "m", "-p", "mock", "--accepted-only", "-o", str(out)])
        == 0
    )
    assert json.loads(out.read_text(encoding="utf-8"))["dataset"]["items"] == 1
