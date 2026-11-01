Dataset `datasets/phantom/phantom-slang.jsonl` (sha256 `f82a527c475f`), prompt template `es-v1`

| Rank | Model | Balanced | Honest | Hedged | Fabricated (95% CI) | False refusal | Errors | Items |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 64.7% | 29.4% | 0.0% | 70.6% (47%-88%) | 0.0% | 0 | 29 |
| 2 | `qwen2.5:1.5b` | 50.0% | 0.0% | 5.9% | 94.1% (82%-100%) | 0.0% | 0 | 29 |
| 3 | `gemma3:1b` | 50.0% | 0.0% | 5.9% | 94.1% (82%-100%) | 0.0% | 0 | 29 |

Dataset `datasets/v1/chilango-bench.jsonl` (sha256 `58df56a8684e`), prompt template `es-v1`

| Rank | Model | Accuracy (95% CI) | Slang | Culture | Procedures | Albur | Unresolved | Errors | Items |
|---:|:---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `llama3.2:3b` | 61.8% (54%-69%) | 63.5% | 70.7% | 48.8% | 65.2% | 6 | 0 | 157 |
| 2 | `qwen2.5:1.5b` | 55.4% (48%-63%) | 42.3% | 51.2% | 65.8% | 73.9% | 0 | 0 | 157 |
| 3 | `gemma3:1b` | 40.1% (32%-48%) | 26.9% | 43.9% | 46.3% | 52.2% | 0 | 0 | 157 |
| 4 | `baseline-always-B` | 21.7% (15%-29%) | 23.1% | 19.5% | 21.9% | 21.7% | 0 | 0 | 157 |
