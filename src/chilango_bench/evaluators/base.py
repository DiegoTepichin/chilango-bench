"""Base models and interfaces for evaluation and grading."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from chilango_bench.dataset.models import BenchmarkItem, Category, EvaluationType


@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of grading a single benchmark item."""

    item_id: str
    category: Category
    eval_type: EvaluationType
    score: float  # Normalized score from 0.0 to 1.0
    is_correct: bool
    model_response: str
    target: str | list[str]
    latency_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None
    """Set when the item could not be graded (runner or judge failure); excluded from accuracy."""
    metadata: dict[str, object] = field(default_factory=dict)


class BaseEvaluator(ABC):
    """Abstract interface for grading candidate outputs."""

    @abstractmethod
    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult:
        """Grade a model's textual response against the benchmark item target.

        Args:
            item: The benchmark question item.
            response_text: The candidate model's raw completion output.

        Returns:
            EvaluationResult containing the computed score and grading details.
        """
