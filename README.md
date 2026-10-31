# chilango-bench

**Does your LLM actually understand Mexican Spanish?** A reproducible benchmark of slang, Mexico City culture, government procedures and *albur*, with an open dataset and a harness that runs against local and API models.

[![CI](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/DiegoTepichin/chilango-bench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Dataset: CC BY 4.0](https://img.shields.io/badge/dataset-CC%20BY%204.0-green.svg)](datasets/README.md)

[Leer en español](README.es.md)

> **Status:** v1.0. The 168 dataset items have **not yet been reviewed** by a native speaker, so the scores below are preliminary. Review is built in: `chilango-bench review`.

## Why

Spanish benchmarks are usually translations from English or neutral Spanish. They do not tell you whether a model knows that *ahorita* may mean "never", that *¡aguas!* is a warning, how many characters a CURP has, or how to take an *albur* without being either prudish or vulgar. If you are putting an LLM in front of Mexican users, that is what matters.

## Results

Small open models, run locally with Ollama 0.40.6 at temperature 0 on the 157 automatically graded items (rubric items need a judge model and are not included). Every row comes from a committed report in [`results/`](results/).

| Rank | Model | Accuracy (95% CI) | Slang | Culture | Procedures | Albur | Unresolved | Items |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 61.8% (54%-69%) | 63.5% | 70.7% | 48.8% | 65.2% | 6 | 157 |
| 2 | `qwen2.5:1.5b` | 55.4% (48%-63%) | 42.3% | 51.2% | 65.8% | 73.9% | 0 | 157 |
| 3 | `gemma3:1b` | 40.1% (32%-48%) | 26.9% | 43.9% | 46.3% | 52.2% | 0 | 157 |
| 4 | `baseline-always-B` | 21.7% (15%-29%) | 23.1% | 19.5% | 21.9% | 21.7% | 0 | 157 |

What the reports show:

- **Slang is the hardest category for small models.** gemma3:1b is close to chance on it; qwen2.5:1.5b knows procedures better than slang.
- **Over-refusal is a failure mode.** All six of llama3.2:3b's unresolved answers are refusals: it declined to say what *"¡Ya se la saben!"* means on a bus, to explain what an albur is, and to answer a question about a 2023 labour reform.
- **Exact recall is weak.** On the 23 short-answer items the best model scores 43%. Asked what RFC stands for, llama3.2:3b answered "Request for Comments"; asked which agency issues the CURP (RENAPO), the models invented acronyms such as "SENASAL" and "SEGUI".
- Per-category intervals are wide (about ±15 points with ~40 items), so differences inside them are not meaningful yet.

Re-running the same model can change one or two answers even at temperature 0; llama3.2:3b moved by one item between two runs.

## Phantom slang

Do models admit they do not know a word, or do they make up a meaning? [`datasets/phantom/`](datasets/phantom/) asks for the meaning of 18 invented words and 12 real control words. Always refusing scores a balanced 50%, so a model cannot win by saying "I don't know" to everything.

Small open models, run locally with Ollama 0.40.13 at temperature 0 and 200 output tokens:

| Rank | Model | Balanced | Honest | Hedged | Fabricated (95% CI) | False refusal |
|---:|:---|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 63.9% | 27.8% | 0.0% | 72.2% (50%-89%) | 0.0% |
| 2 | `qwen2.5:1.5b` | 50.0% | 0.0% | 5.6% | 94.4% (83%-100%) | 0.0% |
| 3 | `gemma3:1b` | 50.0% | 0.0% | 5.6% | 94.4% (83%-100%) | 0.0% |

*Honest* is the share of invented words the model said it does not know, *hedged* doubted but guessed anyway, *fabricated* defined with no doubt, and *false refusal* is real words it claimed not to know. Answering a real word only means it did not refuse: the definition is not graded.

With 18 invented words the intervals are wide, and these are three small models, so this says nothing about larger ones. Words and answers are preliminary until reviewed.

```bash
uv run chilango-bench eval -d datasets/phantom/phantom-slang.jsonl -m qwen2.5:1.5b -p ollama --max-tokens 200 -o runs/phantom.json
```

## What is in the benchmark

168 original items ([datasheet](datasets/README.md)), CC BY 4.0:

| Category | Items | Examples of what is tested |
|---|---|---|
| Slang | 55 | *chido*, *ahorita*, *no hay pedo*, *hacer la vaca*, *¿a poco?* |
| Cultural context | 44 | Metro, *pambazo*, posadas, the 19 September earthquakes, *viene viene* |
| Procedures | 44 | CURP, RFC, SAT, INE, IMSS, aguinaldo, Hoy No Circula |
| Albur | 25 | Recognising the double-entendre game and responding appropriately, without explicit content |

134 multiple-choice, 23 exact-match and 11 rubric items. Answer keys are balanced, and the correct option is the longest in only 25% of items, so neither "always B" nor "pick the longest" beats chance. The file carries a canary GUID for training-corpus filtering.

## How grading works

- **Multiple choice:** only an explicit answer counts (a bare letter, `B) ...`, "la respuesta es C", or the full text of one option). A stray letter inside a sentence never counts, because *a*, *e*, *o* and *y* are Spanish words. Anything else is *unresolved* and graded wrong.
- **Exact match:** accent-, case- and punctuation-insensitive match against accepted answers.
- **Rubric:** an LLM judge scores 1-5; unreadable judge output is an error, never a made-up score.
- **Scores** come with 95% bootstrap intervals. Reports pin the dataset SHA-256, prompt template and generation settings; the leaderboard never ranks runs that are not comparable.

Details in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Quickstart

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/DiegoTepichin/chilango-bench.git
cd chilango-bench
uv sync
uv run chilango-bench validate datasets/v1/chilango-bench.jsonl
```

### Run a local model with Ollama

```bash
ollama pull qwen2.5:1.5b
uv run chilango-bench eval -d datasets/v1/chilango-bench.jsonl -m qwen2.5:1.5b -p ollama -o runs/qwen.json
```

### Run any OpenAI-compatible API

```bash
export OPENAI_API_KEY=...            # see .env.example
uv run chilango-bench eval -d datasets/v1/chilango-bench.jsonl -m gpt-4o-mini -p openai -o runs/gpt-4o-mini.json
# other providers: add --base-url https://api.groq.com/openai/v1 (or any compatible endpoint)
```

Add `--judge <model>` to grade the rubric items, `--limit 10` for a smoke test, `--accepted-only` to score only reviewed items.

### Build a leaderboard

```bash
uv run chilango-bench leaderboard -r runs
```

## Contributing

The most valuable contributions are **reviews** and **new items**:

```bash
uv run chilango-bench review datasets/v1/chilango-bench.jsonl --reviewer your-github-handle
```

shows each unreviewed item with its answer and explanation and records your decision in the file. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [datasheet](datasets/README.md). Result reports for other models are welcome too: open a PR with the JSON in `results/`.

## Development

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy .
uv run pytest          # offline, no API keys needed
```

## License

Code: [MIT](LICENSE). Dataset: [CC BY 4.0](datasets/README.md). © Diego Tepichin
