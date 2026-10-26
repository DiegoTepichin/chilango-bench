import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chilango_bench.dataset.models import Category, EvaluationType
from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.metrics import aggregate_metrics, bootstrap_score
from chilango_bench.reporting.leaderboard import leaderboard_markdown, load_reports
from chilango_bench.reporting.models import (
    DatasetInfo,
    ReportError,
    RunReport,
    RunSettings,
)


def result(item_id: str, correct: bool, category: Category = Category.SLANG) -> EvaluationResult:
    return EvaluationResult(
        item_id=item_id,
        category=category,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        score=float(correct),
        is_correct=correct,
        model_response="A",
        target="A" if correct else "B",
    )


def report(model: str, correct: int, total: int = 10, sha: str = "a" * 64) -> RunReport:
    results = [result(f"i{n}", n < correct) for n in range(total)]
    return RunReport(
        benchmark_version="1.0.0",
        model=model,
        created_at=datetime(2026, 10, 26, tzinfo=UTC),
        dataset=DatasetInfo(path="datasets/v1/x.jsonl", sha256=sha, items=total),
        settings=RunSettings(
            provider="mock",
            base_url=None,
            temperature=0.0,
            max_tokens=512,
            prompt_template="es-v1",
        ),
        metrics=aggregate_metrics(results),
        results=results,
    )


def test_bootstrap_interval_contains_the_accuracy_and_is_reproducible() -> None:
    outcomes = [True] * 30 + [False] * 70

    score = bootstrap_score(outcomes)

    assert score.accuracy == 0.3
    assert score.ci_low < 0.3 < score.ci_high
    assert 0.18 < score.ci_low < 0.25
    assert score == bootstrap_score(outcomes)


def test_bootstrap_of_nothing() -> None:
    assert bootstrap_score([]).n == 0


def test_metrics_have_scores_per_category() -> None:
    metrics = aggregate_metrics(
        [result("a", True), result("b", False, Category.ALBUR), result("c", True, Category.ALBUR)]
    )

    assert set(metrics.categories) == {"slang", "albur"}
    assert metrics.categories["albur"].accuracy == 0.5
    assert metrics.categories["albur"].n == 2


def test_report_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    original = report("m", 7)

    original.save(path)

    assert RunReport.load(path) == original


def test_invalid_report_has_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"model": "x"}), encoding="utf-8")

    with pytest.raises(ReportError, match=r"bad\.json is not a valid run report"):
        RunReport.load(path)


def test_load_reports_returns_invalid_files_instead_of_hiding_them(tmp_path: Path) -> None:
    report("m1", 5).save(tmp_path / "m1.json")
    (tmp_path / "junk.json").write_text("{}", encoding="utf-8")

    loaded = load_reports(tmp_path)

    assert [r.model for r in loaded.reports] == ["m1"]
    assert len(loaded.invalid) == 1
    assert "junk.json" in str(loaded.invalid[0])


def test_load_reports_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="not found"):
        load_reports(tmp_path / "nope")


def test_leaderboard_ranks_and_shows_intervals() -> None:
    table = leaderboard_markdown([report("weak", 4), report("strong", 9)])

    rows = [line for line in table.splitlines() if line.startswith("| 1") or line.startswith("| 2")]
    assert "`strong`" in rows[0]
    assert "`weak`" in rows[1]
    assert "90.0% (" in rows[0]
    assert "sha256 `aaaaaaaaaaaa`" in table


def test_leaderboard_never_ranks_runs_on_different_datasets_together() -> None:
    table = leaderboard_markdown([report("old", 9, sha="b" * 64), report("new", 5)])

    assert table.count("| Rank |") == 2


def test_leaderboard_empty() -> None:
    assert "No benchmark runs" in leaderboard_markdown([])
