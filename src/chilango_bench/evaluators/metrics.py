"""Metrics aggregation and statistical reporting for evaluation runs."""

from collections import defaultdict
from dataclasses import dataclass

from chilango_bench.evaluators.base import EvaluationResult


@dataclass(frozen=True)
class BenchmarkMetrics:
    """Aggregated performance metrics across benchmark items."""

    total_items: int
    correct_items: int
    accuracy: float
    average_score: float
    category_scores: dict[str, float]
    eval_type_scores: dict[str, float]
    total_latency_seconds: float
    mean_latency_seconds: float
    total_prompt_tokens: int
    total_completion_tokens: int


def aggregate_metrics(results: list[EvaluationResult]) -> BenchmarkMetrics:
    """Compute aggregate accuracy, category breakdowns, and performance metrics."""
    if not results:
        return BenchmarkMetrics(
            total_items=0,
            correct_items=0,
            accuracy=0.0,
            average_score=0.0,
            category_scores={},
            eval_type_scores={},
            total_latency_seconds=0.0,
            mean_latency_seconds=0.0,
            total_prompt_tokens=0,
            total_completion_tokens=0,
        )

    total_items = len(results)
    correct_items = sum(1 for r in results if r.is_correct)
    total_score = sum(r.score for r in results)

    cat_totals: dict[str, int] = defaultdict(int)
    cat_correct: dict[str, int] = defaultdict(int)

    type_totals: dict[str, int] = defaultdict(int)
    type_correct: dict[str, int] = defaultdict(int)

    total_latency = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for r in results:
        cat_key = r.category.value
        cat_totals[cat_key] += 1
        if r.is_correct:
            cat_correct[cat_key] += 1

        type_key = r.eval_type.value
        type_totals[type_key] += 1
        if r.is_correct:
            type_correct[type_key] += 1

        total_latency += r.latency_seconds
        total_prompt_tokens += r.prompt_tokens
        total_completion_tokens += r.completion_tokens

    category_scores = {cat: (cat_correct[cat] / cat_totals[cat]) for cat in cat_totals}
    eval_type_scores = {t: (type_correct[t] / type_totals[t]) for t in type_totals}

    return BenchmarkMetrics(
        total_items=total_items,
        correct_items=correct_items,
        accuracy=round(correct_items / total_items, 4),
        average_score=round(total_score / total_items, 4),
        category_scores={k: round(v, 4) for k, v in category_scores.items()},
        eval_type_scores={k: round(v, 4) for k, v in eval_type_scores.items()},
        total_latency_seconds=round(total_latency, 3),
        mean_latency_seconds=round(total_latency / total_items, 3),
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
    )
