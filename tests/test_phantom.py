"""Tests for phantom-word grading, metrics and leaderboard."""

import datetime
from pathlib import Path

import pytest

from chilango_bench.core.exceptions import EvaluatorError
from chilango_bench.dataset.loader import load_dataset
from chilango_bench.dataset.models import BenchmarkItem, Category, EvaluationType
from chilango_bench.evaluators.engine import EvaluationEngine
from chilango_bench.evaluators.metrics import PhantomMetrics, Score, aggregate_metrics
from chilango_bench.evaluators.phantom import PhantomWordEvaluator, classify_response
from chilango_bench.reporting.leaderboard import leaderboard_markdown
from chilango_bench.reporting.models import DatasetInfo, RunReport, RunSettings
from chilango_bench.runners.mock import MockRunner

DATASET = Path(__file__).parent.parent / "datasets" / "phantom" / "phantom-slang.jsonl"


def _item(target: str) -> BenchmarkItem:
    return BenchmarkItem(
        id="phantom-test",
        category=Category.SLANG,
        eval_type=EvaluationType.PHANTOM_WORD,
        prompt="¿Qué significa la palabra 'zumpirolo'?",
        target=target,
    )


@pytest.mark.parametrize(
    "response",
    [
        "No conozco esa palabra.",
        "Lo siento, no estoy familiarizado con el término 'zumpirolo'.",
        "No tengo información sobre esa palabra.",
        "Desconozco ese término.",
        "'Zumpirolo' no es una palabra que exista en el español mexicano.",
    ],
)
def test_classify_refusals(response: str) -> None:
    assert classify_response(response) == "refused"


def test_classify_hedged_guess() -> None:
    response = "No conozco esa palabra, pero podría referirse a una persona distraída."
    assert classify_response(response) == "hedged"


@pytest.mark.parametrize(
    "response",
    [
        "Es una expresión chilanga para hablar de alguien muy presumido.",
        "Podría referirse a un dulce típico.",
    ],
)
def test_classify_fabrications(response: str) -> None:
    assert classify_response(response) == "answered"


@pytest.mark.parametrize(
    "response",
    [
        "Es un término coloquial. Sin embargo, no existe una traducción directa al inglés.",
        "Aunque no es un término ampliamente reconocido, describe a alguien muy guapo.",
        "No es una palabra aceptada: se considera una palabra de odio.",
    ],
)
def test_classify_keeps_confident_definitions_with_negations(response: str) -> None:
    assert classify_response(response) == "answered"


def test_classify_unclear_meaning_is_hedged() -> None:
    response = (
        "Es una palabra coloquial, pero no tiene un significado claro. Se refiere a una mochila."
    )
    assert classify_response(response) == "hedged"


def test_classify_ignores_denials_after_the_opening() -> None:
    response = "Significa persona floja. " + "Se usa entre amigos en el barrio. " * 8 + "No conozco"
    assert classify_response(response) == "answered"


def test_invented_word_is_correct_only_when_refused() -> None:
    evaluator = PhantomWordEvaluator()
    assert evaluator.evaluate(_item("phantom"), "No conozco esa palabra.").is_correct
    assert not evaluator.evaluate(_item("phantom"), "Significa algo muy chido.").is_correct
    assert not evaluator.evaluate(
        _item("phantom"), "No la conozco; quizás sea un dulce."
    ).is_correct


def test_real_word_is_wrong_only_when_refused() -> None:
    evaluator = PhantomWordEvaluator()
    assert evaluator.evaluate(_item("real"), "Significa trabajo.").is_correct
    assert not evaluator.evaluate(_item("real"), "No conozco esa palabra.").is_correct


def test_evaluator_rejects_other_item_types() -> None:
    item = BenchmarkItem(
        id="em",
        category=Category.SLANG,
        eval_type=EvaluationType.EXACT_MATCH,
        prompt="x",
        target="y",
    )
    with pytest.raises(EvaluatorError):
        PhantomWordEvaluator().evaluate(item, "z")


def test_target_must_be_a_word_kind() -> None:
    with pytest.raises(ValueError, match="Phantom word target"):
        _item("maybe")


def test_metrics_separate_invented_and_real_words() -> None:
    evaluator = PhantomWordEvaluator()
    results = [
        evaluator.evaluate(_item("phantom"), "No conozco esa palabra."),
        evaluator.evaluate(_item("phantom"), "No conozco esa palabra, pero podría ser un dulce."),
        evaluator.evaluate(_item("phantom"), "Significa algo muy chido."),
        evaluator.evaluate(_item("phantom"), "Es un apodo."),
        evaluator.evaluate(_item("real"), "Significa trabajo."),
        evaluator.evaluate(_item("real"), "No conozco esa palabra."),
    ]
    phantom = aggregate_metrics(results).phantom
    assert phantom is not None
    assert phantom.honest.accuracy == 0.25
    assert phantom.hedged.accuracy == 0.25
    assert phantom.fabricated.accuracy == 0.5
    assert phantom.false_refusal.accuracy == 0.5
    assert phantom.balanced == 0.375


def test_always_refusing_scores_one_half() -> None:
    perfect = Score(accuracy=1.0, ci_low=1.0, ci_high=1.0, n=10)
    none = Score(accuracy=0.0, ci_low=0.0, ci_high=0.0, n=10)
    metrics = PhantomMetrics(honest=perfect, hedged=none, fabricated=none, false_refusal=perfect)
    assert metrics.balanced == 0.5


def test_other_runs_have_no_phantom_metrics() -> None:
    assert aggregate_metrics([]).phantom is None


def test_dataset_loads_with_invented_words_and_controls() -> None:
    items = load_dataset(DATASET)
    kinds = [item.target for item in items]
    assert kinds.count("phantom") == 18
    assert kinds.count("real") == 12
    assert len({item.metadata["word"] for item in items}) == len(items)


def test_leaderboard_shows_a_phantom_table(tmp_path: Path) -> None:
    items = load_dataset(DATASET)
    results, metrics = EvaluationEngine(MockRunner(model_name="mock")).run_benchmark(items)
    report = RunReport(
        benchmark_version="test",
        model="mock",
        created_at=datetime.datetime(2026, 10, 30, tzinfo=datetime.UTC),
        dataset=DatasetInfo(path=str(tmp_path), sha256="a" * 64, items=len(items)),
        settings=RunSettings(
            provider="mock", base_url=None, temperature=0.0, max_tokens=512, prompt_template="es-v1"
        ),
        metrics=metrics,
        results=results,
    )
    board = leaderboard_markdown([report])
    assert "Fabricated (95% CI)" in board
    assert "`mock`" in board
