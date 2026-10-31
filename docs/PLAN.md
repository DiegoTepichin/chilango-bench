# chilango-bench: plan to v1.0

## Where v0.1 left off

The harness (dataset schema, runners, evaluators, CLI, leaderboard) works end to end with a 40-item multiple-choice seed set. An audit found these gaps:

- The multiple-choice extractor falls back to "first isolated letter", which matches the Spanish words *a*, *e*, *o*, *y* and produces false positives.
- The judge silently scores 1 when its output cannot be parsed.
- Run reports do not record the dataset hash, generation settings or prompt template, so two runs cannot be proven comparable; corrupt reports are skipped without a word.
- `--provider auto` guesses the provider from the model name.
- No real model has been run and the dataset has not been reviewed by a person.

## Goal for v1.0

A benchmark someone else can run, reproduce and trust:

1. Every score is reproducible from a JSON report that pins the dataset hash, the prompt template version and the generation settings.
2. Grading is strict: an answer the grader cannot read is wrong (multiple choice) or an explicit error (judge), never a guess.
3. Scores come with uncertainty (bootstrap 95 % intervals) and a chance baseline.
4. A larger, original dataset (about 160 items) under CC BY 4.0, with a canary string and a review workflow.
5. Real results for small open models run locally with Ollama.

## Scope

| Area | v1.0 |
|---|---|
| Evaluators | Strict multiple-choice extraction; exact match on normalized text; judge returns `judge_error` instead of a fake score. |
| Reports | Pydantic models; dataset SHA-256; run settings; benchmark and template versions; strict loading with clear errors. |
| Metrics | Accuracy per category with bootstrap CIs; unresolved-answer rate; chance baseline. |
| Runners | `mock`, `openai` (any OpenAI-compatible endpoint, `--base-url`), `ollama` preset; per-item runner errors recorded, not fatal. |
| Dataset | `datasets/v1/chilango-bench.jsonl`: multiple choice (balanced keys), exact match and rubric items across the four categories; explanation per item; canary; CC BY 4.0. |
| Review | `chilango-bench review` walks unreviewed items and records accept / reject / skip in the file. |
| Leaderboard | Markdown table with CIs, generated from committed reports in `results/`. |
| Docs | `docs/METHODOLOGY.md`, README with real results. |

## Scope after v1.0

| Area | Added |
|---|---|
| Phantom slang | `datasets/phantom/phantom-slang.jsonl`, `phantom_word` evaluator, fabrication metrics and leaderboard table. |

## Out of scope

Web leaderboard, automated third-party submissions, other dialects, fine-tuning, audio.

## Milestones (one branch and PR each, real CI)

| # | Branch | Content |
|---|---|---|
| M0 | `chore/v1-plan` | This plan, CI and tooling alignment. |
| M1 | `fix/strict-grading` | Multiple-choice extraction, judge errors. |
| M2 | `feat/reproducible-reports` | Report models, hashes, settings, bootstrap CIs, strict loading. |
| M3 | `feat/runners` | Provider presets, base URL, per-item errors, progress. |
| M4 | `feat/dataset-v1` | Schema additions, v1 dataset, licence, canary, review command. |
| M5 | `feat/leaderboard` | Real Ollama runs, leaderboard with CIs, methodology. |
| M6 | `docs/v1` | README, changelog, release 1.0.0. |

## Test strategy

Offline only: mock runners and recorded HTTP responses (`respx`). Grading edge cases (Spanish articles, verbose answers, refusals) get dedicated tests. Bootstrap is tested with fixed seeds.

## Launch checklist

- [x] CI green on main.
- [x] Leaderboard built only from committed reports.
- [x] README states the dataset review status.
- [ ] Tag `v1.0.0`.
