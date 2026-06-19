# BigAppleRecSports

Monorepo: Python backend + Deno/Slack frontend + Shopify integration.

## Project structure

- `backend/` — Python (FastAPI). AWS Lambda deploy target.
- `slack-apps/registrations/` — Deno Run-on-Slack app (waitlist + refund workflows).
- `lib/` — shared Python domain modules (registrations, shopify, etc.).
- `cli/` — Python CLI tools. Each uses `_core/`, `commands/`, `utils.py` layout.
- `infra/` — AWS CDK / SAM infrastructure.

## Python

- **Always** use `uv run` from the repo root. System python is 3.9; project targets 3.14+.
- Tests: `uv run pytest <path> -q`
- Never call `python` / `python3` directly or hand-activate `.venv`.

## AWS

- Account: `084375563770`, profile: `bars`
- The user-level `aws-credential-injector` hook auto-chains `assume bars`.

## Policies

- No backward compatibility guarantees. Break old interfaces freely.
- CLI projects: `_core/` for internal logic, `commands/` for click/typer commands, `utils.py` for shared helpers.
