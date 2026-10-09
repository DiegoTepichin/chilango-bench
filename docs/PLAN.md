# chilango-bench: v0.1 Architecture and Implementation Plan

## 1. Executive Summary

`chilango-bench` is an open-source evaluation benchmark designed to assess Large Language Models (LLMs) on their understanding and generation of Mexican Spanish, specifically focusing on the dialectal nuances of central Mexico (CDMX and surrounding areas).

Standard NLP benchmarks evaluate generic Latin American or Castilian Spanish, frequently missing:
1. **Chilangismos and Mexican Slang**: Rapidly evolving colloquialisms, idioms, and register shifts.
2. **Cultural Context**: Local geography, public transportation (Metro, Metrobús), daily customs, social dynamics, and pop-culture references.
3. **Bureaucratic and Civic Procedures**: Real-world citizen navigation of government systems (SAT, CURP, RFC, CDMX digital driver's license, verificentros, civil registries).
4. **Wordplay and Double Entendre (Albur)**: Complex contextual wordplay, sexual innuendo detection, and avoidance of inadvertent traps without gratuitous refusal or offensive generation.

The v0.1 release delivers a reproducible, lightweight, and extensible CLI-driven benchmark pipeline that evaluates both local and API-hosted models against a curated, versioned dataset.

---

## 2. Guiding Architectural Principles

- **Deterministic & Offline-First Testing**: Test suites must never make external network calls. All CI and local test suites run 100% offline using recorded fixtures or mock runners.
- **Strict Typing & Clean Contracts**: The entire codebase enforces `mypy --strict`. Public APIs and data models must have explicit types, zero implicit `Any`, and strict Pydantic v2 validation.
- **Reproducibility**: Evaluations must produce deterministic, versioned output artifacts (JSON result bundles containing exact prompts, responses, scores, seeds, and metadata).
- **Extensible Runner Pattern**: Model interaction uses a unified provider adapter interface (`BaseRunner`), decoupling evaluation logic from specific API SDKs or local model runtimes.
- **Minimalist Dependencies**: Avoid unnecessary frameworks. Rely on core Python standards, `uv` for dependency management, `pydantic` for data schemas, `httpx` for API transport, and standard reporting tools.

---

## 3. Scope for v0.1

### In Scope
- **Core Data Schema**: Strongly typed Pydantic models for benchmark test cases, supporting multiple evaluation types:
  - `multiple_choice`: Deterministic evaluation with single correct option.
  - `exact_match` / `constrained_generation`: Short answer verification with normalization.
  - `rubric_judged`: Open-ended explanations scored against rubric criteria (1–5 scale).
- **Four Core Categories**:
  - `slang`: Vocabulary, idioms, pragmatic nuance.
  - `cultural_context`: CDMX transit, geography, cultural literacy.
  - `procedures`: Mexican government bureaucracy and administrative workflows.
  - `albur`: Innuendo recognition, intent identification, double entendre resolution.
- **Curated Seed Dataset**: A seed dataset of 40 validated items (10 per category) formatted as JSONL.
- **Runner Implementations**:
  - `MockRunner`: Offline, deterministic mock engine for CI and local verification.
  - `OpenAIRunner`: Universal OpenAI-compatible runner (supports OpenAI, Groq, Ollama, vLLM, and any OpenAI-spec endpoint).
- **Evaluation Engine**:
  - Exact match and choice-selection determinism evaluators.
  - LLM-as-a-judge rubric evaluator using standard prompt templates.
  - Aggregate metrics computation (category accuracy, latency, token consumption).
- **CLI Interface**:
  - Command to validate dataset integrity: `chilango-bench validate <dataset_path>`
  - Command to run evaluations: `chilango-bench eval --dataset <path> --model <model_id> --output <results.json>`
  - Command to generate leaderboards: `chilango-bench leaderboard --results-dir <dir>`
- **CI & Quality Tooling**:
  - Automated GitHub Actions matrix across Python 3.11, 3.12, 3.13, and 3.14.
  - Static analysis: `ruff check .`, `ruff format --check .`, `mypy --strict`.

### Out of Scope for v0.1 (Deferred to Future Milestones)
- Web application / interactive dashboard frontend (planned for v0.2).
- Crowdsourced annotation portal or human-in-the-loop voting (planned for v0.2).
- Audio / Speech dialect evaluation (planned for v0.3).
- Remote database backends (v0.1 relies exclusively on local JSONL and JSON artifacts).

---

## 4. Directory Structure

```text
chilango-bench/
├── .github/
│   └── workflows/
│       └── ci.yml
├── datasets/
│   └── v0.1/
│       ├── seed.jsonl
│       └── schema.json
├── docs/
│   ├── PLAN.md
│   └── ARCHITECTURE.md
├── src/
│   └── chilango_bench/
│       ├── __init__.py
│       ├── py.typed
│       ├── cli.py
│       ├── config.py
│       ├── core/
│       │   ├── exceptions.py
│       │   └── types.py
│       ├── dataset/
│       │   ├── loader.py
│       │   ├── models.py
│       │   └── validator.py
│       ├── runners/
│       │   ├── base.py
│       │   ├── factory.py
│       │   ├── mock.py
│       │   └── openai.py
│       ├── evaluators/
│       │   ├── base.py
│       │   ├── deterministic.py
│       │   └── judge.py
│       └── reporting/
│           ├── leaderboard.py
│           └── models.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── sample_dataset.jsonl
│   ├── test_cli.py
│   ├── test_dataset.py
│   ├── test_evaluators.py
│   ├── test_leaderboard.py
│   └── test_runners.py
├── .env.example
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── LICENSE
├── pyproject.toml
└── README.md
```

---

## 5. Phased Milestones

| Milestone | Deliverables | Verification Criteria |
|---|---|---|
| **M1: Scaffolding & Tooling** | `pyproject.toml`, tool configurations (`ruff`, `mypy --strict`, `pytest`), `.env.example`, `.github/workflows/ci.yml`. | `uv run ruff check .`, `uv run mypy .`, `uv run pytest` pass cleanly in local and CI matrix. |
| **M2: Dataset Schema & Validation** | Pydantic v2 schemas (`BenchmarkItem`, `EvaluationType`, `Category`), JSONL loader/validator, curated `datasets/v0.1/seed.jsonl`. | 100% test coverage on schema validation, invalid data rejection, and seed dataset parsing. |
| **M3: Model Runners & Offline Adapters** | `BaseRunner`, `MockRunner` (fixtures/rule-based), `OpenAIRunner` (httpx with retry & timeout), runner factory. | Unit tests using offline mocks verifying retry policies, token extraction, and response normalization. |
| **M4: Evaluation Engine & Metrics** | Exact match evaluator, multiple choice evaluator, rubric judge evaluator, metrics aggregator. | Fixture-based tests verifying deterministic scoring and metric accuracy. |
| **M5: CLI & Leaderboard Reporting** | CLI entrypoints (`validate`, `eval`, `leaderboard`), JSON report exporter, Markdown leaderboard table formatter. | CLI smoke tests testing end-to-end runs with `MockRunner` generating reports. |
| **M6: Verification & v0.1 Release** | End-to-end integration run, documentation update (`CLAUDE.md`, `README.md`), version tagging. | All linters, formatters, type checkers, and test suites passing across Python 3.11–3.14. |

---

## 6. Engineering Conventions & Code Quality Standards

1. **Strict Typing**: Every function signature must be fully annotated. No `Any` without an explicit, documented reason.
2. **Deterministic Tests**: No real API keys or external endpoints in `pytest`. Use mock runners or fixtures.
3. **Environment Configuration**: Secrets and configuration must only be read from environment variables via `chilango_bench.config`.
4. **Git Discipline**:
   - Branch naming: `feat/<name>`, `fix/<name>`, `chore/<name>`, `docs/<name>`.
   - Conventional Commits in English (`feat: ...`, `chore: ...`, `docs: ...`).
   - Clean linear history: merge locally with `git merge --no-ff`.
