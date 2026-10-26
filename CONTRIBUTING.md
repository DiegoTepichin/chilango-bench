# Contributing

Thanks for your interest. Issues and pull requests are welcome, in English or Spanish.

## Ways to help

1. **Review items.** Native speakers checking facts, wording and answer keys is what turns preliminary scores into real ones:

   ```bash
   uv sync
   uv run chilango-bench review datasets/v1/chilango-bench.jsonl --reviewer your-github-handle
   ```

   Commit the updated JSONL and open a pull request. Reject items that are wrong, ambiguous, offensive beyond what the category needs, or outdated, and give a reason.

2. **Add items.** Write them yourself (no copying from other sources), add an `explanation`, keep distractors plausible and about as long as the correct option, and leave `review_status` as `unreviewed`. Then run `uv run chilango-bench validate datasets/v1/chilango-bench.jsonl` and check that the length and balance figures stay near 25 %. Albur items must not contain explicit sexual content.

3. **Submit results.** Run a model with `chilango-bench eval ... -o results/<model>.json` on an unmodified dataset and open a pull request with the report. Say how you ran it (provider, hardware, version).

4. **Code.** For anything bigger than a small fix, open an issue first.

## Checks

All of these must pass (CI runs them too):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

Tests never touch the network: use `MockRunner` or `respx`.

## Pull requests

- One logical change per pull request.
- [Conventional Commits](https://www.conventionalcommits.org/) in English, for example `feat(dataset): add 10 procedures items` or `fix: treat "Opción: b" as an answer`.
- Changing `format_eval_prompt` requires bumping `PROMPT_TEMPLATE`.

## License

Code contributions are licensed under [MIT](LICENSE); dataset contributions under [CC BY 4.0](datasets/README.md).
