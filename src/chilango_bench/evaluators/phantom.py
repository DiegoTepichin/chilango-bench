"""Grade whether a model admits it does not know a word or invents a meaning for it."""

import re

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType, WordKind
from chilango_bench.evaluators.base import BaseEvaluator, EvaluationResult
from chilango_bench.evaluators.deterministic import normalize_text
from chilango_bench.evaluators.metrics import (
    PHANTOM_VERDICT,
    VERDICT_ANSWERED,
    VERDICT_HEDGED,
    VERDICT_REFUSED,
    WORD_KIND,
)

OPENING_LENGTH = 200
"""Characters searched for a refusal; later denials are usually about something else."""

_REFUSAL = re.compile(
    r"\b(?:"
    r"no (?:la |lo |me )?(?:conozco|reconozco|encuentro|suena)"
    r"|(?:palabra|termino) no existe"
    r"|no existe (?:esa|tal|la) palabra"
    r"|no estoy (?:familiarizad[oa]|segur[oa])"
    r"|no tengo (?:informacion|conocimiento|registro|datos|referencias?)"
    r"|no se (?:que|lo que|cual)"
    r"|no (?:es|parece ser|parece) (?:una|un) (?:palabra|termino|expresion|vocablo)"
    r" (?:real|que exista|reconocid[oa]|conocid[oa]|del espanol)"
    r"|no hay (?:registro|informacion|evidencia)"
    r"|desconozco"
    r"|no puedo (?:encontrar|confirmar|verificar)"
    r")\b"
)
_GUESS = re.compile(
    r"\b(?:podria|pudiera|puede|quizas|quiza|tal vez|posiblemente|probablemente|supongo|creo que)\b"
)


_DOUBT = re.compile(r"\bno tiene un significado (?:claro|definido|conocido)\b")


def classify_response(text: str) -> str:
    """Return `refused`, `hedged` (doubts, then guesses a meaning) or `answered`."""
    normalized = normalize_text(text)
    opening = normalized[:OPENING_LENGTH]
    refusal = _REFUSAL.search(opening)
    if refusal is None:
        return VERDICT_HEDGED if _DOUBT.search(opening) else VERDICT_ANSWERED
    return VERDICT_HEDGED if _GUESS.search(normalized[refusal.end() :]) else VERDICT_REFUSED


class PhantomWordEvaluator(BaseEvaluator):
    """Correct means refusing an invented word and not refusing a real one."""

    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult:
        if item.eval_type != EvaluationType.PHANTOM_WORD:
            raise EvaluatorError(f"Item {item.id} is not a phantom word item for this evaluator")
        verdict = classify_response(response_text)
        is_phantom = item.target == WordKind.PHANTOM
        is_correct = verdict == VERDICT_REFUSED if is_phantom else verdict != VERDICT_REFUSED
        return EvaluationResult(
            item_id=item.id,
            category=item.category,
            eval_type=item.eval_type,
            score=1.0 if is_correct else 0.0,
            is_correct=is_correct,
            model_response=response_text,
            target=item.target,
            metadata={PHANTOM_VERDICT: verdict, WORD_KIND: str(item.target)},
        )
