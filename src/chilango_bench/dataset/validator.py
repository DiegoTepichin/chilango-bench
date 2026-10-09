"""Dataset validation utilities and summary reports."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from chilango_bench.core.exceptions import DatasetError, DatasetValidationError
from chilango_bench.dataset.loader import load_dataset
from chilango_bench.dataset.models import BenchmarkItem, Category, EvaluationType


@dataclass(frozen=True)
class ValidationReport:
    """Summary of validated dataset contents."""

    total_items: int
    category_counts: dict[str, int]
    eval_type_counts: dict[str, int]
    is_valid: bool = True
    error_message: str | None = None


def validate_dataset_file(file_path: str | Path) -> ValidationReport:
    """Validate a dataset file and return a structured summary report.

    Args:
        file_path: Path to dataset file.

    Returns:
        ValidationReport instance summarizing item distributions or errors.
    """
    try:
        items = load_dataset(file_path)
    except (DatasetError, DatasetValidationError) as exc:
        return ValidationReport(
            total_items=0,
            category_counts={},
            eval_type_counts={},
            is_valid=False,
            error_message=str(exc),
        )

    return summarize_dataset(items)


def summarize_dataset(items: list[BenchmarkItem]) -> ValidationReport:
    """Produce distribution summary of an in-memory list of benchmark items."""
    cat_counts = Counter(item.category.value for item in items)
    type_counts = Counter(item.eval_type.value for item in items)

    # Ensure all enum values are present in summary
    for cat in Category:
        cat_counts.setdefault(cat.value, 0)
    for et in EvaluationType:
        type_counts.setdefault(et.value, 0)

    return ValidationReport(
        total_items=len(items),
        category_counts=dict(cat_counts),
        eval_type_counts=dict(type_counts),
        is_valid=True,
    )
