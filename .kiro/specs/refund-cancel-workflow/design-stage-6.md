# Design — Stage 6: Final response shape + Python conventions cleanup [DETAILED]

> Parent: see [design.md](./design.md) for the overall feature design and
> Stages 1–5.

> Stage 6's nominal title is "Final response shape" — the
> `/refunds/create` outgoing shape Stage 7's Slack handler consumes.
> However, that shape (`CreateRefundResponse`) is built by Stage 5's
> controller (§ 5.d). So Stage 6's actual scope is:
>
> 1. **Document the response-shape contract as canonical reference.**
>    Stage 5 builds it; Stage 7 reads it; Stage 6 owns the spec and
>    the field-by-field semantics table.
> 2. **Own the FULL retroactive Python-conventions cleanup across
>    every backend file Stages 1–5 created or modified** (§ 6.g). This
>    is the meatiest substage. Per the user's directive, Stage 5's
>    own § 5.l + § 5.k.9 only cover Stage 5's NEW files; Stage 6
>    sweeps the rest.
> 3. **Property-validation invariants** that Stage 7's renderer
>    relies on (§ 6.e).
>
> No new files are introduced beyond the small TypedDict module Stage 5
> already creates. The cleanup substage is the bulk of Stage 6's
> implementation work.

> **Sub-agent execution order.** Stage 6's substages run in this order:
>
> 1. **§ 6.b → § 6.f FIRST** — wire-shape documentation, controller
>    construction reference, property-validation invariants,
>    deliverables checklist for the response-shape side. Mostly
>    canonical-reference text; no implementation work beyond
>    confirming Stage 5's `models/create_response.py` matches.
> 2. **§ 6.g SECOND** — Python conventions cleanup across Stages 1–5
>    files. Mechanical, list-driven; runs as one focused pass.
> 3. **§ 6.h LAST** — tests planned (deferred to a later stage).

---

## 6.a — File inventory (concrete)

```
backend/modules/refunds/
└── models/
    └── create_response.py        # READ-ONLY for Stage 6 — Stage 5 § 5.c builds it.
                                  #   Stage 6 documents the shape and
                                  #   verifies it matches § 6.b / § 6.c.

backend/utils/                    # CLEANUP TARGETS (§ 6.g)
├── dates.py                      # remove `from __future__ import annotations`
├── money.py                      # remove `from __future__ import annotations`
└── orders.py                     # remove `from __future__ import annotations`

backend/modules/refunds/          # CLEANUP TARGETS (§ 6.g)
├── refund_calculator.py          # remove `from __future__ import annotations` if present
├── models/
│   ├── estimate.py               # sweep Optional/List/Dict; remove __future__
│   ├── refund_request.py         # sweep Optional; remove __future__
│   ├── create_request.py         # verify clean from start (Stage 5)
│   └── create_response.py        # verify clean from start (Stage 5)
├── services/
│   └── estimate_service.py       # full sweep
├── controllers/
│   └── refunds_controller.py     # audit + sweep
└── inputs.py                     # NEW from Stage 5 § 5.k.0; verify clean

backend/modules/orders/
└── controllers/
    └── orders_controller.py      # NEW from Stage 5 § 5.f; verify clean

backend/main.py                   # audit only — Stage 3 added the
                                  #   ShopifyUserError handler; ensure
                                  #   the handler signature is clean.

backend/routes.py                 # audit only — Stage 5's one-line
                                  #   include is the only change.
```

> No NEW files are created by Stage 6's implementation sub-agent.
> The cleanup is mechanical edits to existing files; the response-shape
> documentation references Stage 5's `models/create_response.py`
> verbatim.

---

## 6.b — `CreateRefundResponse` TypedDict (NOT Pydantic — D28)

The outgoing `/refunds/create` response shape. Per **D28**, the shape
is a `TypedDict` constructed manually by the controller — NOT a
Pydantic `BaseModel`. Per the canonical casing rule from Stage 5
§ 5.b.1, the TypedDict keys are **camelCase strings** (matching the
wire JSON the Slack app expects); no boundary `to_camel(...)` helper
is needed because the keys are camelCase from the start.

### Critical Python convention rules (apply to every file in this

section)

- NO `from __future__ import annotations`. Python 3.14+ doesn't need
  it; the import is removed across all in-scope files (§ 6.g).
- Lowercase generics: `list[dict]`, NOT `List[dict]`.
  `dict[str, Any]`, NOT `Dict[str, Any]`. `tuple[str, ...]`, NOT
  `Tuple[str, ...]`.
- `X | None` instead of `Optional[X]`. `A | B` instead of `Union[A, B]`.
  `type[X]` instead of `Type[X]`.
- Snake_case file names (`create_response.py`).
- Snake_case Python identifiers (function names, variable names,
  Pydantic field names) — but TypedDict keys for wire shapes mirror
  the wire JSON, so they're camelCase **strings** (the keys are
  written as `"jobId"` / `"refundId"` literals in TypedDict
  definitions; this is consistent with § 5.b.1's wire-shape exception).

### Definition

```python
# backend/modules/refunds/models/create_response.py
# (Built by Stage 5 § 5.c; Stage 6 documents the canonical shape.)
from typing import TypedDict


class CancelOutcome(TypedDict):
    """Payload returned when `body.cancel` was True and the cancel
    succeeded. Mirrors `OrderCancelPayload.job` from Shopify.

    camelCase keys per § 5.b.1 — the wire JSON expects `jobId` /
    `jobDone`; the TypedDict declares them with that exact spelling
    so the controller's dict literal builds them directly with no
    boundary helper.
    """

    jobId: str
    jobDone: bool


class RefundOutcome(TypedDict):
    """Payload returned when `body.refund` was True and the refund
    succeeded. Mirrors `RefundCreatePayload.refund.{id, …}` from Shopify.

    camelCase keys per § 5.b.1.
    """

    refundId: str
    amount: float
    currency: str            # "USD" | "STORE_CREDIT" (mirrors Shopify's currency code)
    createdAt: str           # ISO 8601 UTC timestamp from Shopify


class CreateRefundResponse(TypedDict, total=False):
    """The full /refunds/create response.

    `total=False` because partial-success states are valid:
      - cancel-only success: `cancel` populated, `refund` is `None`.
      - refund-only success: `refund` populated, `cancel` is `None`.
      - cancel succeeded + refund failed: `cancel` populated, `refund` is
        `None`, `errors[]` non-empty.

    All keys camelCase per § 5.b.1; no boundary `to_camel(...)` helper
    is invoked at the controller's return statement — the dict
    literal in `refunds_controller.py` already builds camelCase keys
    directly.
    """

    ok: bool
    cancel: CancelOutcome | None
    refund: RefundOutcome | None
    errors: list[dict]       # Shopify user-error dicts (`{field, message, code?}`)
```

> **TypedDict is structural — not enforced at runtime.** Python does
> NOT enforce TypedDict shape at runtime; the dict literal the
> controller builds (Stage 5 § 5.d) happens to match
> `CreateRefundResponse`'s shape, and type-checkers (mypy / pyright)
> verify the structural conformance at static-check time. Stage 6
> ships the TypedDict purely for documentation + IDE autocomplete +
> static-typing support; the wire JSON is the actual contract.

---

## 6.c — Field-by-field shape contract

For each TypedDict field, where the value comes from, and when it's
`None`. Stage 7's renderer relies on this table verbatim.

| Field              | Type                    | Source                                                             | When null                                                                                          |
| ------------------ | ----------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `cancel.jobId`     | `str`                   | Shopify `OrderCancelPayload.job.id` GID                            | n/a (always populated when `cancel != null`)                                                       |
| `cancel.jobDone`   | `bool`                  | Shopify `OrderCancelPayload.job.done`                              | n/a                                                                                                |
| `refund.refundId`  | `str`                   | Shopify `RefundCreatePayload.refund.id` GID                        | n/a                                                                                                |
| `refund.amount`    | `float`                 | echo of request `body.amount`                                      | n/a                                                                                                |
| `refund.currency`  | `str`                   | `"USD"` for original_method, `"STORE_CREDIT"` for store_credit     | n/a                                                                                                |
| `refund.createdAt` | `str`                   | Shopify `RefundCreatePayload.refund.createdAt` ISO 8601            | n/a                                                                                                |
| `cancel`           | `CancelOutcome \| None` | populated when `body.cancel=true` and the cancel succeeded         | when `body.cancel=false` OR cancel raised before producing a job                                   |
| `refund`           | `RefundOutcome \| None` | populated when `body.refund=true && amount>0` and refund succeeded | when `body.refund=false` OR `body.amount` was `None`/`0` OR refund raised                          |
| `ok`               | `bool`                  | `not errors` (no Shopify `userErrors` accumulated)                 | always present (TypedDict marks it optional via `total=False` but the controller always builds it) |
| `errors`           | `list[dict]`            | Shopify `userErrors` accumulated from failed mutations             | `[]` on full success                                                                               |

### Partial-success contract

The contract Stage 7 relies on when rendering the post-decision review
card:

| Scenario                                      | `ok`                                                                 | `cancel`  | `refund`  | `errors[]` |
| --------------------------------------------- | -------------------------------------------------------------------- | --------- | --------- | ---------- |
| Cancel only — success                         | `True`                                                               | populated | `None`    | `[]`       |
| Cancel only — Shopify userError               | (handled by global `ShopifyUserError` → 422; never returned as 200)  |           |           |            |
| Refund only — success                         | `True`                                                               | `None`    | populated | `[]`       |
| Refund only — Shopify userError               | (handled by global `ShopifyUserError` → 422; never returned as 200)  |           |           |            |
| Cancel + refund — both succeed                | `True`                                                               | populated | populated | `[]`       |
| Cancel + refund — cancel ok, refund userError | `False`                                                              | populated | `None`    | populated  |
| Cancel + refund — cancel userError            | (handled by global `ShopifyUserError` → 422; refund never attempted) |           |           |            |
| No-op (`cancel=False, refund=False`)          | `True`                                                               | `None`    | `None`    | `[]`       |

The "cancel ok + refund userError" row is the ONLY partial-success
state surfaced with a 200 response — the local try/except in
`refunds_controller.py::create_refund` (Stage 5 § 5.d) catches the
`ShopifyUserError` from the refund-side mutation specifically to keep
the cancel-succeeded outcome visible to the operator.

---

## 6.d — Controller construction (where the dict is built)

Stage 5 § 5.d holds the canonical implementation of the controller
that produces the dict matching `CreateRefundResponse`. Stage 6
documents the construction path explicitly so reviewers and Stage 7
can cross-reference field-by-field.

### Where each field is set

| Field              | Set where (Stage 5 § 5.d)                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `cancel`           | `cancel_outcome` local; populated by `_cancel_outcome_from_payload(...)` after a successful `orderCancel` mutation. |
| `cancel.jobId`     | `cancel_payload.to_dict()["job"]["id"]` (read in `_cancel_outcome_from_payload`).                                   |
| `cancel.jobDone`   | `cancel_payload.to_dict()["job"]["done"]` (read in `_cancel_outcome_from_payload`).                                 |
| `refund`           | `refund_outcome` local; populated by `_refund_outcome_from_payload(...)` after a successful `refundCreate`.         |
| `refund.refundId`  | `refund_payload.to_dict()["refund"]["id"]`.                                                                         |
| `refund.amount`    | `refund_payload.to_dict()["refund"]["total_refunded_set"]["shop_money"]["amount"]` (`float(...)` cast).             |
| `refund.currency`  | `"STORE_CREDIT"` when `refund_to == "store_credit"`; otherwise `total["currency_code"] or "USD"`.                   |
| `refund.createdAt` | `refund_payload.to_dict()["refund"]["created_at"]` (Shopify already returns ISO 8601).                              |
| `ok`               | `not errors` at the controller's return statement.                                                                  |
| `errors`           | `errors` local; populated by the local try/except's `except ShopifyUserError as exc: errors = exc.errors`.          |

### Construction at the return statement

```python
# backend/modules/refunds/controllers/refunds_controller.py
# (Stage 5 § 5.d — quoted here verbatim for the field-construction reference.)
return {
    "ok": not errors,
    "cancel": cancel_outcome,
    "refund": refund_outcome,
    "errors": errors,
}
```

> Per § 5.b.1, the return statement does NOT call `to_camel(...)`.
> The dict literal builds camelCase keys directly (`"ok"`, `"cancel"`,
> `"refund"`, `"errors"`). The `_cancel_outcome_from_payload(...)` and
> `_refund_outcome_from_payload(...)` helpers likewise build their
> nested dicts with camelCase keys (`"jobId"`, `"jobDone"`,
> `"refundId"`, `"amount"`, `"currency"`, `"createdAt"`) — Stage 5's
> § 5.d implementation must match.

### TypedDict is structural — not enforced

Python's `TypedDict` does NOT enforce shape at runtime. The dict
literal above happens to match `CreateRefundResponse`'s shape; static
type-checkers (mypy / pyright) verify the structural conformance at
check time but the runtime never inspects the dict for "missing keys"
/ "extra keys" / "wrong-typed values". Stage 6 ships the TypedDict
purely for documentation, IDE autocomplete, and static-type support.
The actual contract is the wire JSON.

---

## 6.e — Property-validation invariants

The dict-shape invariants Stage 7's renderer relies on. These are
**renderer expectations**, not enforced at construction time
(TypedDict is structural). Stage 5 § 5.d's controller implementation
satisfies all of them by construction.

1. **`ok ⇔ errors empty`.**
   `response["ok"] == True` if and only if `response["errors"] == []`.
   Restated: `response["ok"] = not response["errors"]` is the controller's
   exact construction (Stage 5 § 5.d's return statement).

2. **`ok && body.cancel ⇒ cancel populated`.**
   When `response["ok"] == True` and the request had `body.cancel == True`,
   `response["cancel"]` is a `CancelOutcome` dict (non-`None`). If the
   cancel raises `ShopifyUserError`, `ok` becomes `False` (the local
   try/except puts `errors` into the response, and `ok = not errors`
   evaluates to `False`).

3. **`ok && body.refund && body.amount > 0 ⇒ refund populated`.**
   When `response["ok"] == True` and the request had `body.refund == True`
   with `body.amount > 0`, `response["refund"]` is a `RefundOutcome`
   dict. The `body.amount > 0` qualifier matters: Stage 5 § 5.d's
   controller short-circuits when `body.amount` is `None` or `0`, so
   a refund-flag-true / amount-zero combination produces
   `refund == None` (no mutation issued).

4. **`cancel.jobId` always starts with `"gid://shopify/Job/"`.**
   Shopify returns `OrderCancelPayload.job.id` as a fully-qualified
   global identifier; the controller does not modify it. Stage 7's
   renderer can rely on the prefix when constructing admin-UI links.

5. **`refund.refundId` always starts with `"gid://shopify/Refund/"`.**
   Same reasoning — Shopify returns `RefundCreatePayload.refund.id`
   as a GID; the controller does not modify it.

6. **`refund.currency in {"USD", "STORE_CREDIT"}`.**
   The controller hard-codes `"STORE_CREDIT"` when
   `refund_to == "store_credit"`; otherwise it reads from
   `total["currency_code"]` and defaults to `"USD"` when missing.
   BARS is USD-only today, so the original-payment branch always
   produces `"USD"`. The store-credit branch always produces
   `"STORE_CREDIT"`.

> These six invariants are documented as Stage 7 renderer
> expectations. Stage 6 does NOT add runtime checks for them at the
> construction site — the cost (a small `assert` block) outweighs the
> benefit (TypedDict + static type checking already enforce structural
> conformance, and Shopify's payloads have been stable for years).

---

## 6.f — Stage 6 deliverables checklist (response-shape side)

This checklist covers the response-shape documentation half of Stage 6.
The Python conventions cleanup deliverables live in § 6.g below.

- [ ] `backend/modules/refunds/models/create_response.py` ships the
      three TypedDicts per § 6.b: `CancelOutcome`, `RefundOutcome`,
      `CreateRefundResponse`. Lowercase generics. No `from __future__
import annotations`. camelCase keys (per § 5.b.1).
      Verifiable by
      `! grep -n "from __future__\|List\\[\|Dict\\[\|Optional\\[\|Union\\[\|Tuple\\[\|Set\\[\|Type\\[" backend/modules/refunds/models/create_response.py`
      returning no matches.
- [ ] No Pydantic `BaseModel` for outgoing shapes (D28). Verifiable by
      `! grep -n "BaseModel" backend/modules/refunds/models/create_response.py`
      returning no matches.
- [ ] No backend code constructs Slack Block Kit (D12). Verifiable by
      `! grep -rn "slack_sdk.blocks\|block_builders" backend/`
      returning no matches.
- [ ] Stage 5's controller dict construction in § 5.d matches the
      field-by-field contract in § 6.c — every key listed in § 6.c is
      set in the controller; no extra keys are emitted; the camelCase
      spelling matches verbatim. Verifiable by inspection of
      `backend/modules/refunds/controllers/refunds_controller.py`'s
      return statement and the two `_*_outcome_from_payload(...)`
      helpers.
- [ ] No `to_camel(...)` invocation in `refunds_controller.py` /
      `orders_controller.py` — per § 5.b.1, the camelCase keys are
      built directly at the construction site, not converted at the
      boundary. Verifiable by
      `! grep -rn "to_camel(" backend/modules/refunds/controllers/ backend/modules/orders/controllers/`
      returning no matches. (If § 5.casing's `to_camel` machinery
      lingers from an earlier draft, Stage 6 deletes it as part of
      this deliverable; § 5.b.1 is authoritative.)

---

## 6.g — Python conventions cleanup substage (across Stages 1–5 implementations)

The user's directive: "stages 6 and 7 should also be updated to not
use any outdated python conventions (no `List`, no `Dict`, only
lowercase. no `from __future__ import annotations`. others that have
been deprecated by python3.14 must not be present in my python files
in the final version)" and "add a substage in stage 6 to fix anything
in stages 1-5 that has outdated python conventions".

This substage runs as part of Stage 6 implementation. It is mechanical
(no design judgment) — every conversion is in the rule table at
§ 6.g.3.

### Scope

The cleanup applies to FILES CREATED OR MODIFIED BY STAGES 1–5 of
THIS spec. The list at § 6.g.2 is exhaustive — the sub-agent does NOT
search the rest of the repo. Files explicitly OUT OF SCOPE are
listed at the end of this section.

### 6.g.1 — Substages

- **6.g.1 — Sweep `from __future__ import annotations`.** Remove the
  import line entirely; verify each file still imports correctly.
- **6.g.2 — Sweep `Optional[X]` → `X | None`.**
- **6.g.3 — Sweep deprecated generics.** `List[X]` → `list[X]`,
  `Dict[X, Y]` → `dict[X, Y]`, `Tuple[...]` → `tuple[...]`,
  `Set[X]` → `set[X]`, `FrozenSet[X]` → `frozenset[X]`,
  `Union[X, Y]` → `X | Y`, `Type[X]` → `type[X]`.
- **6.g.4 — Sweep `from typing import` lines.** Keep only
  `Literal`, `TypedDict`, `Annotated`, `Protocol`, `TYPE_CHECKING`,
  `Callable`, `Any`, `Final`, `ClassVar`, `Self` (PEP 673), and any
  other types that have NO PEP 585 / PEP 604 alternative. Remove
  `List`, `Dict`, `Tuple`, `Set`, `FrozenSet`, `Optional`, `Union`,
  `Type` from all `from typing import …` lines.
- **6.g.5 — Verification grep.**
  ```bash
  grep -rn "from __future__ import annotations\|\bList\[\|\bDict\[\|\bOptional\[\|\bTuple\[\|\bSet\[\|\bFrozenSet\[\|\bUnion\[\|\bType\[" \
    backend/modules/refunds/ \
    backend/modules/orders/ \
    backend/utils/dates.py \
    backend/utils/money.py \
    backend/utils/orders.py \
    backend/utils/casing.py \
    backend/utils/shopify_refunds.py \
    backend/main.py \
    backend/routes.py
  ```
  Must return zero hits.
- **6.g.6 — `uv run ruff check backend/` must pass.**
- **6.g.7 — Smoke imports must succeed.**
  ```bash
  uv run python -c "import modules.refunds.controllers.refunds_controller; import modules.refunds.services.estimate_service; import modules.orders.controllers.orders_controller"
  ```
  Must succeed (zero stderr, zero exit code).

### 6.g.2 — Files in scope (concrete, exhaustive list)

The orchestrator's single-shot grep across `backend/` produced this
list. Stage 6's sub-agent treats it as authoritative; any additional
hits discovered during execution are appended to this list, never
silently fixed.

#### Files with `from __future__ import annotations` — REMOVE the import

- `backend/utils/dates.py` (line ~20)
- `backend/utils/money.py` (line ~15)
- `backend/utils/orders.py` (line ~14)
- `backend/modules/refunds/services/estimate_service.py` — verify and
  remove if present.
- `backend/modules/refunds/services/shopify_refund_service.py` —
  Stage 5 § 5.k.0 deletes this file outright; the `from __future__`
  import goes with it. No action for Stage 6.
- `backend/modules/refunds/models/estimate.py` — verify and remove
  if present.
- `backend/modules/refunds/models/refund_request.py` — verify and
  remove if present.
- `backend/modules/refunds/models/create_request.py` — Stage 5; verify
  clean from start.
- `backend/modules/refunds/models/create_response.py` — Stage 5;
  verify clean from start.
- `backend/modules/refunds/controllers/refunds_controller.py` —
  verify and remove if present.
- `backend/modules/orders/controllers/orders_controller.py` —
  Stage 5; verify clean from start.
- `backend/modules/refunds/refund_calculator.py` — verify and remove
  if present (Stage 2 reuses this file as-is, but Stage 6 audits it).

#### Files with deprecated typing forms (`Optional[X]` / `List[X]` / `Dict[X, Y]` / `Tuple[...]` / `Set[...]` / `Union[...]` / `Type[X]`)

- `backend/modules/refunds/services/shopify_refund_service.py` —
  Stage 5 § 5.k.0 DELETES this file outright (R2: the wrapper class
  is gone). The deprecated typing forms exit with the file; no
  rewrite needed. Out-of-scope for Stage 6's cleanup.
- `backend/modules/refunds/services/estimate_service.py` — full
  sweep. Replace `Optional[X]` → `X | None`, `List[X]` → `list[X]`,
  `Dict[K, V]` → `dict[K, V]`, `Tuple[Optional[str], ...]` →
  `tuple[str | None, ...]`. Drop `Optional`, `List`, `Dict`, `Tuple`
  from the `typing` import.
- `backend/modules/refunds/models/estimate.py` —
  `from typing import List, Literal, Optional, TypedDict` →
  `from typing import Literal, TypedDict`. Replace
  `Optional[List[str]]` → `list[str] | None`, `Optional[date]` →
  `date | None`, `Optional[str]` → `str | None`.
- `backend/modules/refunds/models/refund_request.py` —
  `from typing import Optional, ...` → drop `Optional`. Replace
  `Optional[str]` / `Optional[SheetRowRef]` with `str | None` /
  `SheetRowRef | None`.
- `backend/utils/orders.py` — sweep any `Optional[...]` /
  `List[...]` / `Dict[...]` / `Tuple[...]` if present.
- `backend/main.py` — audit only. Stage 3 added the
  `ShopifyUserError` exception handler. Verify the handler signature
  uses lowercase `list[dict]` / `dict[str, Any]` and `X | None`;
  rewrite if needed.
- `backend/routes.py` — audit only. Stage 5 added the one-line
  `router.include_router(orders_router)`. Verify no D33 violations
  in the imports or function signatures the include touches.
- All Stage-5-created files (per § 5.k.0 / § 5.b / § 5.c / § 5.f /
  § 5.k.5) — must comply from creation; Stage 6 audits as
  belt-and-suspenders.

### 6.g.3 — Conversion rule table

| Old (deprecated)                     | New (Python 3.14 idiomatic) |
| ------------------------------------ | --------------------------- |
| `from __future__ import annotations` | DELETE the line entirely    |
| `from typing import Optional`        | DELETE                      |
| `from typing import List`            | DELETE                      |
| `from typing import Dict`            | DELETE                      |
| `from typing import Tuple`           | DELETE                      |
| `from typing import Set`             | DELETE                      |
| `from typing import FrozenSet`       | DELETE                      |
| `from typing import Type`            | DELETE                      |
| `from typing import Union`           | DELETE                      |
| `Optional[X]`                        | `X \| None`                 |
| `Union[A, B]`                        | `A \| B`                    |
| `List[X]`                            | `list[X]`                   |
| `Dict[K, V]`                         | `dict[K, V]`                |
| `Tuple[A, B]`                        | `tuple[A, B]`               |
| `Tuple[X, ...]`                      | `tuple[X, ...]`             |
| `Set[X]`                             | `set[X]`                    |
| `FrozenSet[X]`                       | `frozenset[X]`              |
| `Type[X]`                            | `type[X]`                   |

Mixed `from typing import …` lines (e.g.
`from typing import Optional, Literal, TypedDict`) keep the allowed
symbols and drop the deprecated ones. Don't delete the entire import
statement — preserve `Literal`, `TypedDict`, etc.

### 6.g.4 — Allowed `from typing import …` symbols

These DO have an idiomatic Python-3.14 form OR are essential and stay:

| Symbol              | Why it stays                                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `Literal`           | No lowercase equivalent; `Literal["a", "b"]` is the only spelling.                                                                   |
| `Any`               | Essential escape-hatch type.                                                                                                         |
| `TypedDict`         | The Python 3.14 lowercase form is `dict` itself, but `TypedDict` is the only way to declare structured-dict shapes with field types. |
| `TYPE_CHECKING`     | Runtime/import-time guard; no replacement.                                                                                           |
| `ClassVar`          | Class-attribute marker; no replacement.                                                                                              |
| `Final`             | Read-only marker; no replacement.                                                                                                    |
| `Annotated`         | Adds metadata to a type; no replacement.                                                                                             |
| `cast`              | Runtime cast helper; no replacement.                                                                                                 |
| `overload`          | Decorator for function overloads (Stage 5 forbids overloaded methods, so this rarely appears in scope).                              |
| `Protocol`          | Structural-typing primitive; no replacement.                                                                                         |
| `runtime_checkable` | Decorator that pairs with `Protocol`; no replacement.                                                                                |
| `Callable`          | No lowercase equivalent in this Python version.                                                                                      |
| `Self` (PEP 673)    | Self-typing primitive; no replacement.                                                                                               |

If a Stage-1–5 file imports any other `typing` symbol not on this
list, the sub-agent treats it as "audit / modernize if possible" —
but the conversion table at § 6.g.3 is the comprehensive list of
mechanical rewrites.

### 6.g.5 — Mechanical conversion examples

```python
# BEFORE — backend/modules/refunds/models/estimate.py
from __future__ import annotations

from datetime import date
from typing import List, Optional, TypedDict


class ProductInfo(TypedDict):
    id: str
    url: str
    year: int
    season: str
    sport: str
    day: str
    division: str
    week1Start: Optional[str]
    week2Start: Optional[str]
    week3Start: Optional[str]
    week4Start: Optional[str]
    week5Start: Optional[str]


class RefundRequestEval(TypedDict, total=False):
    ok: bool
    isValid: bool
    validationErrors: Optional[List[str]]
    order: "OrderInfo"
    product: ProductInfo
    estimate: "EstimateBlock"
```

```python
# AFTER — modernized
from datetime import date
from typing import TypedDict


class ProductInfo(TypedDict):
    id: str
    url: str
    year: int
    season: str
    sport: str
    day: str
    division: str
    week1Start: str | None
    week2Start: str | None
    week3Start: str | None
    week4Start: str | None
    week5Start: str | None


class RefundRequestEval(TypedDict, total=False):
    ok: bool
    isValid: bool
    validationErrors: list[str] | None
    order: "OrderInfo"
    product: ProductInfo
    estimate: "EstimateBlock"
```

> **Forward-reference caveat.** Removing `from __future__ import
annotations` means string-quoted forward references (e.g.
> `order: "OrderInfo"`) are NO LONGER auto-stringified. Where a
> forward reference is required because the referenced type is
> defined LATER in the file, the sub-agent leaves the explicit
> string-quote in place. Where a forward reference is unnecessary
> (the type is defined ABOVE), the quotes are dropped. The sub-agent
> does not reorder type definitions; it just preserves the minimal
> set of explicit string forward-references the file already needs
> to compile.

```python
# BEFORE — backend/modules/refunds/services/shopify_refund_service.py
# (Reference only — Stage 5 § 5.k.0 DELETES this file outright; the
# example below is preserved as a reference for any future file with a
# similar shape.)
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List, Dict, Any

class SomeService:
    def __init__(self, client: Optional[ClientType] = None) -> None: ...

    async def cancel_order(
        self,
        order_id: str,
        approved_by: str,
        reason: str = "CUSTOMER",
        restock: bool = False,
        notify_customer: bool = False,
        staff_note: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    async def create_refund_to_original_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "USD",
        notify: bool = False,
        note: Optional[str] = None,
        transactions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]: ...
```

```python
# AFTER — modernized (reference shape — actual file is deleted by Stage 5 § 5.k.0)
from decimal import Decimal
from typing import Any

class SomeService:
    def __init__(self, client: ClientType | None = None) -> None: ...

    async def cancel_order(
        self,
        order_id: str,
        approved_by: str,
        reason: str = "CUSTOMER",
        restock: bool = False,
        notify_customer: bool = False,
        staff_note: str | None = None,
    ) -> dict[str, Any]: ...

    async def create_refund_to_original_payment(
        self,
        order_id: str,
        amount: Decimal,
        currency: str = "USD",
        notify: bool = False,
        note: str | None = None,
        transactions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...
```

### 6.g.6 — Files explicitly OUT OF SCOPE (do NOT touch)

The Stage 6 cleanup is scoped to FILES CREATED OR MODIFIED BY STAGES
1–5 ONLY. The following are pre-existing files / convention drift
that belongs to other specs or earlier eras of the codebase; the
Stage 6 sub-agent IGNORES any matches its grep returns in these
paths:

- `backend/utils/dict_utils/check_dict_equivalence.py`
- `backend/utils/dict_utils/flatten_dict_data.py`
- `backend/utils/date_utils/parse_off_dates.py`
- `backend/utils/datetime/**`
- `backend/utils/spreadsheets/**`
- `backend/utils/interaction/**`
- `backend/legacy/**`
- `backend/services/**` — pre-existing legacy services (the non-`legacy`
  twins from Stage 3 migration)
- `backend/lib/clients/shopify_client/**` — deprecated underscore
  client
- `backend/routers/admin.py`, `backend/routers/slack_api.py`
- `backend/core/**`
- `backend/tests/**` — pre-existing test infra; Stage 6 doesn't
  refactor tests

If a grep returns matches in any of the above paths, the sub-agent
IGNORES those matches — they belong to a future spec or were never
in scope.

### 6.g.7 — Reconciliation with Stage 5 § 5.l

Stage 5 § 5.l also documents a Python-conventions sweep across
stages 1–5. The two are intentionally redundant: § 5.l fires inside
Stage 5's own implementation as a defensive double-check, and § 6.g
fires inside Stage 6's implementation as the canonical owner.
Running both is safe (idempotent — the second pass finds zero hits
because the first pass cleaned them). If § 5.l ships first (Stage 5
runs ahead of Stage 6), § 6.g's grep returns zero hits and the
sub-agent only verifies clean state. If § 6.g ships first, § 5.l's
grep returns zero hits and the same. The canonical owner of the
retroactive cleanup is Stage 6 § 6.g — Stage 5 § 5.l is a
belt-and-suspenders check.

### 6.g.8 — § 6.g deliverables checklist

- [ ] Every file in § 6.g.2's "remove `from __future__`" list has
      the import removed. Verifiable by
      `! grep -rn "from __future__ import annotations" <files>` returning
      no matches.
- [ ] Every file in § 6.g.2's "deprecated typing forms" list has
      its `from typing import` line trimmed and its annotations
      rewritten per § 6.g.3. Verifiable by the § 6.g.5 compound grep
      returning no matches.
- [ ] `from typing import …` lines in scope keep only the symbols
      listed in § 6.g.4. Verifiable by manual review of each
      `from typing import` line in the in-scope files.
- [ ] `uv run ruff check backend/modules/refunds/ backend/modules/orders/ backend/utils/ backend/main.py backend/routes.py`
      passes.
- [ ] Smoke imports succeed:
      `uv run python -c "import modules.refunds.controllers.refunds_controller; import modules.refunds.services.estimate_service; import modules.orders.controllers.orders_controller"`
      exits 0.
- [ ] No file under `backend/modules/refunds/`,
      `backend/modules/orders/`, or the touched `backend/utils/`
      files has `from __future__ import annotations`.
- [ ] No file under those same paths imports `Optional`, `List`,
      `Dict`, `Tuple`, `Set`, `FrozenSet`, `Type`, or `Union` from
      `typing`.
- [ ] No file under those same paths uses `Optional[X]`,
      `Union[A, B]`, `List[X]`, `Dict[K, V]`, `Tuple[...]`, `Set[X]`,
      `FrozenSet[X]`, or `Type[X]` in any annotation.

---

## 6.h — Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `backend/modules/refunds/tests/test_create_response_shape.py` —
  TypedDict structural-conformance sanity. Verifies that a
  controller-built dict (the literal from Stage 5 § 5.d's return
  statement) is assignable to the `CreateRefundResponse` TypedDict
  and survives `json.dumps` round-trip without key renaming.
- (Other tests overlap with Stage 5's planned tests — e.g.
  `test_refunds_controller_create.py` — and are NOT duplicated here.
  The TypedDict shape is exercised indirectly by Stage 5's
  controller tests; Stage 6 only adds the dedicated structural-
  conformance test as a focused contract check.)

---

## Cross-references

- **Depends on:** Stage 5 (the controller produces the dict that
  conforms to this shape; Stage 6 documents the shape but does not
  build it). Stage 5 must land § 5.b / § 5.c / § 5.d before Stage 6's
  § 6.b / § 6.c / § 6.d are accurate.
- **Can run in parallel with:** Stage 7 (the wire-contract design
  here and the Slack-side renderer can be designed concurrently
  once Stage 5's response shape is fixed). Stage 6's § 6.g cleanup
  also runs independently — it touches Python files only, while
  Stage 7's work is TS-only on the Slack side.
- **Blocks:** Stage 7 (the Slack renderer reads `CreateRefundResponse`
  field-by-field; the field-by-field contract in § 6.c is the
  authoritative reference Stage 7's renderer follows).

---

## 6.todo — Orchestrator TODOs (apply to design.md when accumulating)

These items are sub-agent feedback for the orchestrator; they affect
`design.md` (decisions log + open questions section) and are out of
scope for the Stage 6 implementation sub-agent itself.

1. **Casing convention authoritative source.** § 5.b.1 (Stage 5) is
   the canonical casing rule for the spec — Python snake_case
   identifiers, TS camelCase identifiers, wire JSON camelCase keys
   directly on TypedDicts (no `to_camel(...)` boundary helper). The
   orchestrator should retire the older D32 / § 5.casing formulation
   that introduced `to_camel(...)` machinery — it is superseded by
   § 5.b.1. Stage 6's § 6.b / § 6.f deliverables call out the
   `! grep -rn "to_camel(" ...` verification that confirms § 5.b.1
   landed.

2. **Q7 (`restockTo` lane consumption downstream) remains deferred**
   to a follow-up inventory-restock spec. Stage 5 § 5.e already maps
   the four lanes down to the boolean Shopify expects today. Stage 6
   does NOT need to act on Q7.

3. **No new decisions.** Stage 6 introduces no new design decisions;
   it documents Stage 5's response shape and runs the retroactive
   Python-conventions cleanup. The cleanup itself is governed by
   D33 (Python 3.14+ conventions) which Stage 5 already records.
