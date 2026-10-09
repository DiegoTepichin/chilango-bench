"""Data models and schemas for benchmark evaluation items."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Category(StrEnum):
    """Evaluation domain categories."""

    SLANG = "slang"
    CULTURAL_CONTEXT = "cultural_context"
    PROCEDURES = "procedures"
    ALBUR = "albur"


class EvaluationType(StrEnum):
    """Supported evaluation paradigms."""

    MULTIPLE_CHOICE = "multiple_choice"
    EXACT_MATCH = "exact_match"
    RUBRIC_JUDGED = "rubric_judged"


class RubricCriterion(BaseModel):
    """Criterion used for rubric-based LLM judge evaluations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1, description="Short name of criterion")
    description: str = Field(..., min_length=1, description="Scoring explanation and requirements")
    weight: float = Field(default=1.0, gt=0, description="Relative weight in final composite score")


class BenchmarkItem(BaseModel):
    """Schema representing an individual evaluation item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        ..., min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique identifier"
    )
    category: Category = Field(..., description="Evaluation category")
    eval_type: EvaluationType = Field(..., description="Evaluation paradigm")
    prompt: str = Field(..., min_length=1, description="Prompt given to the candidate model")
    system_prompt: str | None = Field(default=None, description="Optional system prompt")
    choices: dict[str, str] | None = Field(
        default=None,
        description="Options for multiple choice items (e.g. {'A': '...', 'B': '...'})",
    )
    target: str | list[str] = Field(
        ..., description="Canonical expected answer or list of acceptable ground truths"
    )
    rubric: list[RubricCriterion] | None = Field(
        default=None, description="Criteria for rubric judged items"
    )
    metadata: dict[str, str | int | float | bool] = Field(
        default_factory=dict, description="Arbitrary metadata such as difficulty, source, or notes"
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt_not_blank(cls, value: str) -> str:
        """Ensure prompt is not purely whitespace."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Prompt cannot be empty or purely whitespace")
        return stripped

    @model_validator(mode="after")
    def validate_eval_type_consistency(self) -> Self:
        """Enforce relational integrity between evaluation type and required fields."""
        if self.eval_type == EvaluationType.MULTIPLE_CHOICE:
            if not self.choices or len(self.choices) < 2:
                raise ValueError(
                    "Multiple choice items must provide at least 2 choices in 'choices'"
                )
            if not isinstance(self.target, str):
                raise ValueError(
                    "Multiple choice target must be a single choice key string (e.g. 'A')"
                )
            if self.target not in self.choices:
                raise ValueError(
                    f"Target '{self.target}' is not present in choices: {list(self.choices.keys())}"
                )

        elif self.eval_type == EvaluationType.EXACT_MATCH:
            if isinstance(self.target, str) and not self.target.strip():
                raise ValueError("Exact match target cannot be empty")
            if isinstance(self.target, list):
                if not self.target:
                    raise ValueError("Exact match target list cannot be empty")
                if any(not isinstance(t, str) or not t.strip() for t in self.target):
                    raise ValueError("All exact match acceptable targets must be non-empty strings")

        elif self.eval_type == EvaluationType.RUBRIC_JUDGED:
            if not isinstance(self.target, str) or not self.target.strip():
                raise ValueError(
                    "Rubric judged items must have a non-empty reference string in 'target'"
                )

        return self
