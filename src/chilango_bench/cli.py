"""Command-line interface for chilango-bench."""

import argparse
import datetime
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from chilango_bench import __version__
from chilango_bench.core.exceptions import ChilangoBenchError
from chilango_bench.dataset.loader import file_sha256, load_dataset
from chilango_bench.dataset.validator import validate_dataset_file
from chilango_bench.evaluators.engine import PROMPT_TEMPLATE, EvaluationEngine
from chilango_bench.reporting.leaderboard import leaderboard_markdown, load_reports
from chilango_bench.reporting.models import DatasetInfo, RunReport, RunSettings
from chilango_bench.runners.factory import create_runner

if TYPE_CHECKING:
    from chilango_bench.runners.base import BaseRunner


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="chilango-bench",
        description="Benchmark large language models on Mexican Spanish dialect and nuances.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Command: validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate integrity and schema of a benchmark JSONL dataset."
    )
    validate_parser.add_argument("dataset", help="Path to JSONL dataset file")

    # Command: eval
    eval_parser = subparsers.add_parser(
        "eval", help="Run benchmark evaluation against a target model."
    )
    eval_parser.add_argument(
        "-d", "--dataset", required=True, help="Path to evaluation dataset JSONL file"
    )
    eval_parser.add_argument(
        "-m",
        "--model",
        required=True,
        help="Target model identifier (e.g. gpt-4o-mini, mock-model)",
    )
    eval_parser.add_argument(
        "-p", "--provider", default="auto", help="Provider adapter ('openai', 'mock', 'auto')"
    )
    eval_parser.add_argument(
        "-j", "--judge", default=None, help="Optional judge model for rubric evaluations"
    )
    eval_parser.add_argument(
        "-o", "--output", default=None, help="Destination JSON path for run report bundle"
    )

    # Command: leaderboard
    lb_parser = subparsers.add_parser(
        "leaderboard", help="Generate Markdown leaderboard from a directory of run reports."
    )
    lb_parser.add_argument(
        "-r",
        "--results-dir",
        default="results",
        help="Directory containing benchmark JSON reports (default: results/)",
    )

    return parser


def run_validate(dataset_path: str) -> int:
    """Handle 'validate' subcommand."""
    sys.stdout.write(f"Validating dataset: {dataset_path}\n")
    report = validate_dataset_file(dataset_path)

    if not report.is_valid:
        sys.stderr.write(f"❌ Validation failed: {report.error_message}\n")
        return 1

    sys.stdout.write(f"✅ Dataset is valid! Total items: {report.total_items}\n")
    sys.stdout.write("Distribution by Category:\n")
    for cat, count in sorted(report.category_counts.items()):
        sys.stdout.write(f"  - {cat}: {count}\n")
    sys.stdout.write("Distribution by Evaluation Type:\n")
    for et, count in sorted(report.eval_type_counts.items()):
        sys.stdout.write(f"  - {et}: {count}\n")
    return 0


def run_eval(
    dataset_path: str,
    model: str,
    provider: str,
    judge_model: str | None,
    output_path: str | None,
) -> int:
    """Handle 'eval' subcommand."""
    sys.stdout.write(f"Running chilango-bench on model: {model} (provider: {provider})\n")
    items = load_dataset(dataset_path)
    sys.stdout.write(f"Loaded {len(items)} items from {dataset_path}\n")

    runner = create_runner(model=model, provider=provider)
    judge_runner: BaseRunner | None = (
        create_runner(model=judge_model, provider="auto") if judge_model else None
    )

    engine = EvaluationEngine(runner=runner, judge_runner=judge_runner)
    results, metrics = engine.run_benchmark(items)

    sys.stdout.write("\n================ Benchmark Results ================\n")
    sys.stdout.write(f"Model: {model}\n")
    sys.stdout.write(
        f"Accuracy: {metrics.accuracy:.1%} ({metrics.correct_items}/{metrics.graded_items}), "
        f"95% CI {metrics.overall.ci_low:.0%}-{metrics.overall.ci_high:.0%}\n"
    )
    sys.stdout.write("Category Accuracy:\n")
    for cat, score in metrics.categories.items():
        sys.stdout.write(
            f"  - {cat}: {score.accuracy:.1%} ({score.ci_low:.0%}-{score.ci_high:.0%})\n"
        )
    sys.stdout.write(
        f"Mean Latency: {metrics.mean_latency_seconds:.3f}s "
        f"(Total: {metrics.total_latency_seconds:.3f}s)\n"
    )
    sys.stdout.write(
        f"Tokens: {metrics.total_prompt_tokens} prompt, "
        f"{metrics.total_completion_tokens} completion\n"
    )
    sys.stdout.write("===================================================\n")

    if output_path:
        report = RunReport(
            benchmark_version=__version__,
            model=model,
            created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
            dataset=DatasetInfo(
                path=Path(dataset_path).as_posix(),
                sha256=file_sha256(dataset_path),
                items=len(items),
            ),
            settings=RunSettings(
                provider=provider,
                base_url=getattr(runner, "base_url", None),
                temperature=0.0,
                max_tokens=512,
                prompt_template=PROMPT_TEMPLATE,
                judge_model=judge_model,
            ),
            metrics=metrics,
            results=results,
        )
        report.save(output_path)
        sys.stdout.write(f"Saved run report artifact to: {output_path}\n")

    return 0


def run_leaderboard(results_dir: str) -> int:
    """Handle 'leaderboard' subcommand."""
    loaded = load_reports(results_dir)
    for error in loaded.invalid:
        sys.stderr.write(f"skipped: {error}\n")
    sys.stdout.write(leaderboard_markdown(loaded.reports))
    return 1 if loaded.invalid else 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if not args.subcommand:
        parser.print_help()
        return 0

    try:
        if args.subcommand == "validate":
            return run_validate(args.dataset)
        if args.subcommand == "eval":
            return run_eval(
                dataset_path=args.dataset,
                model=args.model,
                provider=args.provider,
                judge_model=args.judge,
                output_path=args.output,
            )
        if args.subcommand == "leaderboard":
            return run_leaderboard(args.results_dir)
    except ChilangoBenchError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Unexpected error: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
