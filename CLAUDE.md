@../briefs/chilango-bench.md

# chilango-bench

## What it is

A benchmark of large language models on Mexican Spanish: slang, cultural context, government procedures and wordplay (albur). A curated dataset plus a reproducible leaderboard that runs against local and API-hosted models.

## Who it is for

Developers and companies choosing an LLM for products in Mexico, and NLP researchers working on Spanish.

## Scope (v0.1)

To be defined in `docs/PLAN.md` during the planning session.

Anything else is out of scope until v0.1 ships.

## Code standards

- Python 3.11+ (CI matrix: 3.11, 3.12, 3.13, 3.14). Dependencies and environments managed with `uv`.
- Strict typing: `mypy --strict` clean, no untyped public functions, no `Any` without a reason.
- Lint and format with `ruff`.
- Tests with `pytest`. No network calls in tests: use recorded or fixture data.
- Small functions, clear names, no dead code, no comments that restate the code.
- Configuration and secrets only through environment variables, documented in `.env.example`.
- Conventional Commits in English, one logical change per commit.
- README and docs describe only what exists and has been run.

## Commands

- `uv sync`: Install project and development dependencies.
- `uv run ruff check .`: Lint Python source files.
- `uv run ruff format --check .`: Verify code formatting.
- `uv run mypy .`: Run strict static type checking.
- `uv run pytest`: Execute test suite offline.
- `uv run chilango-bench --version`: Display package version.
- `uv run chilango-bench validate datasets/v0.1/seed.jsonl`: Validate JSONL dataset schema and categories.
- `uv run chilango-bench eval --dataset <path> --model <model> [--provider mock|openai] [--output <report.json>]`: Evaluate model against benchmark.
- `uv run chilango-bench leaderboard --results-dir <dir>`: Generate markdown leaderboard table from report artifacts.

## Structure

Defined in `docs/PLAN.md`. Core package lives in `src/chilango_bench`, tests in `tests/`, datasets in `datasets/`.
