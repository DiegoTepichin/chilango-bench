"""Run report: everything needed to reproduce and compare a benchmark run."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 (pydantic needs it at runtime)
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from chilango_bench.core.exceptions import ChilangoBenchError
from chilango_bench.evaluators.base import EvaluationResult  # noqa: TC001
from chilango_bench.evaluators.metrics import BenchmarkMetrics  # noqa: TC001


class ReportError(ChilangoBenchError):
    """A report file is missing, unreadable or does not match the schema."""


class DatasetInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    sha256: str
    items: int


class RunSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    base_url: str | None
    temperature: float
    max_tokens: int
    prompt_template: str
    judge_model: str | None = None


class RunReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    report_version: Literal[1] = 1
    benchmark_version: str
    model: str
    created_at: datetime
    dataset: DatasetInfo
    settings: RunSettings
    metrics: BenchmarkMetrics
    results: list[EvaluationResult]

    @property
    def comparability_key(self) -> tuple[str, int, str, str | None]:
        """Runs are comparable only on the same dataset bytes, items, template and judge."""
        return (
            self.dataset.sha256,
            self.dataset.items,
            self.settings.prompt_template,
            self.settings.judge_model,
        )

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> RunReport:
        source = Path(path)
        try:
            return cls.model_validate_json(source.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ReportError(f"cannot read report {source}: {exc}") from exc
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(p) for p in first["loc"]) or "(root)"
            raise ReportError(
                f"{source} is not a valid run report: {location}: {first['msg']}"
            ) from exc
