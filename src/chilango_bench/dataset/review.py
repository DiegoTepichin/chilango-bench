"""Interactive review of dataset items, written back to the JSONL file after every decision."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from chilango_bench.core.exceptions import DatasetError
from chilango_bench.dataset.models import BenchmarkItem, ReviewStatus

Ask = Callable[[str], str]
Say = Callable[[str], None]

DECISIONS = {"a": ReviewStatus.ACCEPTED, "r": ReviewStatus.REJECTED}


@dataclass(frozen=True)
class ReviewSummary:
    accepted: int
    rejected: int
    skipped: int
    remaining: int


def review_dataset(
    path: str | Path, reviewer: str, ask: Ask | None = None, say: Say | None = None
) -> ReviewSummary:
    """Walk unreviewed items; `a` accepts, `r` rejects (with a reason), `s` skips, `q` quits."""
    prompt: Ask = input if ask is None else ask
    show: Say = print if say is None else say
    file = Path(path)
    if not file.is_file():
        raise DatasetError(f"dataset file does not exist: {file}")
    lines = file.read_text(encoding="utf-8").splitlines()
    pending = [i for i, line in enumerate(lines) if _is_unreviewed(line)]
    counts = {"accepted": 0, "rejected": 0, "skipped": 0}
    for position, index in enumerate(pending, start=1):
        item = BenchmarkItem.model_validate_json(lines[index])
        show(_render(item, position, len(pending)))
        answer = _ask_decision(prompt)
        if answer == "q":
            break
        if answer == "s":
            counts["skipped"] += 1
            continue
        metadata = dict(item.metadata, reviewer=reviewer)
        if answer == "r":
            metadata["rejection_reason"] = prompt("reason: ").strip() or "unspecified"
        updated = item.model_copy(update={"review_status": DECISIONS[answer], "metadata": metadata})
        lines[index] = updated.model_dump_json(exclude_none=True)
        file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts["accepted" if answer == "a" else "rejected"] += 1
    remaining = sum(_is_unreviewed(line) for line in lines)
    return ReviewSummary(counts["accepted"], counts["rejected"], counts["skipped"], remaining)


def _is_unreviewed(line: str) -> bool:
    if not line.strip() or line.lstrip().startswith("#"):
        return False
    status = json.loads(line).get("review_status", ReviewStatus.UNREVIEWED.value)
    return bool(status == ReviewStatus.UNREVIEWED.value)


def _ask_decision(ask: Ask) -> str:
    while True:
        answer = ask("[a]ccept, [r]eject, [s]kip, [q]uit: ").strip().lower()[:1]
        if answer in {"a", "r", "s", "q"}:
            return answer


def _render(item: BenchmarkItem, position: int, total: int) -> str:
    lines = [
        "",
        f"── {position}/{total} · {item.id} · {item.category.value} · {item.eval_type.value}",
        item.prompt,
    ]
    if item.choices:
        lines.extend(
            f"  {'→' if key == item.target else ' '} {key}) {text}"
            for key, text in item.choices.items()
        )
    else:
        lines.append(f"  target: {item.target}")
    if item.rubric:
        lines.extend(f"  rubric · {c.name}: {c.description}" for c in item.rubric)
    if item.explanation:
        lines.append(f"  why: {item.explanation}")
    return "\n".join(lines)
