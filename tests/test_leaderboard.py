"""Unit tests for report persistence and leaderboard generation."""

from pathlib import Path

from chilango_bench.dataset.models import Category, EvaluationType
from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.metrics import BenchmarkMetrics
from chilango_bench.reporting.leaderboard import (
    generate_leaderboard_markdown,
    load_reports_from_directory,
    load_run_report,
    save_run_report,
)
from chilango_bench.reporting.models import BenchmarkRunReport


def test_save_and_load_run_report(tmp_path: Path) -> None:
    """Ensure benchmark run reports serialize and deserialize cleanly."""
    metrics = BenchmarkMetrics(
        total_items=2,
        correct_items=2,
        accuracy=1.0,
        average_score=1.0,
        category_scores={"slang": 1.0},
        eval_type_scores={"multiple_choice": 1.0},
        total_latency_seconds=0.2,
        mean_latency_seconds=0.1,
        total_prompt_tokens=20,
        total_completion_tokens=4,
    )
    result = EvaluationResult(
        item_id="item-1",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        score=1.0,
        is_correct=True,
        model_response="B",
        target="B",
    )
    report = BenchmarkRunReport(
        benchmark_version="0.1.0",
        model_name="mock-model",
        timestamp_utc="2026-10-08T00:00:00Z",
        dataset_path="datasets/v0.1/seed.jsonl",
        metrics=metrics,
        results=[result],
    )

    report_file = tmp_path / "report.json"
    save_run_report(report, report_file)
    assert report_file.exists()

    loaded = load_run_report(report_file)
    assert loaded.model_name == "mock-model"
    assert loaded.metrics.accuracy == 1.0
    assert len(loaded.results) == 1
    assert loaded.results[0].item_id == "item-1"


def test_generate_leaderboard_markdown(tmp_path: Path) -> None:
    """Ensure leaderboard Markdown table formats and sorts properly."""
    m1 = BenchmarkMetrics(
        total_items=10,
        correct_items=9,
        accuracy=0.90,
        average_score=0.90,
        category_scores={"slang": 1.0, "cultural_context": 0.8},
        eval_type_scores={"multiple_choice": 0.90},
        total_latency_seconds=1.0,
        mean_latency_seconds=0.1,
        total_prompt_tokens=100,
        total_completion_tokens=20,
    )
    r1 = BenchmarkRunReport("0.1.0", "model-alpha", "2026-10-08", "seed.jsonl", m1, [])

    m2 = BenchmarkMetrics(
        total_items=10,
        correct_items=6,
        accuracy=0.60,
        average_score=0.60,
        category_scores={"slang": 0.5, "cultural_context": 0.7},
        eval_type_scores={"multiple_choice": 0.60},
        total_latency_seconds=2.0,
        mean_latency_seconds=0.2,
        total_prompt_tokens=100,
        total_completion_tokens=20,
    )
    r2 = BenchmarkRunReport("0.1.0", "model-beta", "2026-10-08", "seed.jsonl", m2, [])

    # Empty report list
    empty_md = generate_leaderboard_markdown([])
    assert "No benchmark runs found" in empty_md

    # Reports table
    table = generate_leaderboard_markdown([r2, r1])
    assert "| Rank | Model | Overall Acc |" in table
    # model-alpha (90%) should rank #1 ahead of model-beta (60%)
    lines = [line for line in table.splitlines() if line.startswith("| **")]
    assert len(lines) == 2
    assert "model-alpha" in lines[0]
    assert "model-beta" in lines[1]


def test_load_reports_from_directory(tmp_path: Path) -> None:
    """Ensure valid reports in directory are discovered and parsed."""
    m = BenchmarkMetrics(1, 1, 1.0, 1.0, {}, {}, 0.1, 0.1, 1, 1)
    r = BenchmarkRunReport("0.1.0", "m1", "now", "path", m, [])
    save_run_report(r, tmp_path / "r1.json")

    # Add a non-report json file to verify resilience
    (tmp_path / "junk.json").write_text('{"bad": "json"}', encoding="utf-8")

    reports = load_reports_from_directory(tmp_path)
    assert len(reports) == 1
    assert reports[0].model_name == "m1"
