"""Grading result model and evaluator interface."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from chilango_bench.dataset.models import BenchmarkItem, Category, EvaluationType


class EvaluationResult(BaseModel):
    """Outcome of grading one benchmark item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    category: Category
    eval_type: EvaluationType
    score: float = Field(ge=0.0, le=1.0)
    is_correct: bool
    model_response: str
    target: str | list[str]
    latency_seconds: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: str | None = None
    """Set when the item could not be graded (runner or judge failure); excluded from accuracy."""
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class BaseEvaluator(ABC):
    """Grades a candidate model's response to one item."""

    @abstractmethod
    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult: ...
