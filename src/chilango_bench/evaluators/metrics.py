"""Aggregate metrics for an evaluation run, with bootstrap confidence intervals."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from chilango_bench.evaluators.base import EvaluationResult

UNRESOLVED = "UNRESOLVED"
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 20261026


class Score(BaseModel):
    """Accuracy over `n` graded items with a 95 % percentile-bootstrap interval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    accuracy: float
    ci_low: float
    ci_high: float
    n: int


class BenchmarkMetrics(BaseModel):
    """Accuracy over graded items; items with a runner or judge error are counted apart."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_items: int
    graded_items: int
    correct_items: int
    errored_items: int
    unresolved_items: int
    """Multiple-choice answers that did not commit to an option (graded as wrong)."""
    overall: Score
    categories: dict[str, Score]
    eval_types: dict[str, Score]
    average_score: float
    total_latency_seconds: float
    mean_latency_seconds: float
    total_prompt_tokens: int
    total_completion_tokens: int

    @property
    def accuracy(self) -> float:
        return self.overall.accuracy


def bootstrap_score(outcomes: Sequence[bool], *, seed: int = BOOTSTRAP_SEED) -> Score:
    """Accuracy and a 95 % percentile-bootstrap interval, reproducible through `seed`."""
    n = len(outcomes)
    if n == 0:
        return Score(accuracy=0.0, ci_low=0.0, ci_high=0.0, n=0)
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(outcomes, k=n)) / n for _ in range(BOOTSTRAP_RESAMPLES))
    low = means[int(0.025 * BOOTSTRAP_RESAMPLES)]
    high = means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return Score(
        accuracy=round(sum(outcomes) / n, 4), ci_low=round(low, 4), ci_high=round(high, 4), n=n
    )


def aggregate_metrics(results: list[EvaluationResult]) -> BenchmarkMetrics:
    graded = [r for r in results if r.error is None]
    latency = sum(r.latency_seconds for r in results)
    return BenchmarkMetrics(
        total_items=len(results),
        graded_items=len(graded),
        correct_items=sum(r.is_correct for r in graded),
        errored_items=len(results) - len(graded),
        unresolved_items=sum(r.metadata.get("extracted_choice") == UNRESOLVED for r in graded),
        overall=bootstrap_score([r.is_correct for r in graded]),
        categories=_scores_by(graded, lambda r: r.category.value),
        eval_types=_scores_by(graded, lambda r: r.eval_type.value),
        average_score=round(sum(r.score for r in graded) / len(graded), 4) if graded else 0.0,
        total_latency_seconds=round(latency, 3),
        mean_latency_seconds=round(latency / len(results), 3) if results else 0.0,
        total_prompt_tokens=sum(r.prompt_tokens for r in results),
        total_completion_tokens=sum(r.completion_tokens for r in results),
    )


def _scores_by(
    results: list[EvaluationResult], key: Callable[[EvaluationResult], str]
) -> dict[str, Score]:
    groups: dict[str, list[bool]] = defaultdict(list)
    for result in results:
        groups[key(result)].append(result.is_correct)
    return {group: bootstrap_score(groups[group]) for group in sorted(groups)}
