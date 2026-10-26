"""Evaluation engine orchestrating dataset execution, scoring, and metrics."""

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType
from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.deterministic import ExactMatchEvaluator, MultipleChoiceEvaluator
from chilango_bench.evaluators.judge import RubricJudgeEvaluator
from chilango_bench.evaluators.metrics import BenchmarkMetrics, aggregate_metrics
from chilango_bench.runners.base import BaseRunner


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


class EvaluationEngine:
    """Orchestrates candidate model execution and grading across benchmark items."""

    def __init__(self, runner: BaseRunner, judge_runner: BaseRunner | None = None) -> None:
        self.runner = runner
        self.mcq_evaluator = MultipleChoiceEvaluator()
        self.em_evaluator = ExactMatchEvaluator()
        self.judge_evaluator = RubricJudgeEvaluator(judge_runner) if judge_runner else None

    def evaluate_item(self, item: BenchmarkItem) -> EvaluationResult:
        """Run candidate model and grade individual benchmark item."""
        formatted_prompt = format_eval_prompt(item)

        response = self.runner.generate(
            prompt=formatted_prompt,
            system_prompt=item.system_prompt,
            temperature=0.0,
        )

        if item.eval_type == EvaluationType.MULTIPLE_CHOICE:
            eval_res = self.mcq_evaluator.evaluate(item, response.text)
        elif item.eval_type == EvaluationType.EXACT_MATCH:
            eval_res = self.em_evaluator.evaluate(item, response.text)
        elif item.eval_type == EvaluationType.RUBRIC_JUDGED:
            if not self.judge_evaluator:
                msg = (
                    f"Item {item.id} requires a judge runner for rubric evaluation, "
                    "but none was provided."
                )
                raise EvaluatorError(msg)
            eval_res = self.judge_evaluator.evaluate(item, response.text)
        else:
            raise EvaluatorError(f"Unsupported evaluation type: {item.eval_type}")

        # Incorporate latency and token consumption from runner response
        return EvaluationResult(
            item_id=eval_res.item_id,
            category=eval_res.category,
            eval_type=eval_res.eval_type,
            score=eval_res.score,
            is_correct=eval_res.is_correct,
            model_response=eval_res.model_response,
            target=eval_res.target,
            latency_seconds=response.latency_seconds,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            metadata=eval_res.metadata,
        )

    def run_benchmark(
        self, items: list[BenchmarkItem]
    ) -> tuple[list[EvaluationResult], BenchmarkMetrics]:
        """Execute benchmark sequentially over items and produce summary metrics."""
        results: list[EvaluationResult] = []
        for item in items:
            result = self.evaluate_item(item)
            results.append(result)

        metrics = aggregate_metrics(results)
        return results, metrics
