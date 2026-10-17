# chilango-bench

**A reproducible benchmark for evaluating LLMs on Mexican Spanish** — slang, cultural literacy, civic procedures, and wordplay (*albur*).

[![CI](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](https://github.com/DiegoTepichin/chilango-bench)
[![mypy strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Status: pre-release.** The harness works end to end, but the seed dataset has not been human-reviewed yet and no real model results have been published. Do not cite scores from this repository yet.

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
        R1["🌐 OpenAIRunner\nany OpenAI-compatible endpoint"]
        R2["🧪 MockRunner\n100% Offline CI"]
    end

    R1 -.-> E
    R2 -.-> E

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

The seed dataset (`v0.1`) ships with 40 multiple-choice items, 10 per category, with answer keys spread evenly across A–D. Every item is marked `review_status: unreviewed` until a human verifies it.

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

# OpenAI-compatible endpoint (set OPENAI_BASE_URL for providers other than OpenAI)
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

## Leaderboard

No results yet. Real model runs will be published here, each backed by its JSON run report, once the seed dataset has been reviewed.

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
