"""`chilango-bench` command line."""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from chilango_bench import __version__
from chilango_bench.core.exceptions import ChilangoBenchError
from chilango_bench.dataset.loader import file_sha256, load_dataset
from chilango_bench.dataset.models import EvaluationType, ReviewStatus
from chilango_bench.dataset.review import review_dataset
from chilango_bench.dataset.validator import validate_dataset_file
from chilango_bench.evaluators.engine import PROMPT_TEMPLATE, EvaluationEngine, GenerationSettings
from chilango_bench.reporting.leaderboard import leaderboard_markdown, load_reports
from chilango_bench.reporting.models import DatasetInfo, RunReport, RunSettings
from chilango_bench.runners.factory import Provider, create_runner

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chilango_bench.dataset.models import BenchmarkItem
    from chilango_bench.evaluators.base import EvaluationResult
    from chilango_bench.evaluators.metrics import BenchmarkMetrics

EXIT_OK = 0
EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chilango-bench",
        description="Benchmark large language models on Mexican Spanish.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    validate = commands.add_parser("validate", help="check a dataset file against the schema")
    validate.add_argument("dataset", type=Path)

    run = commands.add_parser("eval", help="run a model on the benchmark")
    run.add_argument("-d", "--dataset", type=Path, required=True)
    run.add_argument("-m", "--model", required=True, help="model name as the provider knows it")
    run.add_argument(
        "-p", "--provider", choices=[p.value for p in Provider], default=Provider.OPENAI.value
    )
    run.add_argument("--base-url", help="override the endpoint of the openai or ollama provider")
    run.add_argument("-j", "--judge", help="judge model for rubric items (same provider)")
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--max-tokens", type=int, default=512)
    run.add_argument("--limit", type=int, help="evaluate only the first N items (smoke test)")
    run.add_argument("-o", "--output", type=Path, help="write the JSON run report here")

    run.add_argument(
        "--accepted-only", action="store_true", help="evaluate only items a reviewer accepted"
    )

    review = commands.add_parser("review", help="accept or reject unreviewed dataset items")
    review.add_argument("dataset", type=Path)
    review.add_argument("--reviewer", required=True, help="your name or GitHub handle")

    board = commands.add_parser("leaderboard", help="Markdown leaderboard from run reports")
    board.add_argument("-r", "--results-dir", type=Path, default=Path("results"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            return run_validate(args.dataset)
        if args.command == "eval":
            return run_eval(args)
        if args.command == "review":
            summary = review_dataset(args.dataset, args.reviewer)
            print(
                f"accepted {summary.accepted}, rejected {summary.rejected}, "
                f"skipped {summary.skipped}; {summary.remaining} still unreviewed"
            )
            return EXIT_OK
        return run_leaderboard(args.results_dir)
    except ChilangoBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILURE


def run_validate(dataset: Path) -> int:
    report = validate_dataset_file(dataset)
    if not report.is_valid:
        print(f"invalid: {report.error_message}", file=sys.stderr)
        return EXIT_FAILURE
    print(f"{dataset}: {report.total_items} valid items")
    breakdowns = (
        ("category", report.category_counts),
        ("type", report.eval_type_counts),
        ("review", report.review_counts),
    )
    for name, counts in breakdowns:
        print(f"  by {name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(
        f"  correct option is the longest in {report.longest_choice_rate:.0%} "
        f"and the shortest in {report.shortest_choice_rate:.0%} of multiple-choice items"
    )
    return EXIT_OK


def run_eval(args: argparse.Namespace) -> int:
    provider = Provider(args.provider)
    items = _select_items(
        load_dataset(args.dataset),
        judge=args.judge,
        limit=args.limit,
        accepted_only=args.accepted_only,
    )
    runner = create_runner(args.model, provider, args.base_url)
    judge = create_runner(args.judge, provider, args.base_url) if args.judge else None
    settings = GenerationSettings(temperature=args.temperature, max_tokens=args.max_tokens)
    engine = EvaluationEngine(runner, judge, settings)
    print(f"{args.model} ({provider.value}) on {len(items)} items", file=sys.stderr)
    results, metrics = engine.run_benchmark(items, _print_progress)
    print(_summary(args.model, metrics))
    if args.output:
        report = RunReport(
            benchmark_version=__version__,
            model=args.model,
            created_at=datetime.datetime.now(datetime.UTC).replace(microsecond=0),
            dataset=DatasetInfo(
                path=args.dataset.as_posix(), sha256=file_sha256(args.dataset), items=len(items)
            ),
            settings=RunSettings(
                provider=provider.value,
                base_url=getattr(runner, "base_url", None),
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                prompt_template=PROMPT_TEMPLATE,
                judge_model=args.judge,
            ),
            metrics=metrics,
            results=results,
        )
        report.save(args.output)
        print(f"wrote {args.output}", file=sys.stderr)
    return EXIT_OK


def run_leaderboard(results_dir: Path) -> int:
    loaded = load_reports(results_dir)
    for error in loaded.invalid:
        print(f"skipped: {error}", file=sys.stderr)
    print(leaderboard_markdown(loaded.reports), end="")
    return EXIT_FAILURE if loaded.invalid else EXIT_OK


def _select_items(
    items: list[BenchmarkItem], *, judge: str | None, limit: int | None, accepted_only: bool
) -> list[BenchmarkItem]:
    items = [item for item in items if item.review_status is not ReviewStatus.REJECTED]
    if accepted_only:
        items = [item for item in items if item.review_status is ReviewStatus.ACCEPTED]
    if judge is None:
        rubric = sum(item.eval_type is EvaluationType.RUBRIC_JUDGED for item in items)
        if rubric:
            print(f"skipping {rubric} rubric item(s): pass --judge to grade them", file=sys.stderr)
        items = [item for item in items if item.eval_type is not EvaluationType.RUBRIC_JUDGED]
    return items[:limit] if limit else items


def _print_progress(index: int, total: int, result: EvaluationResult) -> None:
    mark = "error" if result.error else ("ok" if result.is_correct else "wrong")
    print(f"[{index}/{total}] {result.item_id}: {mark}", file=sys.stderr)


def _summary(model: str, metrics: BenchmarkMetrics) -> str:
    overall = metrics.overall
    lines = [
        f"{model}: {overall.accuracy:.1%} accuracy "
        f"(95% CI {overall.ci_low:.1%}-{overall.ci_high:.1%}), "
        f"{metrics.correct_items}/{metrics.graded_items} correct",
        *(
            f"  {name}: {score.accuracy:.1%} ({score.ci_low:.0%}-{score.ci_high:.0%}, n={score.n})"
            for name, score in metrics.categories.items()
        ),
        f"  unresolved answers: {metrics.unresolved_items}, errors: {metrics.errored_items}, "
        f"mean latency: {metrics.mean_latency_seconds:.2f}s",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
