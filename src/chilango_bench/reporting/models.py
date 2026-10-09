"""Data models for benchmark run reporting and artifact persistence."""

from dataclasses import asdict, dataclass

from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.metrics import BenchmarkMetrics


@dataclass(frozen=True)
class BenchmarkRunReport:
    """Full execution report of a benchmark evaluation run."""

    benchmark_version: str
    model_name: str
    timestamp_utc: str
    dataset_path: str
    metrics: BenchmarkMetrics
    results: list[EvaluationResult]

    def to_dict(self) -> dict[str, object]:
        """Convert report to serializable dictionary."""
        return {
            "benchmark_version": self.benchmark_version,
            "model_name": self.model_name,
            "timestamp_utc": self.timestamp_utc,
            "dataset_path": self.dataset_path,
            "metrics": asdict(self.metrics),
            "results": [
                {
                    "item_id": r.item_id,
                    "category": r.category.value,
                    "eval_type": r.eval_type.value,
                    "score": r.score,
                    "is_correct": r.is_correct,
                    "model_response": r.model_response,
                    "target": r.target,
                    "latency_seconds": r.latency_seconds,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "metadata": r.metadata,
                }
                for r in self.results
            ],
        }
