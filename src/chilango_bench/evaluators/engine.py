"""Evaluation engine orchestrating dataset execution, scoring, and metrics."""

from collections.abc import Callable
from dataclasses import dataclass

from chilango_bench.core.exceptions import EvaluatorError, RunnerError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType
from chilango_bench.evaluators.base import BaseEvaluator, EvaluationResult
from chilango_bench.evaluators.deterministic import ExactMatchEvaluator, MultipleChoiceEvaluator
from chilango_bench.evaluators.judge import RubricJudgeEvaluator
from chilango_bench.evaluators.metrics import BenchmarkMetrics, aggregate_metrics
from chilango_bench.evaluators.phantom import PhantomWordEvaluator
from chilango_bench.runners.base import BaseRunner

PROMPT_TEMPLATE = "es-v1"
"""Bump whenever `format_eval_prompt` changes, so old and new runs are never ranked together."""


def format_eval_prompt(item: BenchmarkItem) -> str:
    """Format prompt with choices if multiple choice."""
    if item.eval_type == EvaluationType.MULTIPLE_CHOICE and item.choices:
        choices_text = "\n".join(f"{k}) {v}" for k, v in item.choices.items())
        return (
            f"{item.prompt}\n\n"
            f"Opciones:\n{choices_text}\n\n"
            "Responde únicamente con la letra de la opción correcta (ejemplo: A)."
        )
    return item.prompt


@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = 0.0
    max_tokens: int = 512


ProgressCallback = Callable[[int, int, EvaluationResult], None]


class EvaluationEngine:
    """Runs the candidate model on each item and grades the answer."""

    def __init__(
        self,
        runner: BaseRunner,
        judge_runner: BaseRunner | None = None,
        settings: GenerationSettings | None = None,
    ) -> None:
        self.runner = runner
        self.settings = settings or GenerationSettings()
        self.mcq_evaluator = MultipleChoiceEvaluator()
        self.em_evaluator = ExactMatchEvaluator()
        self.phantom_evaluator = PhantomWordEvaluator()
        self.judge_evaluator = RubricJudgeEvaluator(judge_runner) if judge_runner else None

    def evaluate_item(self, item: BenchmarkItem) -> EvaluationResult:
        """Grade one item; a runner failure becomes an errored result instead of an exception."""
        evaluator = self._evaluator_for(item)
        try:
            response = self.runner.generate(
                prompt=format_eval_prompt(item),
                system_prompt=item.system_prompt,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )
        except RunnerError as exc:
            return EvaluationResult(
                item_id=item.id,
                category=item.category,
                eval_type=item.eval_type,
                score=0.0,
                is_correct=False,
                model_response="",
                target=item.target,
                error=f"runner failed: {exc}",
            )
        try:
            graded = evaluator.evaluate(item, response.text)
        except RunnerError as exc:
            graded = EvaluationResult(
                item_id=item.id,
                category=item.category,
                eval_type=item.eval_type,
                score=0.0,
                is_correct=False,
                model_response=response.text,
                target=item.target,
                error=f"judge failed: {exc}",
            )
        return graded.model_copy(
            update={
                "latency_seconds": response.latency_seconds,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
            }
        )

    def run_benchmark(
        self, items: list[BenchmarkItem], on_result: ProgressCallback | None = None
    ) -> tuple[list[EvaluationResult], BenchmarkMetrics]:
        results: list[EvaluationResult] = []
        for index, item in enumerate(items, start=1):
            results.append(self.evaluate_item(item))
            if on_result is not None:
                on_result(index, len(items), results[-1])
        return results, aggregate_metrics(results)

    def _evaluator_for(self, item: BenchmarkItem) -> BaseEvaluator:
        if item.eval_type is EvaluationType.MULTIPLE_CHOICE:
            return self.mcq_evaluator
        if item.eval_type is EvaluationType.EXACT_MATCH:
            return self.em_evaluator
        if item.eval_type is EvaluationType.PHANTOM_WORD:
            return self.phantom_evaluator
        if self.judge_evaluator is None:
            raise EvaluatorError(f"item {item.id} needs a judge model (--judge)")
        return self.judge_evaluator
