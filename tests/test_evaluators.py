"""Unit tests for deterministic evaluators, rubric judge, metrics, and evaluation engine."""

import pytest

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.models import BenchmarkItem, Category, EvaluationType, RubricCriterion
from chilango_bench.evaluators.base import EvaluationResult
from chilango_bench.evaluators.deterministic import (
    ExactMatchEvaluator,
    MultipleChoiceEvaluator,
    extract_choice_key,
    normalize_text,
)
from chilango_bench.evaluators.engine import EvaluationEngine, format_eval_prompt
from chilango_bench.evaluators.judge import RubricJudgeEvaluator
from chilango_bench.evaluators.metrics import aggregate_metrics
from chilango_bench.runners.mock import MockRunner


def test_normalize_text() -> None:
    """Ensure normalization handles accents, casing, and punctuation properly."""
    raw = "¡¿CÁMARA, mi gente?!  "
    normalized = normalize_text(raw)
    assert normalized == "camara mi gente"


def test_extract_choice_key_patterns() -> None:
    """Ensure various choice expression styles are recognized."""
    choices = {"A": "Metro Pantitlán", "B": "Metro La Raza", "C": "Metro Tacubaya"}

    assert extract_choice_key("B", choices) == "B"
    assert extract_choice_key("B. Es la opción correcta.", choices) == "B"
    assert extract_choice_key("b) La Raza", choices) == "B"
    assert extract_choice_key("La respuesta correcta es la opción C.", choices) == "C"
    assert extract_choice_key("Considero que la estación es Metro Pantitlán.", choices) == "A"
    assert extract_choice_key("No tengo certeza alguna", choices) is None


def test_multiple_choice_evaluator() -> None:
    """Ensure MultipleChoiceEvaluator scores correct and incorrect responses."""
    item = BenchmarkItem(
        id="mcq-test",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        prompt="¿Significado de cámara?",
        choices={"A": "Foto", "B": "De acuerdo"},
        target="B",
    )
    evaluator = MultipleChoiceEvaluator()

    res_correct = evaluator.evaluate(item, "Opción B")
    assert res_correct.is_correct is True
    assert res_correct.score == 1.0

    res_incorrect = evaluator.evaluate(item, "Opción A")
    assert res_incorrect.is_correct is False
    assert res_incorrect.score == 0.0

    bad_item = BenchmarkItem(
        id="bad-item",
        category=Category.SLANG,
        eval_type=EvaluationType.EXACT_MATCH,
        prompt="Prompt",
        target="Target",
    )
    with pytest.raises(EvaluatorError, match="not a valid multiple choice item"):
        evaluator.evaluate(bad_item, "B")


def test_exact_match_evaluator() -> None:
    """Ensure ExactMatchEvaluator handles case and accent differences."""
    item = BenchmarkItem(
        id="em-test",
        category=Category.CULTURAL_CONTEXT,
        eval_type=EvaluationType.EXACT_MATCH,
        prompt="¿Cómo se llama la torta de tamal?",
        target=["Guajolota", "la guajolota"],
    )
    evaluator = ExactMatchEvaluator()

    res_accent = evaluator.evaluate(item, "¡GUAJOLOTA!")
    assert res_accent.is_correct is True
    assert res_accent.score == 1.0

    res_phrase = evaluator.evaluate(item, "Se le conoce como la guajolota en la CDMX")
    assert res_phrase.is_correct is True

    res_wrong = evaluator.evaluate(item, "Es un pambazo")
    assert res_wrong.is_correct is False
    assert res_wrong.score == 0.0


def test_rubric_judge_evaluator() -> None:
    """Ensure RubricJudgeEvaluator parses structured judge scores and scales properly."""
    criterion = RubricCriterion(name="precisión", description="Detalle del albur")
    item = BenchmarkItem(
        id="rubric-test",
        category=Category.ALBUR,
        eval_type=EvaluationType.RUBRIC_JUDGED,
        prompt="Explica el albur",
        target="Explicación detallada del doble sentido fálico",
        rubric=[criterion],
    )

    # Mock judge returning score 5
    mock_judge = MockRunner(
        default_response='{"score": 5, "justification": "Captura perfectamente el albur"}'
    )
    evaluator = RubricJudgeEvaluator(mock_judge)

    res = evaluator.evaluate(item, "Respuesta del candidato")
    assert res.score == 1.0  # (5-1)/4 = 1.0
    assert res.is_correct is True
    assert res.metadata["judge_raw_score"] == 5

    # Mock judge returning fallback regex score 3
    mock_judge_regex = MockRunner(
        default_response="Mi puntuación final es un 3 para esta respuesta."
    )
    evaluator_regex = RubricJudgeEvaluator(mock_judge_regex)
    res_regex = evaluator_regex.evaluate(item, "Respuesta parcial")
    assert res_regex.score == 0.5  # (3-1)/4 = 0.5
    assert res_regex.is_correct is True


def test_aggregate_metrics_calculations() -> None:
    """Ensure aggregate_metrics computes percentages and breakdowns correctly."""
    results = [
        EvaluationResult(
            item_id="1",
            category=Category.SLANG,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            score=1.0,
            is_correct=True,
            model_response="A",
            target="A",
            latency_seconds=0.1,
            prompt_tokens=10,
            completion_tokens=2,
        ),
        EvaluationResult(
            item_id="2",
            category=Category.SLANG,
            eval_type=EvaluationType.MULTIPLE_CHOICE,
            score=0.0,
            is_correct=False,
            model_response="B",
            target="A",
            latency_seconds=0.2,
            prompt_tokens=10,
            completion_tokens=2,
        ),
        EvaluationResult(
            item_id="3",
            category=Category.PROCEDURES,
            eval_type=EvaluationType.EXACT_MATCH,
            score=1.0,
            is_correct=True,
            model_response="SAT",
            target="SAT",
            latency_seconds=0.3,
            prompt_tokens=15,
            completion_tokens=3,
        ),
    ]

    metrics = aggregate_metrics(results)
    assert metrics.total_items == 3
    assert metrics.correct_items == 2
    assert metrics.accuracy == round(2 / 3, 4)
    assert metrics.category_scores[Category.SLANG.value] == 0.5
    assert metrics.category_scores[Category.PROCEDURES.value] == 1.0
    assert metrics.total_prompt_tokens == 35
    assert metrics.total_completion_tokens == 7


def test_evaluation_engine_end_to_end() -> None:
    """Ensure EvaluationEngine runs items through runner and computes metrics."""
    item_mcq = BenchmarkItem(
        id="engine-mcq",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        prompt="¿Qué significa cámara?",
        choices={"A": "Foto", "B": "De acuerdo"},
        target="B",
    )
    runner = MockRunner(default_response="B")
    engine = EvaluationEngine(runner=runner)

    res = engine.evaluate_item(item_mcq)
    assert res.is_correct is True
    assert res.score == 1.0
    assert res.latency_seconds > 0

    # Test running benchmark list
    results, metrics = engine.run_benchmark([item_mcq])
    assert len(results) == 1
    assert metrics.accuracy == 1.0


def test_format_eval_prompt() -> None:
    """Ensure prompt formatting adds choices for multiple choice items."""
    item = BenchmarkItem(
        id="prompt-test",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        prompt="Pregunta",
        choices={"A": "Op 1", "B": "Op 2"},
        target="A",
    )
    formatted = format_eval_prompt(item)
    assert "A) Op 1" in formatted
    assert "B) Op 2" in formatted


def test_evaluation_engine_exact_match_and_rubric() -> None:
    """Ensure engine properly routes exact match and rubric items."""
    item_em = BenchmarkItem(
        id="em-1",
        category=Category.PROCEDURES,
        eval_type=EvaluationType.EXACT_MATCH,
        prompt="¿Nombre del documento?",
        target="CURP",
    )
    item_rubric = BenchmarkItem(
        id="rubric-1",
        category=Category.ALBUR,
        eval_type=EvaluationType.RUBRIC_JUDGED,
        prompt="Explica el albur",
        target="Explicación esperada",
    )

    runner = MockRunner(default_response="CURP")
    engine_no_judge = EvaluationEngine(runner=runner)

    res_em = engine_no_judge.evaluate_item(item_em)
    assert res_em.is_correct is True

    with pytest.raises(EvaluatorError, match="requires a judge runner"):
        engine_no_judge.evaluate_item(item_rubric)

    # With judge runner
    judge = MockRunner(default_response='{"score": 4, "justification": "Bien"}')
    engine_with_judge = EvaluationEngine(runner=runner, judge_runner=judge)
    res_rubric = engine_with_judge.evaluate_item(item_rubric)
    assert res_rubric.is_correct is True
    assert res_rubric.score == 0.75


def test_aggregate_metrics_empty() -> None:
    """Ensure aggregate_metrics returns default zeroed metrics for empty list."""
    metrics = aggregate_metrics([])
    assert metrics.total_items == 0
    assert metrics.accuracy == 0.0


def test_evaluator_type_mismatches() -> None:
    """Ensure evaluators reject items with invalid eval_type."""
    item_mcq = BenchmarkItem(
        id="mcq-mismatch",
        category=Category.SLANG,
        eval_type=EvaluationType.MULTIPLE_CHOICE,
        prompt="P",
        choices={"A": "1", "B": "2"},
        target="A",
    )

    em_eval = ExactMatchEvaluator()
    with pytest.raises(EvaluatorError, match="not an exact match item"):
        em_eval.evaluate(item_mcq, "A")

    judge = MockRunner(default_response="5")
    rubric_eval = RubricJudgeEvaluator(judge)
    with pytest.raises(EvaluatorError, match="not a rubric judged item"):
        rubric_eval.evaluate(item_mcq, "A")
