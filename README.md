# chilango-bench

A benchmark evaluating Large Language Models on Mexican Spanish nuances: slang, cultural context, bureaucratic procedures, and wordplay (*albur*).

## Project Status

`chilango-bench` is currently under active development (Milestone 1: Project Scaffolding). See [PLAN.md](docs/PLAN.md) for architectural details and implementation milestones.

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
