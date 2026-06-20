---
name: python-uv-run
description: Run Python in this repo with `uv run` from the project root. Use whenever invoking Python in the BigAppleRecSports monorepo — running scripts, pytest, modules, REPL snippets, or any `python`/`python3` command. The repo targets Python 3.14 with a uv-managed environment; bare `python3` resolves to an old system interpreter and lacks deps (pydantic, etc.).
---

# Python via `uv run`

Always invoke Python through **`uv run`**, executed from the **repo root**
(`/Users/jrandazzo/git-bars/BigAppleRecSports`).

## Commands

```bash
# Tests
uv run pytest lib/domain/registrations/test_refund_calculator.py -q

# A module / script
uv run python path/to/script.py

# An inline snippet
uv run python -c 'import pydantic; print(pydantic.VERSION)'
```

## Why

- `uv run` resolves the project's Python 3.14 + dependencies (pydantic, etc.).
- Bare `python3` is the system 3.9 — missing `StrEnum`, pydantic, and more, so
  imports of repo modules fail.
- Running from the repo root keeps imports like `from lib.domain...` /
  `from registrations...` resolvable and matches `pyproject.toml` config.

## Don't

- Don't call `python` / `python3` directly.
- Don't hand-activate `.venv` or hardcode `.venv/bin/python`; let `uv run` manage it.
- Don't `cd` into a subdir to run Python; stay at the repo root and use full paths.
