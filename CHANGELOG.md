# Changelog

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Phantom slang dataset: 18 invented words and 12 real controls, with a `phantom_word` evaluator, fabrication metrics and a leaderboard table.
- Results for `llama3.2:3b`, `qwen2.5:1.5b` and `gemma3:1b` on phantom slang.

## [1.0.0] - 2026-10-26

### Added

- v1 dataset: 168 original items (134 multiple choice, 23 exact match, 11 rubric) under CC BY 4.0, with explanations, review status and a canary GUID.
- `chilango-bench review` to accept or reject items from the terminal; rejected items are never evaluated and `eval --accepted-only` scores only accepted ones.
- `ollama` provider, `--base-url`, `--temperature`, `--max-tokens`, `--limit` and per-item progress.
- Run reports (Pydantic) with dataset SHA-256, generation settings, prompt template version and judge model.
- 95 % bootstrap confidence intervals overall, per category and per evaluation type.
- Option-length bias check in `validate`.
- Results for `llama3.2:3b`, `qwen2.5:1.5b`, `gemma3:1b` and an always-B baseline; `docs/METHODOLOGY.md`.

### Changed

- Multiple-choice grading accepts only explicit answers; a loose letter inside a sentence no longer counts.
- Leaderboard groups runs by dataset hash, item count, prompt template and judge, and shows confidence intervals.
- Providers are explicit (`mock`, `openai`, `ollama`); `--provider auto` was removed.

### Fixed

- Unparseable or out-of-range judge output is an error instead of a silent score of 1.
- Runner failures are recorded per item instead of aborting the run.
- Invalid report files are reported instead of being skipped silently.
- Distractors rewritten so the correct option is no longer the longest in most items.

### Removed

- The v0.1 seed file (its 40 items are part of v1).

## [0.1.0] - 2026-10-09

Initial harness and 40-item seed set.

[1.0.0]: https://github.com/DiegoTepichin/chilango-bench/releases/tag/v1.0.0
[0.1.0]: https://github.com/DiegoTepichin/chilango-bench/commits/main
