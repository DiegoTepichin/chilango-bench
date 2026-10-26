"""Deterministic evaluators for multiple choice and exact match benchmarks."""

import re
import unicodedata

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType
from chilango_bench.evaluators.base import BaseEvaluator, EvaluationResult
from chilango_bench.evaluators.metrics import UNRESOLVED


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping accents, and collapsing punctuation/whitespace."""
    # Decompose unicode characters into base character + diacritic
    nfkd = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace punctuation with spaces
    without_punct = re.sub(r"[^\w\s]", " ", without_accents)
    # Collapse multiple whitespaces
    return " ".join(without_punct.split()).strip()


MIN_CHOICE_TEXT_LENGTH = 4
_MARKUP = re.compile(r"[*_`#>]")
_BARE_KEY = re.compile(r"^\(?([A-Za-z])\)?[.:]?$")
_LEADING_KEY = re.compile(r"^(?:\(([A-Za-z])\)|([A-Za-z])[).:]|([A-Z])\s)")
_ALTERNATIVE = re.compile(r"^\)?\s*(?:,|o|u|y|ni)\s+\(?[A-Za-z]\b", re.IGNORECASE)
_KEYWORD_KEY = re.compile(
    r"\b(?:opci[oó]n|respuesta|letra|inciso)(?:\s+correcta)?(?:\s+es)?(?:\s+la)?"
    r"\s*[:\-]?\s*\(?([A-Za-z])\b",
    re.IGNORECASE,
)


def extract_choice_key(response_text: str, choices: dict[str, str]) -> str | None:
    """Return the option the response commits to, or None when it is missing or ambiguous.

    Only explicit forms count: a bare letter ("B", "(b)"), a leading letter with punctuation
    ("B) ...", "b. ..."), a keyword ("la respuesta es C") or the full text of exactly one option.
    A loose single letter inside a sentence never counts: in Spanish "a", "e", "o" and "y" are
    words.
    """
    text = _MARKUP.sub("", response_text).strip()
    valid = {key.upper() for key in choices}
    for candidate in (_bare_key(text), _leading_key(text), _keyword_key(text)):
        if candidate is not None:
            return candidate if candidate in valid else None
    return _choice_text_key(text, choices)


def _bare_key(text: str) -> str | None:
    match = _BARE_KEY.match(text)
    return match.group(1).upper() if match else None


def _leading_key(text: str) -> str | None:
    match = _LEADING_KEY.match(text)
    if not match:
        return None
    return next(g for g in match.groups() if g).upper()


def _keyword_key(text: str) -> str | None:
    keys: set[str] = set()
    for match in _KEYWORD_KEY.finditer(text):
        if _ALTERNATIVE.match(text[match.end() :]):
            return None
        keys.add(match.group(1).upper())
    return keys.pop() if len(keys) == 1 else None


def _choice_text_key(text: str, choices: dict[str, str]) -> str | None:
    response = f" {normalize_text(text)} "
    matches = [
        key.upper()
        for key, value in choices.items()
        if len(normalized := normalize_text(value)) >= MIN_CHOICE_TEXT_LENGTH
        and f" {normalized} " in response
    ]
    return matches[0] if len(matches) == 1 else None


class MultipleChoiceEvaluator(BaseEvaluator):
    """Evaluates multiple choice items by extracting and matching option keys."""

    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult:
        """Grade multiple choice response."""
        if item.eval_type != EvaluationType.MULTIPLE_CHOICE or not item.choices:
            raise EvaluatorError(
                f"Item {item.id} is not a valid multiple choice item for this evaluator"
            )

        extracted_key = extract_choice_key(response_text, item.choices)
        expected_key = str(item.target).upper()
        is_correct = extracted_key is not None and extracted_key == expected_key
        score = 1.0 if is_correct else 0.0

        return EvaluationResult(
            item_id=item.id,
            category=item.category,
            eval_type=item.eval_type,
            score=score,
            is_correct=is_correct,
            model_response=response_text,
            target=item.target,
            metadata={"extracted_choice": extracted_key or UNRESOLVED},
        )


class ExactMatchEvaluator(BaseEvaluator):
    """Evaluates short-form exact match items using string normalization."""

    def evaluate(self, item: BenchmarkItem, response_text: str) -> EvaluationResult:
        """Grade exact match response."""
        if item.eval_type != EvaluationType.EXACT_MATCH:
            raise EvaluatorError(f"Item {item.id} is not an exact match item for this evaluator")

        norm_candidate = normalize_text(response_text)

        targets: list[str] = (
            [str(t) for t in item.target] if isinstance(item.target, list) else [str(item.target)]
        )

        norm_targets = [normalize_text(t) for t in targets]

        # Exact normalized match or concise boundary match
        is_correct = (
            norm_candidate in norm_targets
            or any(t == norm_candidate for t in norm_targets)
            or any(f" {t} " in f" {norm_candidate} " for t in norm_targets if len(t) > 3)
        )

        score = 1.0 if is_correct else 0.0

        return EvaluationResult(
            item_id=item.id,
            category=item.category,
            eval_type=item.eval_type,
            score=score,
            is_correct=is_correct,
            model_response=response_text,
            target=item.target,
            metadata={
                "normalized_candidate": norm_candidate,
                "normalized_targets": " | ".join(norm_targets),
            },
        )
