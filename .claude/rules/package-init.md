# Package `__init__.py` — no re-exports

## Rule

**Importing into `__init__.py` solely to re-export symbols is forbidden.**

Consumers import from the **defining module** (e.g. `from lib.utils.spreadsheets.helpers import read_csv_file`), not from the package root.

### Forbidden

```python
# lib/utils/spreadsheets/__init__.py
from lib.utils.spreadsheets.helpers import read_csv_file

__all__ = ["read_csv_file"]
```

Any pattern whose purpose is “import here so callers can `from lib.utils.spreadsheets import …`”.

### Allowed without asking

- Empty `__init__.py` (namespace marker only)
- Module docstring only (no imports)

### Exception — user approval required

Before adding **any** import to `__init__.py` that exists for re-export, aliasing, or `__all__` curation:

1. **Stop** — do not land the edit.
2. **Ask** the user explicitly; state what would be re-exported and why.
3. **Wait** for explicit approval in the same thread.
4. Implement only what was approved.

No “temporary” re-exports. No “we’ll clean up later.”

## Rationale

Re-exports hide the canonical module and encourage import cycles. One import path per symbol.

## Enforcement

`.cursor/hooks/package-init.sh` runs on **Edit / Write / StrReplace** when the target path is `__init__.py` (`preToolUse` in `.cursor/hooks.json`; `PreToolUse` in `.claude/settings.json`; `failClosed: true` in Cursor).

- **Every** `__init__.py` edit injects `agent_message` with this rule.
- Edits whose proposed content adds `import` / `from … import` / `__all__` are **denied** (`permission: deny`, exit 2) until the user explicitly approves re-export in the thread.
