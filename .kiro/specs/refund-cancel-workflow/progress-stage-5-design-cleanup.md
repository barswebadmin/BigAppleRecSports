# Stage 5 design cleanup progress

Single-shot documentation reconciliation pass: design-stage-5.md ONLY.
Goal: § 5.b.1 is the sole casing rule; the obsolete § 5.casing /
`to_camel` boundary-helper plan is erased from the doc.

- [x] C1 § 5.casing H2 section deleted — saved at 2026-06-21T02:12:49Z
- [x] C2 § 5.k.5 utils/casing.py spec deleted — saved at 2026-06-21T02:13:39Z
- [x] C3 § 5.b.1 reconciliation paragraph removed — saved at 2026-06-21T02:13:39Z
- [x] C4 inline `to_camel` / `utils/casing.py` / `_camelize` references deleted — saved at 2026-06-21T02:13:39Z
- [x] C5 D32 entry retitled / removed (deleted alongside § 5.casing in C1; orchestrator-TODO entry rewritten to reference § 5.b.1) — saved at 2026-06-21T02:13:39Z
- [x] C6 deliverables checklist updated — saved at 2026-06-21T02:13:39Z
- [x] C7 verification grep — `grep -nE 'to_camel|utils/casing|_camelize|D32' design-stage-5.md` returns ZERO behavioral hits — saved at 2026-06-21T02:13:39Z

## Summary

§ 5.b.1 is now the sole casing rule in design-stage-5.md. The obsolete
boundary-helper plan (§ 5.casing + § 5.k.5 `to_camel` / `utils/casing.py`
spec + D32 entry) has been deleted. All inline references to the
helper path have been rewritten to match the camelCase-direct path that
actually shipped (TypedDicts mirror the wire shape directly; the dict
the controller builds IS the wire JSON; Pydantic aliases handle
incoming camel→snake on `BaseModel` bodies).

### Deleted

- Entire `## 5.casing — Casing convention` H2 section, including the
  embedded "Decision D32" entry (lines 486-545 in the pre-edit file).
- Entire `### 5.k.5 — Convert models/estimate.py TypedDict keys to
snake_case + add utils/casing.py` sub-section, including the
  `def _camelize(...)` / `def to_camel(...)` source block and the
  controller `from utils.casing import to_camel` examples.
- "Reconciliation with § 5.casing / D32" paragraph from § 5.b.1.
- `backend/utils/casing.py` row from the § 5.l "Files in scope" table.
- `backend/utils/casing.py` line from each of the three § 5.l
  verification command blocks.
- "casing.py / to_camel" line from § 5.a file inventory tree.
- `to_camel(value: Any) -> Any` smoke-import + casing.py existence
  bullets from § 5.h Stage 5 deliverables checklist.
- `from backend.utils.casing import to_camel` smoke-import bullet.
- `test_casing.py` planned-tests bullet from § 5.i.
- "snake_case keys (D32) verifiable by grep…" + "to_camel imported by
  every controller" bullets from § 5.k Substage deliverables checklist.

### Rewritten

- § 5.c heading and intro paragraph: TypedDicts now declared with
  camelCase keys directly per § 5.b.1; `CancelOutcome` /
  `RefundOutcome` / `CreateRefundResponse` field names rewritten to
  `jobId` / `jobDone` / `refundId` / `createdAt`.
- § 5.d controller body: removed `from utils.casing import to_camel`
  import; rewrote the `return to_camel(response)` line to plain
  `return response`; rewrote the docstrings on
  `_cancel_outcome_from_payload` / `_refund_outcome_from_payload` and
  flipped their return-dict keys to camelCase.
- § 5.f orders_controller: removed the casing import and the
  `to_camel({...})` wrapper at the route's return; the dict literal
  now uses `jobId` / `jobDone` directly.
- § 5.b.1 "Boundary helpers" paragraph: dropped the now-redundant
  parenthetical about `to_camel(...)` not being needed; the
  paragraph asserts the camelCase-direct construction in plain terms.
- § 5.m boundary-properties bullet: rewrote to describe the
  camelCase-direct path (no boundary helper, no snake→camel flip on
  the way out).
- § 5.todo orchestrator-feedback item #1: rewrote from
  "D32 already lives in this stage-5 doc" + paste of D32 text to a
  pointer at § 5.b.1 as the canonical statement of the casing
  convention. Q7 / R8 items #2 and #3 left untouched per the task's
  do-not-touch directive.
- § 5.h deliverables: added a single explicit verification item
  ("All TypedDicts that mirror the wire shape … declare camelCase
  keys directly. Verifiable by `grep -rn '^class.*TypedDict'
backend/modules/refunds/models/` producing classes whose fields
  are camelCase strings.") replacing the deleted casing-related
  bullets.

### Verification grep output

```
$ grep -nE 'to_camel|utils/casing|_camelize|D32' .kiro/specs/refund-cancel-workflow/design-stage-5.md
$ grep -nE '5\.casing|## 5\.casing' .kiro/specs/refund-cancel-workflow/design-stage-5.md
```

Both: zero matches.

### Untouched (per task directive)

- Q7 mentions in the § 5.e mapping-table footnotes and § 5.h
  deliverables checklist (Q7 is `✅ DEFERRED` in design.md Open
  Questions and orchestrator-feedback bullet about "Q7 deferred — DO
  NOT BLOCK Stage 5 on it" is already accurate).
- design.md / design-stage-4.md / design-stage-6.md / design-stage-7.md
  and any other file outside design-stage-5.md.
- All source code under `backend/`, `slack-apps/`, `lib/`. Doc-only
  cleanup pass.

Cleanup: COMPLETED
