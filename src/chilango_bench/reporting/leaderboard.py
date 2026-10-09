"""Leaderboard generation and benchmark run persistence."""

import json
from pathlib import Path
from typing import Any

from chilango_bench.core.exceptions import ChilangoBenchError
from chilango_bench.dataset.models import Category, EvaluationType
from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.metrics import BenchmarkMetrics
from chilango_bench.reporting.models import BenchmarkRunReport


def save_run_report(report: BenchmarkRunReport, file_path: str | Path) -> None:
    """Serialize and save benchmark run report to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def load_run_report(file_path: str | Path) -> BenchmarkRunReport:
    """Read and deserialize a benchmark run report JSON file."""
    path = Path(file_path)
    if not path.is_file():
        raise ChilangoBenchError(f"Report file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ChilangoBenchError(f"Report {path} must contain a JSON object")

    if "metrics" not in data or "benchmark_version" not in data or "model_name" not in data:
        raise ChilangoBenchError(f"Report {path} is missing mandatory benchmark fields")

    metrics_raw: dict[str, Any] = data.get("metrics", {})
    metrics = BenchmarkMetrics(
        total_items=int(metrics_raw.get("total_items", 0)),
        correct_items=int(metrics_raw.get("correct_items", 0)),
        accuracy=float(metrics_raw.get("accuracy", 0.0)),
        average_score=float(metrics_raw.get("average_score", 0.0)),
        category_scores=dict(metrics_raw.get("category_scores", {})),
        eval_type_scores=dict(metrics_raw.get("eval_type_scores", {})),
        total_latency_seconds=float(metrics_raw.get("total_latency_seconds", 0.0)),
        mean_latency_seconds=float(metrics_raw.get("mean_latency_seconds", 0.0)),
        total_prompt_tokens=int(metrics_raw.get("total_prompt_tokens", 0)),
        total_completion_tokens=int(metrics_raw.get("total_completion_tokens", 0)),
    )

    results_raw = data.get("results", [])
    results: list[EvaluationResult] = []
    for r in results_raw:
        results.append(
            EvaluationResult(
                item_id=str(r.get("item_id", "")),
                category=Category(str(r.get("category", "slang"))),
                eval_type=EvaluationType(str(r.get("eval_type", "multiple_choice"))),
                score=float(r.get("score", 0.0)),
                is_correct=bool(r.get("is_correct", False)),
                model_response=str(r.get("model_response", "")),
                target=r.get("target", ""),
                latency_seconds=float(r.get("latency_seconds", 0.0)),
                prompt_tokens=int(r.get("prompt_tokens", 0)),
                completion_tokens=int(r.get("completion_tokens", 0)),
                metadata=dict(r.get("metadata", {})),
            )
        )

    return BenchmarkRunReport(
        benchmark_version=str(data.get("benchmark_version", "unknown")),
        model_name=str(data.get("model_name", "unknown")),
        timestamp_utc=str(data.get("timestamp_utc", "")),
        dataset_path=str(data.get("dataset_path", "")),
        metrics=metrics,
        results=results,
    )


def load_reports_from_directory(dir_path: str | Path) -> list[BenchmarkRunReport]:
    """Scan directory for all valid benchmark report JSON files."""
    path = Path(dir_path)
    if not path.is_dir():
        raise ChilangoBenchError(f"Directory not found: {path}")

    reports: list[BenchmarkRunReport] = []
    for json_file in sorted(path.glob("*.json")):
        try:
            report = load_run_report(json_file)
            reports.append(report)
        except Exception:
            continue
    return reports


def generate_leaderboard_markdown(reports: list[BenchmarkRunReport]) -> str:
    """Generate a GitHub-flavored Markdown leaderboard table sorted by accuracy."""
    if not reports:
        return "_No benchmark runs found to display in leaderboard._\n"

    # Sort primarily by accuracy descending, secondary by average_score descending
    sorted_reports = sorted(
        reports,
        key=lambda r: (r.metrics.accuracy, r.metrics.average_score),
        reverse=True,
    )

    lines: list[str] = [
        "# 🌮 chilango-bench: Leaderboard",
        "",
        "| Rank | Model | Overall Acc | Slang | Culture | Procedures | Albur | Latency (s) |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for rank, rep in enumerate(sorted_reports, start=1):
        m = rep.metrics
        slang_acc = m.category_scores.get(Category.SLANG.value, 0.0) * 100
        cult_acc = m.category_scores.get(Category.CULTURAL_CONTEXT.value, 0.0) * 100
        proc_acc = m.category_scores.get(Category.PROCEDURES.value, 0.0) * 100
        albur_acc = m.category_scores.get(Category.ALBUR.value, 0.0) * 100
        overall = m.accuracy * 100

        line = (
            f"| **{rank}** | `{rep.model_name}` | "
            f"**{overall:.1f}%** | {slang_acc:.1f}% | {cult_acc:.1f}% | "
            f"{proc_acc:.1f}% | {albur_acc:.1f}% | {m.mean_latency_seconds:.2f}s |"
        )
        lines.append(line)

    lines.append("")
    return "\n".join(lines)
