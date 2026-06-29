# Learned antipatterns

Recurring failure modes flagged by the user in past sessions. Grouped by theme. Read before working in unfamiliar parts of the repo; consult `## Module API` before declaring new exports, `## Implementation shape` before writing a non-trivial transform.

---

## Module API

### Anticipatory export

**Trigger:** Before typing `export` / adding a name to `__init__.py`.

**Smells:** `rg "\b<name>\b"` finds no importer outside the defining file; entire module declared but never imported anywhere; `export` keyword preserved across a file move with no current consumer.

**Diagnosis:** Treating "this is a module API" as license to publish by default. Public-by-default hides dead code from grep and ossifies internal names as if they were contracts.

**Rule:** Name the external consumer before exporting. None → leave un-exported (and delete the file if nothing in it has any consumer). Add `export` only when a real second consumer appears.

**Python `__init__.py`:** Re-export shims are forbidden — see `.claude/rules/package-init.md`. The `package-init` hook denies `import` / `__all__` in `__init__.py` edits; the Stop quality gate re-checks touched `__init__.py` files on disk.

**Exception:** SDK / framework entrypoints whose consumer is the runtime (Slack `DefineFunction`, Lambda handler, FastAPI route, pytest fixture).

---

## Implementation shape

### Pipeline-not-table

**Trigger:** About to reach for `flatMap` / `filter` / `reduce` / comprehension to "clean up" a nested `if`/`for` or a run of N near-identical statements.

**Smells:** the pipeline still walks the list and branches per element; the same lookup question is re-asked every call (`DATA.filter(x => x.k === arg)…`); N hand-written calls of the same shape sit in a block (`f(x, "a"); f(x, "b"); …`).

**Diagnosis:** Treating "flatten the nesting" as the target instead of "remove the branching." Pipelines compose nicely but still encode "for each element, decide what to do" — the work is identical, just dressed up.

**Rule:** Before writing the pipeline, ask: *can I reshape the input or output into a lookup table or dispatch map so this becomes key access?* If yes, do that. Pipelines are second-best; tables/precomputed indexes/dispatch dicts are first.

**Inline examples (this session):**
- Nine repeated `findColumn(headers, "first name"|"last name"|…)` calls → `Record<Field, keyword>` spec table + `Object.fromEntries(Object.entries(spec).map(...))`.
- Per-call `LEAGUE_DATA.filter(lg => lg.sport === sport && …)` → `Map<sport, {wtnb, open}>` built once at module load; lookup is `MAP.get(sport)`.
- `if (kind === "a") … else if (kind === "b") …` chain → `const HANDLERS: Record<Kind, Fn> = { a, b, c }; HANDLERS[kind](…)`.
