@../briefs/chilango-bench.md

# chilango-bench

## What it is

A benchmark of large language models on Mexican Spanish: slang, cultural context, government procedures and wordplay (albur). A curated dataset plus a reproducible leaderboard that runs against local and API-hosted models.

## Who it is for

Developers and companies choosing an LLM for products in Mexico, and NLP researchers working on Spanish.

## Scope

v1.0 scope lives in `docs/PLAN.md`; methodology in `docs/METHODOLOGY.md`. Ideas beyond it go to GitHub issues.

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

- `uv sync`: install the project and dev dependencies.
- `uv run ruff check .` / `uv run ruff format --check .` / `uv run mypy .` / `uv run pytest`: the CI checks.
- `uv run chilango-bench validate datasets/v1/chilango-bench.jsonl`: schema, counts, review status and option-length bias.
- `uv run chilango-bench eval -d <dataset> -m <model> -p mock|openai|ollama [--base-url] [--judge] [--limit] [--accepted-only] -o <report.json>`: run a model.
- `uv run chilango-bench review <dataset> --reviewer <handle>`: interactive item review.
- `uv run chilango-bench leaderboard -r results`: Markdown leaderboard from reports.

## Structure

Package in `src/chilango_bench` (`dataset/`, `runners/`, `evaluators/`, `reporting/`, `cli.py`), tests in `tests/`, dataset in `datasets/v1/`, published run reports in `results/`, scratch runs in the ignored `runs/`.
