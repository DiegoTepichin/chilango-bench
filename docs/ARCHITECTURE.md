# chilango-bench: Architecture Reference

This document describes the internal architecture of `chilango-bench` as implemented in v0.1. For the project roadmap and milestone plan, see [`PLAN.md`](./PLAN.md).

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI  (chilango_bench.cli)                                      │
│  validate │ eval │ leaderboard                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │  EvaluationEngine      │  chilango_bench.evaluators.engine
         │  (orchestration)       │
         └──┬────────────┬────────┘
            │            │
   ┌────────▼──┐   ┌─────▼────────────────┐
   │  Runners  │   │  Evaluators          │
   │  (I/O)    │   │  (scoring logic)     │
   └────────┬──┘   └─────┬────────────────┘
            │             │
   ┌────────▼──┐   ┌──────▼──────────────────────┐
   │ BaseRunner│   │  MultipleChoiceEvaluator     │
   │ MockRunner│   │  ExactMatchEvaluator         │
   │ OpenAI   │   │  RubricJudgeEvaluator        │
   │ Runner   │   └─────────────────────────────┘
   └───────────┘
            │
   ┌────────▼──────────────────────┐
   │  Dataset (Pydantic v2 models) │
   │  BenchmarkItem · Category     │
   │  EvaluationType · Rubric      │
   └───────────────────────────────┘
            │
   ┌────────▼──────────────────────┐
   │  Reporting                    │
   │  EvalReport (JSON artifact)   │
   │  Leaderboard (Markdown table) │
   └───────────────────────────────┘
```

---

## 2. Package Layout

```
src/chilango_bench/
├── __init__.py          # Package metadata (version)
├── py.typed             # PEP 561 marker
├── cli.py               # Typer-based CLI entrypoints
├── config.py            # Pydantic Settings – env var access
├── core/
│   ├── exceptions.py    # Domain exception hierarchy
│   └── types.py         # Shared type aliases
├── dataset/
│   ├── models.py        # BenchmarkItem, Category, EvaluationType, RubricCriterion
│   ├── loader.py        # JSONL file loader (returns List[BenchmarkItem])
│   └── validator.py     # Schema validation with human-readable error reporting
├── runners/
│   ├── base.py          # BaseRunner ABC + RunnerResponse dataclass
│   ├── mock.py          # MockRunner – offline, deterministic, no I/O
│   ├── openai.py        # OpenAIRunner – httpx, retry, timeout, OpenAI-compatible
│   └── factory.py       # create_runner() – provider dispatch function
├── evaluators/
│   ├── base.py          # BaseEvaluator ABC + EvaluationResult dataclass
│   ├── deterministic.py # MultipleChoiceEvaluator, ExactMatchEvaluator, helpers
│   ├── judge.py         # RubricJudgeEvaluator – LLM-as-a-judge with JSON parsing
│   ├── engine.py        # EvaluationEngine – orchestrates runner + evaluator routing
│   └── metrics.py       # aggregate_metrics() – accuracy, latency, token totals
└── reporting/
    ├── models.py        # EvalReport Pydantic model (JSON artifact schema)
    └── leaderboard.py   # Markdown table generator from result directories
```

---

## 3. Core Data Flow

### 3.1 Dataset Loading

```
seed.jsonl (JSONL file)
    → dataset.loader.load_dataset()
    → List[BenchmarkItem]   (validated by Pydantic v2)
```

Each `BenchmarkItem` carries:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier |
| `category` | `Category` | `slang \| cultural_context \| procedures \| albur` |
| `eval_type` | `EvaluationType` | `multiple_choice \| exact_match \| rubric_judged` |
| `prompt` | `str` | The prompt shown to the evaluated model |
| `choices` | `dict[str, str] \| None` | Options for MCQ items |
| `target` | `str \| list[str]` | Ground truth (single string or acceptable variants) |
| `rubric` | `list[RubricCriterion] \| None` | Scoring rubric for judge items |

### 3.2 Evaluation Pipeline

```
List[BenchmarkItem]
    → EvaluationEngine.run_benchmark()
        ├── for each item:
        │   ├── format_eval_prompt(item)        # inject choices if MCQ
        │   ├── runner.generate(prompt)         # call model (or mock)
        │   └── evaluator.evaluate(item, text)  # score response
        │       ├── MultipleChoiceEvaluator     # extract_choice_key() + compare
        │       ├── ExactMatchEvaluator         # normalize_text() + fuzzy match
        │       └── RubricJudgeEvaluator        # judge_runner.generate() + parse JSON
        └── aggregate_metrics(results)          # accuracy, latency, tokens per category
    → (List[EvaluationResult], BenchmarkMetrics)
```

### 3.3 Reporting

```
(List[EvaluationResult], BenchmarkMetrics)
    → EvalReport (Pydantic model)
    → report.json (JSON artifact on disk)

List[report.json files in results-dir]
    → leaderboard.generate_leaderboard_table()
    → Markdown table printed to stdout
```

---

## 4. Runner Interface

All runners implement `BaseRunner`. Adding a new provider means subclassing it:

```python
class BaseRunner(ABC):
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> RunnerResponse: ...
```

`RunnerResponse` is a frozen dataclass with `text`, `prompt_tokens`, `completion_tokens`,
`latency_seconds`, `model_name`, and `raw_response`.

### Runner selection via factory

```python
from chilango_bench.runners.factory import create_runner

runner = create_runner(model="gpt-4o-mini", provider="openai", api_key="sk-...")
runner = create_runner(model="llama3", provider="openai", base_url="http://localhost:11434/v1")
runner = create_runner(model="mock-ci", provider="mock")
```

The `"auto"` provider selects `MockRunner` when the model name starts with `"mock"`,
and `OpenAIRunner` otherwise.

---

## 5. Evaluator Routing

`EvaluationEngine` dispatches to the correct evaluator based on `item.eval_type`:

| `eval_type` | Evaluator | Requires judge runner? |
|---|---|---|
| `multiple_choice` | `MultipleChoiceEvaluator` | No |
| `exact_match` | `ExactMatchEvaluator` | No |
| `rubric_judged` | `RubricJudgeEvaluator` | Yes (`EvaluatorError` if absent) |

Scores are normalized to `[0.0, 1.0]`. Rubric scores (1–5) are mapped as `(raw - 1) / 4`.

---

## 6. Configuration

All runtime configuration is read from environment variables via
`chilango_bench.config.get_settings()` (Pydantic `BaseSettings`). No secrets are
hard-coded. See [`.env.example`](../.env.example) for the full list of supported variables.

---

## 7. Exception Hierarchy

```
Exception
└── ChilangoError            (base for all domain errors)
    ├── DatasetError         (malformed JSONL, schema violations)
    ├── RunnerError          (network failures, timeouts, API errors)
    ├── EvaluatorError       (type mismatches, missing judge runner)
    └── ConfigurationError   (missing required environment variables)
```

---

## 8. Testing Strategy

All tests run **100% offline**. The table below summarizes coverage by module:

| Module | Strategy |
|---|---|
| `dataset` | Valid/invalid JSONL fixtures, Pydantic validation edge cases |
| `runners` | `MockRunner` for unit logic; `respx` to intercept `httpx` for `OpenAIRunner` |
| `evaluators` | Pure unit tests with fixture `BenchmarkItem` instances |
| `engine` | End-to-end with `MockRunner` – no external I/O |
| `cli` | `main()` called directly with `tmp_path` for artifact outputs |

CI runs the full matrix across Python 3.11, 3.12, 3.13, and 3.14 via GitHub Actions.
