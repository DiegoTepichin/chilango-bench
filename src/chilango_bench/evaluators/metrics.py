"""Aggregate metrics for an evaluation run."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from chilango_bench.evaluators.base import EvaluationResult

UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class BenchmarkMetrics:
    """Accuracy over graded items; items with a runner or judge error are counted apart."""

    total_items: int
    graded_items: int
    correct_items: int
    errored_items: int
    unresolved_items: int
    """Multiple-choice answers that did not commit to an option (graded as wrong)."""
    accuracy: float
    average_score: float
    category_scores: dict[str, float]
    eval_type_scores: dict[str, float]
    total_latency_seconds: float
    mean_latency_seconds: float
    total_prompt_tokens: int
    total_completion_tokens: int


def aggregate_metrics(results: list[EvaluationResult]) -> BenchmarkMetrics:
    graded = [r for r in results if r.error is None]
    correct = sum(r.is_correct for r in graded)
    latency = sum(r.latency_seconds for r in results)
    return BenchmarkMetrics(
        total_items=len(results),
        graded_items=len(graded),
        correct_items=correct,
        errored_items=len(results) - len(graded),
        unresolved_items=sum(r.metadata.get("extracted_choice") == UNRESOLVED for r in graded),
        accuracy=_ratio(correct, len(graded)),
        average_score=_ratio(sum(r.score for r in graded), len(graded)),
        category_scores=_accuracy_by(graded, lambda r: r.category.value),
        eval_type_scores=_accuracy_by(graded, lambda r: r.eval_type.value),
        total_latency_seconds=round(latency, 3),
        mean_latency_seconds=round(latency / len(results), 3) if results else 0.0,
        total_prompt_tokens=sum(r.prompt_tokens for r in results),
        total_completion_tokens=sum(r.completion_tokens for r in results),
    )


def _ratio(numerator: float, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _accuracy_by(
    results: list[EvaluationResult], key: Callable[[EvaluationResult], str]
) -> dict[str, float]:
    totals: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    for result in results:
        totals[key(result)] += 1
        correct[key(result)] += result.is_correct
    return {group: _ratio(correct[group], totals[group]) for group in sorted(totals)}
