"""Markdown leaderboard built from committed run reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from chilango_bench.dataset.models import Category
from chilango_bench.reporting.models import ReportError, RunReport

if TYPE_CHECKING:
    from chilango_bench.evaluators.metrics import Score

CATEGORY_LABELS = {
    Category.SLANG: "Slang",
    Category.CULTURAL_CONTEXT: "Culture",
    Category.PROCEDURES: "Procedures",
    Category.ALBUR: "Albur",
}


@dataclass(frozen=True)
class LoadedReports:
    reports: list[RunReport]
    invalid: list[ReportError]


def load_reports(directory: str | Path) -> LoadedReports:
    """Load every `*.json` report; invalid files are returned, never silently dropped."""
    folder = Path(directory)
    if not folder.is_dir():
        raise ReportError(f"results directory not found: {folder}")
    reports: list[RunReport] = []
    invalid: list[ReportError] = []
    for path in sorted(folder.glob("*.json")):
        try:
            reports.append(RunReport.load(path))
        except ReportError as exc:
            invalid.append(exc)
    return LoadedReports(reports, invalid)


def leaderboard_markdown(reports: list[RunReport]) -> str:
    """One ranked table per group of comparable runs (same dataset hash and prompt template)."""
    if not reports:
        return "_No benchmark runs found._\n"
    groups: dict[tuple[str, int, str, str | None], list[RunReport]] = defaultdict(list)
    for report in reports:
        groups[report.comparability_key].append(report)
    ordered = sorted(groups.values(), key=lambda g: max(r.created_at for r in g), reverse=True)
    return "\n".join(_table(group) for group in ordered)


def _table(reports: list[RunReport]) -> str:
    first = reports[0]
    ranked = sorted(reports, key=lambda r: (r.metrics.accuracy, r.model), reverse=True)
    categories = [c for c in Category if any(c.value in r.metrics.categories for r in reports)]
    header = ["Rank", "Model", "Accuracy (95% CI)", *(CATEGORY_LABELS[c] for c in categories)]
    header += ["Unresolved", "Errors", "Items"]
    lines = [
        f"Dataset `{first.dataset.path}` (sha256 `{first.dataset.sha256[:12]}`), "
        f"prompt template `{first.settings.prompt_template}`",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---:", ":---", *["---:"] * (len(header) - 2)]) + "|",
    ]
    for rank, report in enumerate(ranked, start=1):
        metrics = report.metrics
        cells = [
            str(rank),
            f"`{report.model}`",
            _score(metrics.overall, interval=True),
            *(_score(metrics.categories.get(c.value)) for c in categories),
            str(metrics.unresolved_items),
            str(metrics.errored_items),
            str(metrics.graded_items),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _score(score: Score | None, *, interval: bool = False) -> str:
    if score is None or score.n == 0:
        return "—"
    text = f"{score.accuracy:.1%}"
    if interval:
        text += f" ({score.ci_low:.0%}-{score.ci_high:.0%})"
    return text
