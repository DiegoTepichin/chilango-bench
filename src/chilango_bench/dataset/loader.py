"""Dataset loader and serializer for chilango-bench JSONL files."""

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from chilango_bench.core.exceptions import DatasetError, DatasetValidationError
from chilango_bench.dataset.models import BenchmarkItem


def load_dataset(file_path: str | Path) -> list[BenchmarkItem]:
    """Load and validate benchmark items from a JSONL file.

    Args:
        file_path: Path to the JSONL dataset file.

    Returns:
        List of strictly validated BenchmarkItem instances.

    Raises:
        DatasetError: If the file does not exist or cannot be accessed.
        DatasetValidationError: If any item fails schema or duplicate validation.
    """
    path = Path(file_path)
    if not path.is_file():
        raise DatasetError(f"Dataset file does not exist: {path}")

    items: list[BenchmarkItem] = []
    seen_ids: dict[str, int] = {}

    try:
        with path.open("r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetValidationError(
                        f"Malformed JSON on line {line_no}: {exc.msg}",
                        line_number=line_no,
                    ) from exc

                if not isinstance(data, dict):
                    raise DatasetValidationError(
                        f"Expected JSON object on line {line_no}, got {type(data).__name__}",
                        line_number=line_no,
                    )

                try:
                    item = BenchmarkItem.model_validate(data)
                except ValidationError as exc:
                    first_err = exc.errors()[0]
                    loc = ".".join(str(p) for p in first_err["loc"])
                    msg = first_err["msg"]
                    raise DatasetValidationError(
                        f"Validation error on line {line_no} [{loc}]: {msg}",
                        line_number=line_no,
                        item_id=str(data.get("id")) if "id" in data else None,
                    ) from exc

                if item.id in seen_ids:
                    first_line = seen_ids[item.id]
                    msg = (
                        f"Duplicate item ID '{item.id}' found on line {line_no} "
                        f"(first declared on line {first_line})"
                    )
                    raise DatasetValidationError(
                        msg,
                        line_number=line_no,
                        item_id=item.id,
                    )

                seen_ids[item.id] = line_no
                items.append(item)

    except OSError as exc:
        raise DatasetError(f"Failed to read dataset file {path}: {exc}") from exc

    if not items:
        raise DatasetError(f"Dataset file is empty or contains no valid items: {path}")

    return items


def save_dataset(items: list[BenchmarkItem], file_path: str | Path) -> None:
    """Save benchmark items to a JSONL file.

    Args:
        items: List of benchmark items to write.
        file_path: Destination path.

    Raises:
        DatasetError: If writing to the file fails.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                line = item.model_dump_json(exclude_none=True)
                f.write(f"{line}\n")
    except OSError as exc:
        raise DatasetError(f"Failed to write dataset to {path}: {exc}") from exc


def file_sha256(file_path: str | Path) -> str:
    """Hex SHA-256 of the dataset bytes, which pins exactly what a run was graded on."""
    return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
