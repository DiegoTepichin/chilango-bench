# chilango-bench

**A reproducible benchmark for evaluating LLMs on Mexican Spanish** — slang, cultural literacy, civic procedures, and wordplay (*albur*).

[![CI](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](https://github.com/DiegoTepichin/chilango-bench)
[![mypy strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why

Standard Spanish NLP benchmarks evaluate formal Castilian or generic Latin American Spanish. They miss the pragmatic reality of Mexican Spanish — spoken by over 130 million people. An LLM failing to distinguish *"¡cámara!"* (agreement/goodbye) from a camera apparatus, or hallucinating SAT procedures vs. RENAPO workflows, breaks real-world trust.

`chilango-bench` provides a deterministic, reproducible evaluation suite to score and compare models before deploying them in Mexico.

## Architecture

```mermaid
flowchart LR
    D[("📁 JSONL Dataset\nseed.jsonl")] --> V["🛡️ Schema Validator\nPydantic v2"]
    V --> E["⚙️ Evaluation Engine"]

    subgraph Runners ["Model Runners"]
        R1["🌐 OpenAIRunner\nOpenAI · Groq · vLLM"]
        R2["💻 Local Runner\nOllama · LM Studio"]
        R3["🧪 MockRunner\n100% Offline CI"]
    end

    R1 -.-> E
    R2 -.-> E
    R3 -.-> E

    E --> J{"Grading\nEngine"}
    J -->|Deterministic| MC["Multiple Choice\n& Exact Match"]
    J -->|Qualitative| RB["LLM-as-a-Judge\nRubric 1–5"]

    MC --> A["📊 Metrics\nAccuracy · Latency · Tokens"]
    RB --> A

    A --> OUT1["📄 JSON Run Bundle\nresults/*.json"]
    A --> OUT2["🏆 Markdown Leaderboard"]
```

## Benchmark dimensions

| Category | Description |
| :--- | :--- |
| **Slang** | Colloquial lexicon, pragmatic discourse markers, register shifts (*chilangismos*) |
| **Cultural context** | CDMX Metro system, traditions, urban geography, food |
| **Procedures** | Real-world admin navigation: SAT, CURP, RFC, e.firma, licencias |
| **Albur** | Wordplay, innuendo detection, double entendre resolution |

The seed dataset (`v0.1`) ships with 40 curated items — 10 per category.

## Quickstart

Requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/DiegoTepichin/chilango-bench.git
cd chilango-bench
uv sync
```

### Validate dataset

```bash
uv run chilango-bench validate datasets/v0.1/seed.jsonl
```

### Run evaluation

```bash
# Offline mock run (no API key needed)
uv run chilango-bench eval \
  --dataset datasets/v0.1/seed.jsonl \
  --model mock-model \
  --provider mock \
  --output results/mock-run.json

# Local model via Ollama
OPENAI_BASE_URL="http://localhost:11434/v1" uv run chilango-bench eval \
  --dataset datasets/v0.1/seed.jsonl \
  --model llama3.2 \
  --output results/llama3.json

# Cloud endpoint (OpenAI / Groq / any OpenAI-compatible API)
export OPENAI_API_KEY="your-api-key"
uv run chilango-bench eval \
  --dataset datasets/v0.1/seed.jsonl \
  --model gpt-4o-mini \
  --output results/gpt-4o-mini.json
```

### Generate leaderboard

```bash
uv run chilango-bench leaderboard --results-dir results
```

## Leaderboard (v0.1 seed)

| Rank | Model | Overall | Slang | Culture | Procedures | Albur |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `gpt-4o` | 92.5% | 90% | 100% | 100% | 80% |
| 2 | `llama-3.3-70b` | 85.0% | 90% | 90% | 90% | 70% |
| 3 | `gpt-4o-mini` | 82.5% | 80% | 90% | 90% | 70% |
| 4 | `llama-3.1-8b` | 67.5% | 70% | 70% | 80% | 50% |

> Results on the curated seed dataset. Submit a PR to add your model.

## Development

```bash
uv run ruff check .          # lint
uv run ruff format --check . # format
uv run mypy .                # type check
uv run pytest                # test suite (100% offline)
```

All checks must pass before merging. CI runs the full matrix across Python 3.11–3.14.

## License

[MIT](LICENSE)
