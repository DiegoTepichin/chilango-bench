# Methodology

How chilango-bench builds its dataset, asks models, grades answers and reports scores. Everything described here is implemented in this repository; the section names point to the code.

## What is measured

Whether a language model understands the Spanish spoken in Mexico, with a focus on Mexico City:

| Category | Question it answers |
|---|---|
| `slang` | Does the model understand everyday slang and its pragmatics (what *ahorita* or *no hay pedo* actually mean in context)? |
| `cultural_context` | Does it know Mexico City life: transport, food, holidays, landmarks, shared memory? |
| `procedures` | Can it be trusted on government and labour procedures people actually ask about (CURP, RFC, SAT, INE, IMSS, aguinaldo)? |
| `albur` | Does it recognise the double-entendre game and respond appropriately, without being prudish or explicit? |

It does not measure general reasoning, other Spanish dialects or generation quality beyond the rubric items.

## Dataset

- 168 original items in `datasets/v1/chilango-bench.jsonl`, written for this benchmark (see `datasets/README.md`).
- Each item has an explanation of why the answer is right, so a reviewer can check it quickly.
- **Review**: every item starts as `unreviewed`. `chilango-bench review` records a reviewer's accept or reject decision in the file. Rejected items are never evaluated; `--accepted-only` restricts a run to accepted items. At the time of writing no item has been reviewed, so all published scores are preliminary.
- **Bias checks** (`dataset/validator.py`, enforced by tests): answer keys are balanced across A–D, and the correct option is the longest in 25 % of multiple-choice items, so neither "always B" nor "pick the longest" beats chance.
- **Contamination**: the file starts with a canary GUID that corpus builders can filter on. A private held-out split is not part of v1.

## Asking the model

`evaluators/engine.py`, template version `es-v1`:

- Multiple choice: the question, then `Opciones:` with one `X) text` line per option, then *"Responde únicamente con la letra de la opción correcta (ejemplo: A)."*
- Exact match and rubric: the question as written; exact-match prompts say how to answer (for example *"Responde con una sola palabra."*).
- No system prompt, temperature 0, at most 512 output tokens, one attempt per item. Runner failures are retried with backoff (`CHILANGO_MAX_RETRIES`); if they persist, the item is recorded with an `error` and the run continues.

Changing the template requires bumping `PROMPT_TEMPLATE`; reports carry the version and the leaderboard never ranks runs with different versions together.

## Grading

`evaluators/deterministic.py` and `evaluators/judge.py`.

**Multiple choice.** Only an explicit commitment counts:

1. a bare letter, optionally in parentheses or bold (`B`, `(b)`, `**C**`);
2. a leading letter followed by `)`, `.`, `:` or, for upper case, a space (`B) La Raza`);
3. a keyword followed by a letter (`la respuesta es C`, `opción B`, `inciso d`);
4. the full text of exactly one option (options shorter than four characters are ignored).

A loose letter inside a sentence never counts, because *a*, *e*, *o* and *y* are Spanish words. Two candidate letters (`A o C`) are ambiguous. Anything else is `UNRESOLVED` and graded wrong; the unresolved count is reported separately so format failures can be told apart from knowledge failures.

**Exact match.** Both sides are lower-cased, stripped of accents and punctuation, and whitespace-collapsed. The answer is correct if it equals an accepted answer or contains one as a whole word sequence (accepted answers of three or more characters, or containing a digit).

**Rubric.** The judge model receives the question, the reference answer, the criteria and the candidate answer, and must return JSON `{"score": 1-5, "justification": "..."}`. Scores map to 0–1 as `(score − 1) / 4`; 3 or more counts as correct. Output that is not valid JSON with an integer from 1 to 5 (or a `score: N` field) is recorded as a judge `error`, not as a score. The judge has not yet been validated against human grades, so rubric results are reported separately and are off by default (`--judge` enables them).

**Phantom word.** `evaluators/phantom.py` reads the first 200 characters of an open answer for refusal phrases and classifies it as `refused`, `hedged` (doubts, then guesses, or says the word has no clear meaning) or `answered`. An invented word is correct only when refused; a real control word is correct unless refused. The balanced score is the mean of both rates, so always refusing scores 50 %. Whether a definition of a real word is right is not graded.

These rules are deterministic but imperfect. They were corrected after reading every answer of the first run: three phrases such as *"no existe una traducción"* were wrongly read as doubt. The saved answers were regraded, not regenerated. Some cases stay debatable: an answer that calls a word "inventada" and then describes how people use it counts as `answered`, and so does one that refuses because it claims, falsely, that the word is offensive. Every answer is in the report so anyone can audit them.

## Metrics

`evaluators/metrics.py`.

- **Accuracy** = correct / graded items. Items with an `error` are excluded from the denominator and counted in `errored_items`.
- **95 % confidence intervals** come from a percentile bootstrap (2 000 resamples, fixed seed), overall, per category and per evaluation type. With ~40 items per category, intervals are wide (±15 points); differences inside them are not meaningful.
- Latency and token counts are reported but not ranked.

## Reproducibility

`reporting/models.py`. Every run writes a JSON report with the benchmark version, the dataset path, item count and SHA-256, the provider and endpoint, temperature, max tokens, prompt template, judge model, all metrics and every item's response and grade. The leaderboard (`reporting/leaderboard.py`) is generated only from these files and groups runs that share dataset hash, item count, template and judge. Corrupt or invalid report files are listed as errors, never silently skipped.

To reproduce a published row: check out the commit, run `chilango-bench eval` with the settings in the report, and compare the dataset hash.

## Known limitations

- No item has been reviewed by a native speaker yet.
- 168 items is small; per-category intervals are wide.
- The focus is central Mexico; other regions' slang is underrepresented.
- Facts about procedures can change (fees, deadlines). Items avoid amounts that change yearly, but reviewers should re-check them.
- Only small local models have been run so far.
- Phantom words were checked against Urban Dictionary and es.wiktionary on 2026-10-30. The RAE dictionary blocked automated lookups, and a native speaker has not reviewed them yet. Words derived from real ones were discarded because a model could fairly infer them.
- Local inference is not perfectly deterministic: re-running llama3.2:3b through Ollama at temperature 0 changed one answer out of 157.
