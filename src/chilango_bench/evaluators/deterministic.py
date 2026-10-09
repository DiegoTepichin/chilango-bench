"""Deterministic evaluators for multiple choice and exact match benchmarks."""

import re
import unicodedata

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, EvaluationType
from chilango_bench.evaluators.base import BaseEvaluator, EvaluationResult


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, stripping accents, and collapsing punctuation/whitespace."""
    # Decompose unicode characters into base character + diacritic
    nfkd = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace punctuation with spaces
    without_punct = re.sub(r"[^\w\s]", " ", without_accents)
    # Collapse multiple whitespaces
    return " ".join(without_punct.split()).strip()


def extract_choice_key(response_text: str, choices: dict[str, str]) -> str | None:
    """Extract choice key (e.g. 'A', 'B') from candidate response."""
    text = response_text.strip()
    valid_keys = set(choices.keys())

    # Case 1: Response starts directly with a single key followed by punctuation or space
    direct_match = re.match(r"^([A-Za-z])[\.\)\s\:\-]", text)
    if direct_match:
        key = direct_match.group(1).upper()
        if key in valid_keys:
            return key

    # Case 2: Exact single letter response
    if len(text) == 1 and text.upper() in valid_keys:
        return text.upper()

    # Case 3: Explicit phrase like "Opción B", "Respuesta: B", "La letra B"
    phrase_match = re.search(
        r"(?:opci[oó]n|respuesta|letra)\s*[:\s\-]*\s*([A-Za-z])\b", text, re.IGNORECASE
    )
    if phrase_match:
        key = phrase_match.group(1).upper()
        if key in valid_keys:
            return key

    # Case 4: First isolated token matching a choice key
    isolated_match = re.search(r"\b([A-Za-z])\b", text)
    if isolated_match:
        key = isolated_match.group(1).upper()
        if key in valid_keys:
            return key

    # Case 5: The response text contains the exact value of one of the choices
    normalized_response = normalize_text(text)
    for key, choice_text in choices.items():
        norm_choice = normalize_text(choice_text)
        if norm_choice and norm_choice in normalized_response:
            return key

    return None


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
            metadata={"extracted_choice": extracted_key or "UNRESOLVED"},
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
            metadata={"normalized_candidate": norm_candidate, "normalized_targets": norm_targets},
        )
