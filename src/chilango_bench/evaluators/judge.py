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

        score_int, justification = self._parse_judge_output(judge_response.text)
        # Normalize 1..5 to 0.0..1.0
        normalized_score = max(0.0, min(1.0, (score_int - 1.0) / 4.0))
        is_correct = score_int >= 3

        return EvaluationResult(
            item_id=item.id,
            category=item.category,
            eval_type=item.eval_type,
            score=normalized_score,
            is_correct=is_correct,
            model_response=response_text,
            target=item.target,
            metadata={
                "judge_raw_score": score_int,
                "judge_justification": justification,
                "judge_model": self.judge_runner.model_name,
            },
        )

    def _parse_judge_output(self, text: str) -> tuple[int, str]:
        """Extract score and justification from judge model output."""
        cleaned = text.strip()

        # Attempt JSON extraction
        try:
            # Strip markdown code blocks if wrapped in ```json ... ```
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if "score" in data:
                    raw_score = int(data["score"])
                    justification = str(data.get("justification", ""))
                    clamped_score = max(1, min(5, raw_score))
                    return clamped_score, justification
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback to regex finding score
        score_match = re.search(r"\b([1-5])\b", cleaned)
        if score_match:
            return int(score_match.group(1)), cleaned

        # Default fallback
        return 1, f"Failed to parse structured score from judge output: {cleaned}"
