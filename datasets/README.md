# chilango-bench dataset

`v1/chilango-bench.jsonl` holds 168 items written for this benchmark. They are original text, not copied from other benchmarks, websites or exams.

## Licence

The dataset is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The code in this repository is MIT.

## Canary

The file starts with a canary GUID. If you build a training corpus, filter out any document that contains it, so that future models are not trained on the answers. If a model can reproduce the GUID, it has probably seen this file.

## Contents

| Category | Items | What it tests |
|---|---|---|
| `slang` | 55 | Everyday Mexican slang and its pragmatics (*chido*, *ahorita*, *no hay pedo*, *hacer la vaca*). |
| `cultural_context` | 44 | Mexico City life: Metro, food, holidays, landmarks, earthquakes, street culture. |
| `procedures` | 44 | Government and labour procedures: CURP, RFC, SAT, INE, IMSS, aguinaldo, Hoy No Circula. |
| `albur` | 25 | Recognising the Mexican double-entendre game and handling it appropriately, without explicit content. |

| Type | Items | Grading |
|---|---|---|
| `multiple_choice` | 134 | Four options; only an explicit answer counts. |
| `exact_match` | 23 | Accent- and case-insensitive match against a list of accepted answers. |
| `rubric_judged` | 11 | An LLM judge scores 1–5 against a reference answer and criteria. Skipped unless `--judge` is given. |

Quality checks run by `chilango-bench validate` and the test suite:

- Correct answers are spread evenly across A–D (no letter above 28 %).
- The correct option is the longest in 25 % of multiple-choice items, so "pick the longest option" scores chance.
- Every item has an `explanation` (or a rubric) so reviewers can check the reasoning.

## Review status

Every item carries `review_status`: `unreviewed`, `accepted` or `rejected`. **All 168 items are currently `unreviewed`.** Results on this file are preliminary until a native speaker has checked each item.

Review items from the terminal:

```bash
uv run chilango-bench review datasets/v1/chilango-bench.jsonl --reviewer your-github-handle
```

Each decision is written back to the file immediately, with your handle in `metadata.reviewer`. Rejected items are excluded from `eval`; `eval --accepted-only` scores only accepted items.

## Fields

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `<category prefix>-<number>`, unique. |
| `category` | yes | One of the four above. |
| `eval_type` | yes | `multiple_choice`, `exact_match` or `rubric_judged`. |
| `prompt` | yes | Shown to the model. |
| `choices` | multiple choice | `{"A": ..., "B": ..., "C": ..., "D": ...}`. |
| `target` | yes | Option key, list of accepted answers, or reference answer. |
| `rubric` | no | Criteria for the judge. |
| `explanation` | no | Why the target is right. Never shown to models. |
| `review_status` | no | Defaults to `unreviewed`. |
| `metadata` | no | `difficulty`, `source`, `reviewer`, `rejection_reason`. |

## Contributing items

Open a pull request that adds lines to the JSONL file with `review_status: unreviewed` and an `explanation`. Write the text yourself; do not paste from other sources. Keep distractors plausible and about as long as the correct option, then run `uv run chilango-bench validate datasets/v1/chilango-bench.jsonl` and check the length and balance figures.
