# BigAppleRecSports (BARS)

Multi-language monorepo for managing recreational sports leagues.

## Quick Start

```bash
uv sync
make start
make test-backend-unit
```

## Architecture

- **Backend API** (FastAPI)
- **Google Apps Scripts** (TypeScript/JavaScript)
- **Lambda Functions** (Python)
- **Slack Apps** (Deno)
- **Shopify Apps** (Liquid templates)

## Installation

### Python Projects
```bash
cd backend && uv sync
cd lambda && uv sync
cd shared_utilities && uv sync
```

### JavaScript Projects
```bash
cd google-apps-scripts && pnpm install
```

### Deno Projects
```bash
cd slack-apps
# Dependencies auto-resolved from deno.json
```

## Development

### Linting & Formatting (Ruff)

All Python projects use Ruff for linting and formatting. Auto-format on save is currently **disabled** for manual control.

**Manual Commands:**

```bash
# Format files
ruff format backend/
ruff format shared_utilities/

# Check linter issues (no changes)
ruff check backend/

# Fix auto-fixable issues
ruff check --fix backend/

# Organize imports
ruff check --select I --fix backend/
```

**Check Current Configuration:**

```bash
# View effective config for a project
ruff check --show-settings backend/

# List all available rules
ruff rule --all
```

**Change Configuration:**

Two layers control Ruff behavior:

1. **IDE Automation** (`.vscode/settings.json`)
   - `editor.formatOnSave` - Auto-format on save (currently `false`)
   - `editor.codeActionsOnSave` - Auto-fix/organize imports (currently disabled)

2. **Ruff Rules** (`pyproject.toml`)
   - Root config applies globally (line-length: 120, rules: E/F/I/N/W)
   - Override in project-specific `pyproject.toml` if needed

**VSCode Manual Triggers:**

- Format: `Shift+Option+F` or Command Palette → "Format Document"
- Fix All: Command Palette → "Ruff: Fix all auto-fixable problems"
- Organize Imports: Command Palette → "Ruff: Organize Imports"

### Pre-commit Hook

The repo ships a pre-commit hook at `.githooks/pre-commit` (enable once with
`git config core.hooksPath .githooks`). It runs automatically on every `git commit`.

**Staged-only isolation.** Before running any check, the hook moves your
**unstaged modifications and untracked files** into a temp backup directory
(`.git/pre-commit-backup`) and reverts the working tree to the staged version, so
the checks see *exactly* what you're committing and nothing else. Everything is
restored on exit (success or failure) via a trap. We deliberately do **not** use
`git stash` — `stash pop` conflicts whenever the formatter rewrites a staged file
and can silently leave work stashed on a partial commit.

**What it checks, in order:**

1. **Branch guard** — blocks direct commits to `main`.
2. **Ruff (Python, staged files only)** — collects the staged `.py` files and:
   - **Lints** them (report-only, no `--fix`, so your code is never edited by the
     linter). On failures you get an interactive prompt to continue / retry / abort.
   - **Formats** them, then re-stages only those files. Because it's scoped to
     staged files, a commit can never sweep in reformatting of unrelated files.
3. **Pydantic required-fields check** — `scripts/check_required_fields.py`.
4. **CI workflow tests** — only when `.github/workflows/`, `shared-utilities/`, or
   `lambda-functions/` are touched.
5. **GAS endpoint detection** — warns (non-blocking) when `doGet`/`doPost` change.
6. **Secret detection** — `scripts/detect_secrets.py`; blocks the commit on a hit.

**Ruff rule sets applied** (from root `pyproject.toml`: `line-length = 120`,
`target-version = "py314"`):

| Code | Rule set | What it catches |
| ---- | -------- | --------------- |
| `E`  | pycodestyle errors | PEP 8 style errors (indentation, statement layout) |
| `W`  | pycodestyle warnings | PEP 8 style warnings (e.g. trailing whitespace) |
| `F`  | Pyflakes | Real bugs: unused imports/vars, undefined names, f-string issues |
| `I`  | isort | Import ordering / grouping |
| `N`  | pep8-naming | Naming conventions for classes, functions, constants |

`E501` (line-too-long) is ignored — the formatter owns line width. Note that with
`target-version = "py314"`, `ruff format` removes now-redundant parentheses in
`except` clauses (PEP 758): `except (A, B):` → `except A, B:`, which is valid 3.14.

> **TODO (future stage): no JS/TS formatter or linter yet.** The pre-commit hook
> only handles Python (Ruff). JavaScript/TypeScript files — Deno Slack apps,
> Google Apps Scripts, etc. — are **not** linted or formatted on commit, so style
> can drift. A future stage should add one and wire it into the hook (staged-only,
> mirroring the Ruff setup). Recommended options:
>
> - **Deno code** (`slack-apps/`): use the built-in **`deno fmt`** and
>   **`deno lint`** — zero-config, no dependencies, already available.
> - **Node/Apps Scripts JS/TS** (`google-apps-scripts/`): either
>   - **[Biome](https://biomejs.dev/)** — single fast Rust tool for both format +
>     lint (closest analog to Ruff), or
>   - **[Prettier](https://prettier.io/)** (format) + **[ESLint](https://eslint.org/)**
>     (lint) + `typescript-eslint` — the conventional pairing.
> - **Hook integration**: **[lint-staged](https://github.com/lint-staged/lint-staged)**
>   (often with Husky) to run the above only on staged files.

### Backend
```bash
make start
make test-backend-unit
```

### Lambda
```bash
cd lambda/functions/<function-name>
uv run python run_local.py
```

### Google Apps Scripts
```bash
cd google-apps-scripts
pnpm install
pnpm build
```

### Slack Apps
```bash
cd slack-apps
deno task test-all
```

## Configuration

Create `.env` file at repository root:
```bash
SHOPIFY_URL_ADMIN_DOMAIN=your-store.myshopify.com
SHOPIFY_TOKEN=your_admin_api_token
SLACK_REFUNDS_BOT_TOKEN=xoxb-your-bot-token
GOOGLE_DEFAULT_ADMIN_EMAIL=admin@yourdomain.com
GOOGLE__SERVICE_ACCOUNT='{"type":"service_account",...}'
```

## API Endpoints

```bash
GET /orders/{order_number}
DELETE /orders/{order_number}
POST /orders/{order_number}/refund
POST /orders/{order_number}/restock
POST /refunds/send-to-slack
POST /webhooks/shopify/product/update
POST /slack/webhook
```

## Google Apps Scripts

TypeScript/JavaScript automation for Google Workspace.

### Projects
- process-refunds-exchanges
- parse-registration-info
- leadership-discount-codes
- product-variant-creation
- waitlist-script
- payment-assistance-tags
- add-sold-out-product-to-waitlist

### Deployment
```bash
cd google-apps-scripts/projects/<project-name>
clasp push && clasp deploy
```

## Lambda Functions

Python functions deployed to AWS via GitHub Actions.

### Functions
- shopifyProductUpdateHandler
- changePricesOfOpenAndWaitlistVariants
- MoveInventoryLambda
- updateRegistrationStatus
- closeRegProductToWaitlist
- WaitlistManager

### Local Development
```bash
cd lambda/functions/<function-name>
uv run python run_local.py
```

## Deployment

### Backend
Automatic via GitHub Actions on push to `main`.

### Lambda
Automatic via GitHub Actions when function code changes.

### Google Apps Scripts
```bash
cd google-apps-scripts/projects/<project-name>
clasp push && clasp deploy
```

### Slack Apps
```bash
cd slack-apps
slack deploy
```

## Testing

```bash
uv run pytest
make test-backend-unit
make test-backend-integration
```

## Troubleshooting

```bash
make install
make compile backend
make test-backend-unit
```

## Documentation

- [UV Guide](UV_GUIDE.md) - Python package management
- [Monorepo Architecture](MONOREPO_ARCHITECTURE.md) - Multi-language structure
- [Model Migration](MODEL_MIGRATION_CHECKLIST.md) - Schema migration guide
- [pnpm vs npx](PNPM_VS_NPX.md) - JavaScript package management

## License

Proprietary to Big Apple Recreational Sports.
