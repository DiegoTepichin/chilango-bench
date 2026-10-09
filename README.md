# chilango-bench

A benchmark evaluating Large Language Models on Mexican Spanish nuances: slang, cultural context, bureaucratic procedures, and wordplay (*albur*).

## Project Status

v0.1 core implementation completed:
- Strongly typed dataset schema and 40 curated seed items across 4 categories.
- Unified model runner abstraction (`MockRunner` and `OpenAIRunner`).
- Deterministic and rubric-based evaluation engine.
- Reproducible CLI commands (`validate`, `eval`, `leaderboard`).

See [PLAN.md](docs/PLAN.md) for architectural details.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python environment and dependency management.

```bash
# Install dependencies
uv sync

# Run checks
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

## CLI Usage

```bash
# Validate dataset integrity
uv run chilango-bench validate datasets/v0.1/seed.jsonl

# Run benchmark evaluation
uv run chilango-bench eval --dataset datasets/v0.1/seed.jsonl --model mock-model --provider mock --output results/mock.json

# Generate leaderboard from results directory
uv run chilango-bench leaderboard --results-dir results
```
