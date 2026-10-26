"""LLM-as-a-judge rubric evaluator for open-ended benchmark responses."""

import json
import re

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType
from chilango_bench.evaluators.base import BaseEvaluator, EvaluationResult
from chilango_bench.runners.base import BaseRunner

JUDGE_SYSTEM_PROMPT = """Eres un evaluador experto y objetivo de modelos en español mexicano.
Tu tarea es calificar la respuesta de un modelo candidato frente a una referencia.
Debes calificar con un puntaje entero del 1 al 5 según la siguiente escala:
1: Completamente incorrecta o irrelevante.
2: Mayormente incorrecta o confunde conceptos clave.
3: Parcialmente correcta, entiende la idea pero omite detalles o matices esenciales.
4: Buena respuesta, comprende los matices culturales/lingüísticos con precisión aceptable.
5: Excelente respuesta, captura perfectamente el contexto, modismos y sutilezas mexicanas.

Debes responder ÚNICAMENTE un objeto JSON válido con este formato:
{"score": <entero del 1 al 5>, "justification": "<breve explicación de tu veredicto>"}
"""


PASSING_SCORE = 3
_SCORE_FIELD = re.compile(r"[\"']?score[\"']?\s*[:=]\s*(\d+)", re.IGNORECASE)


class RubricJudgeEvaluator(BaseEvaluator):
    """Evaluates open-ended answers using an LLM judge runner against rubric criteria."""

    def __init__(self, judge_runner: BaseRunner) -> None:
        self.judge_runner = judge_runner

    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult:
        """Judge candidate answer using judge runner."""
        if item.eval_type != EvaluationType.RUBRIC_JUDGED:
            raise EvaluatorError(f"Item {item.id} is not a rubric judged item for this evaluator")

        rubric_text = ""
        if item.rubric:
            rubric_text = "\nCriterios de evaluación específicos:\n" + "\n".join(
                f"- {c.name} (peso {c.weight}): {c.description}" for c in item.rubric
            )

        judge_prompt = (
            f"Pregunta del benchmark:\n{item.prompt}\n\n"
            f"Respuesta de referencia (Ground Truth):\n{item.target}\n"
            f"{rubric_text}\n\n"
            f"Respuesta del modelo candidato a evaluar:\n{response_text}\n\n"
            "Emite tu veredicto en formato JSON:"
        )

        judge_response = self.judge_runner.generate(
            prompt=judge_prompt,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=256,
        )

        verdict = parse_judge_output(judge_response.text)
        if verdict is None:
            return EvaluationResult(
                item_id=item.id,
                category=item.category,
                eval_type=item.eval_type,
                score=0.0,
                is_correct=False,
                model_response=response_text,
                target=item.target,
                error=f"judge output could not be parsed: {judge_response.text[:200]!r}",
                metadata={"judge_model": self.judge_runner.model_name},
            )
        score, justification = verdict
        return EvaluationResult(
            item_id=item.id,
            category=item.category,
            eval_type=item.eval_type,
            score=(score - 1) / 4,
            is_correct=score >= PASSING_SCORE,
            model_response=response_text,
            target=item.target,
            metadata={
                "judge_raw_score": score,
                "judge_justification": justification,
                "judge_model": self.judge_runner.model_name,
            },
        )


def parse_judge_output(text: str) -> tuple[int, str] | None:
    """Score (1-5) and justification from the judge, or None if it is missing or out of range."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("score"), int):
            score = int(data["score"])
            return (score, str(data.get("justification", ""))) if 1 <= score <= 5 else None
    field = _SCORE_FIELD.search(text)
    if field and 1 <= int(field.group(1)) <= 5:
        return int(field.group(1)), text.strip()
    return None
