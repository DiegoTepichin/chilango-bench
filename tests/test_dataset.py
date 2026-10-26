"""Unit tests for dataset schema, loaders, validators, and seed dataset."""

from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from chilango_bench.core.exceptions import DatasetError, DatasetValidationError
from chilango_bench.dataset.loader import load_dataset, save_dataset
from chilango_bench.dataset.models import (
    BenchmarkItem,
    Category,
    EvaluationType,
    ReviewStatus,
    RubricCriterion,
)
from chilango_bench.dataset.validator import validate_dataset_file


def test_benchmark_item_valid_multiple_choice() -> None:
    """Verify valid multiple choice item instantiation."""
    item = BenchmarkItem(
        id="test-mcq-1",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        prompt="¿Qué significa cámara?",
        choices={"A": "Opción 1", "B": "Opción 2"},
        target="A",
        metadata={"difficulty": "easy"},
    )
    assert item.id == "test-mcq-1"
    assert item.category == Category.SLANG
    assert item.eval_type == EvaluationType.MULTIPLE_CHOICE
    assert item.target == "A"


def test_benchmark_item_invalid_choice_target() -> None:
    """Ensure target must be within choices for multiple choice items."""
    with pytest.raises(ValidationError, match="Target 'C' is not present in choices"):
        BenchmarkItem(
            id="test-mcq-invalid",
            category=Category.SLANG,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            prompt="¿Qué significa cámara?",
            choices={"A": "Opción 1", "B": "Opción 2"},
            target="C",
        )


def test_benchmark_item_mcq_insufficient_choices() -> None:
    """Ensure multiple choice items must have at least 2 choices."""
    with pytest.raises(ValidationError, match="at least 2 choices"):
        BenchmarkItem(
            id="test-mcq-few",
            category=Category.SLANG,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            prompt="¿Qué significa cámara?",
            choices={"A": "Opción 1"},
            target="A",
        )


def test_benchmark_item_blank_prompt() -> None:
    """Ensure blank prompts are rejected."""
    with pytest.raises(ValidationError, match="Prompt cannot be empty or purely whitespace"):
        BenchmarkItem(
            id="test-blank",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="   ",
            target="respuesta",
        )


def test_benchmark_item_exact_match_valid() -> None:
    """Verify exact match item with multiple acceptable targets."""
    item = BenchmarkItem(
        id="test-em-1",
        category=Category.CULTURAL_CONTEXT,
        eval_type=EvaluationType.EXACT_MATCH,
        prompt="¿Nombre de la torta de tamal?",
        target=["guajolota", "la guajolota"],
    )
    assert item.eval_type == EvaluationType.EXACT_MATCH
    assert isinstance(item.target, list)
    assert len(item.target) == 2


def test_benchmark_item_rubric_judged_valid() -> None:
    """Verify rubric judged item with criteria."""
    criterion = RubricCriterion(name="precisión", description="Explica el origen", weight=1.5)
    item = BenchmarkItem(
        id="test-rubric-1",
        category=Category.ALBUR,
        eval_type=EvaluationType.RUBRIC_JUDGED,
        prompt="Explica el doble sentido de la frase",
        target="La frase alude a una insinuación sexual mediante homofonía",
        rubric=[criterion],
    )
    assert item.eval_type == EvaluationType.RUBRIC_JUDGED
    assert item.rubric is not None
    assert len(item.rubric) == 1
    assert item.rubric[0].weight == 1.5


DATASET = Path("datasets/v1/chilango-bench.jsonl")


def test_v1_dataset_loads_and_covers_every_category_and_type() -> None:
    items = load_dataset(DATASET)
    report = validate_dataset_file(DATASET)

    assert report.is_valid
    assert len(items) >= 150
    assert all(count > 0 for count in report.category_counts.values())
    assert all(count > 0 for count in report.eval_type_counts.values())


def test_v1_answer_keys_are_balanced() -> None:
    items = load_dataset(DATASET)
    multiple_choice = [item for item in items if item.eval_type == EvaluationType.MULTIPLE_CHOICE]
    counts = Counter(str(item.target) for item in multiple_choice)

    assert max(counts.values()) / len(multiple_choice) <= 0.25 + 0.03


def test_v1_option_length_does_not_give_the_answer_away() -> None:
    report = validate_dataset_file(DATASET)

    assert 0.15 <= report.longest_choice_rate <= 0.30
    assert report.shortest_choice_rate <= 0.30


def test_v1_items_explain_their_answer_and_carry_review_status() -> None:
    items = load_dataset(DATASET)

    assert all(item.explanation or item.rubric or "origin" in item.metadata for item in items)
    assert all(isinstance(item.review_status, ReviewStatus) for item in items)


def test_v1_file_starts_with_the_canary() -> None:
    first_line = DATASET.read_text(encoding="utf-8").splitlines()[0]

    assert first_line.startswith("# chilango-bench v1 dataset. Canary GUID ")


def test_load_dataset_duplicate_id_rejection(tmp_path: Path) -> None:
    """Ensure duplicate item IDs are caught and reported."""
    bad_file = tmp_path / "duplicates.jsonl"
    line1 = (
        '{"id": "item-1", "category": "slang", "eval_type": "exact_match", '
        '"prompt": "P1", "target": "T1"}\n'
    )
    line2 = (
        '{"id": "item-1", "category": "slang", "eval_type": "exact_match", '
        '"prompt": "P2", "target": "T2"}\n'
    )
    bad_file.write_text(line1 + line2, encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Duplicate item ID 'item-1'"):
        load_dataset(bad_file)


def test_load_dataset_malformed_json(tmp_path: Path) -> None:
    """Ensure malformed JSON raises DatasetValidationError with line number."""
    bad_file = tmp_path / "malformed.jsonl"
    bad_file.write_text('{"id": "item-1", "category": "slang"\n', encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Malformed JSON on line 1"):
        load_dataset(bad_file)


def test_load_dataset_non_dict_json(tmp_path: Path) -> None:
    """Ensure JSON arrays or scalars raise DatasetValidationError."""
    bad_file = tmp_path / "not_dict.jsonl"
    bad_file.write_text('["not", "an", "object"]\n', encoding="utf-8")
    with pytest.raises(DatasetValidationError, match="Expected JSON object on line 1"):
        load_dataset(bad_file)


def test_load_dataset_file_not_found(tmp_path: Path) -> None:
    """Ensure non-existent files raise DatasetError."""
    missing_file = tmp_path / "does_not_exist.jsonl"
    with pytest.raises(DatasetError, match="Dataset file does not exist"):
        load_dataset(missing_file)


def test_load_dataset_empty_file(tmp_path: Path) -> None:
    """Ensure empty files raise DatasetError."""
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(DatasetError, match="Dataset file is empty"):
        load_dataset(empty_file)


def test_save_and_reload_dataset(tmp_path: Path) -> None:
    """Ensure dataset can be saved to JSONL and reloaded identically."""
    items = [
        BenchmarkItem(
            id="item-save-1",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="Prompt 1",
            target="Target 1",
        ),
        BenchmarkItem(
            id="item-save-2",
            category=Category.PROCEDURES,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            prompt="Prompt 2",
            choices={"A": "O1", "B": "O2"},
            target="B",
        ),
    ]

    out_file = tmp_path / "output.jsonl"
    save_dataset(items, out_file)

    loaded = load_dataset(out_file)
    assert len(loaded) == 2
    assert loaded[0].id == "item-save-1"
    assert loaded[1].id == "item-save-2"
    assert loaded[1].target == "B"


def test_validate_dataset_file_reports_errors(tmp_path: Path) -> None:
    """Ensure validate_dataset_file produces error reports on invalid files."""
    bad_file = tmp_path / "broken.jsonl"
    bad_file.write_text('{"bad": "data"}\n', encoding="utf-8")
    report = validate_dataset_file(bad_file)
    assert report.is_valid is False
    assert report.error_message is not None


def test_benchmark_item_mcq_target_must_be_str() -> None:
    """Ensure multiple choice target cannot be a list."""
    with pytest.raises(ValidationError, match="single choice key string"):
        BenchmarkItem(
            id="test-mcq-list-target",
            category=Category.SLANG,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            prompt="¿Pregunta?",
            choices={"A": "O1", "B": "O2"},
            target=["A"],
        )


def test_benchmark_item_exact_match_invalid_targets() -> None:
    """Ensure invalid exact match targets are rejected."""
    with pytest.raises(ValidationError, match="Exact match target cannot be empty"):
        BenchmarkItem(
            id="test-em-empty-str",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="¿Pregunta?",
            target="   ",
        )

    with pytest.raises(ValidationError, match="Exact match target list cannot be empty"):
        BenchmarkItem(
            id="test-em-empty-list",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="¿Pregunta?",
            target=[],
        )

    with pytest.raises(ValidationError, match="All exact match acceptable targets"):
        BenchmarkItem(
            id="test-em-blank-in-list",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="¿Pregunta?",
            target=["bueno", " "],
        )


def test_benchmark_item_rubric_invalid_targets() -> None:
    """Ensure rubric judged items reject empty target references."""
    with pytest.raises(ValidationError, match="non-empty reference string"):
        BenchmarkItem(
            id="test-rubric-empty",
            category=Category.ALBUR,
            eval_type=EvaluationType.RUBRIC_JUDGED,
            prompt="¿Pregunta?",
            target="   ",
        )


def test_load_dataset_os_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure IO/OS errors during reading raise DatasetError."""
    test_file = tmp_path / "file.jsonl"
    test_file.write_text('{"id": "1"}\n', encoding="utf-8")

    def mock_open(*args: object, **kwargs: object) -> None:
        raise OSError("Disk failure")

    monkeypatch.setattr(Path, "open", mock_open)
    with pytest.raises(DatasetError, match="Failed to read dataset file"):
        load_dataset(test_file)


def test_save_dataset_os_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure IO/OS errors during writing raise DatasetError."""
    dest_file = tmp_path / "dest.jsonl"
    items = [
        BenchmarkItem(
            id="test-item",
            category=Category.SLANG,
            eval_type=EvaluationType.EXACT_MATCH,
            prompt="P",
            target="T",
        )
    ]

    def mock_open(*args: object, **kwargs: object) -> None:
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "open", mock_open)
    with pytest.raises(DatasetError, match="Failed to write dataset"):
        save_dataset(items, dest_file)
