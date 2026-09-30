# Contributing

Thanks for taking a look. TreeRing is early; the most valuable contributions right now are:

- **Attacks.** A manifest + fake extractor that gets untrusted data into the privileged module, or an action past the provenance check, is worth more than a feature. Open it as an issue with a failing test.
- **LLM adapters** for the `Planner` and `Extractor` protocols (OpenAI, Anthropic, local models via structured output).
- **Schemas** for common quarantined outputs beyond `EmailSummary`.
- **Docs and translations.**

## Setup

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run treering demo
```

## Rules of the road

- Every security-relevant change needs a test that fails without it.
- No LLM in the enforcement path. LLMs propose; code decides.
- Keep the ring log single-writer. Modules never write their own entries.
- Public APIs get a docstring; everything else should read without comments.

By contributing you agree your work is licensed under Apache-2.0.
