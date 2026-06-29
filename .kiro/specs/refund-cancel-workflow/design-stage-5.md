# Design — Stage 5: Cancel + refund execution [DETAILED]

> Parent: see [design.md](./design.md) for the overall feature design and Stages 1-3.

> Stage 5 wires `POST /refunds/create` (and the missing
> `DELETE /orders/{id}` route) to call the canonical `shop_client.py`
> directly. Per **D30** there is no `ExecuteService` orchestrator and
> per the user's "no overloaded methods / no `cancel_order` +
> `create_refund` wrapper" directive there is no `ShopifyRefundService`
> class either — the cancel-then-refund branching (~10 lines) lives
> directly in the FastAPI controller, and each Shopify mutation is
> invoked via `shopify_client.run(schema.<resource>.<queries|mutations>.<name>, **kwargs)`
> verbatim from the call site. Per **D31** every Shopify call uses that
> existing pattern with no wrapper layer in between.

> **Sub-agent execution order.** Stage 5's substages run in this order:
>
> 1. **§ 5.k FIRST** — retroactive cleanup of Stages 1–3 (Stage 3
>    service-class teardown, inline one-line factories, drop the
>    `"full"` restockTo literal, move wire-shape types out of
>    `domain/refund/api.ts`, snake_case audit). The dependent code in
>    `refunds_controller.py`, `approve_modal.ts`, `send_request_for_eval.ts`
>    must be in its final shape BEFORE Stage 5's new code lands.
> 2. **§ 5.l** — Python conventions sweep across stages 1–5
>    (no `from __future__ import annotations`, no uppercase `List` /
>    `Dict` / `Optional`).
> 3. **§ 5.m** — Stage 1 deferred backend wire-up
>    (`functions/send_request_for_eval.ts` actual `validateRefund` POST
>    - approval-modal push).
> 4. **THEN § 5.b → § 5.j** — new `CreateRefundRequest` model, new
>    `CreateRefundResponse` TypedDicts, controller extension,
>    `orders_controller.py`, route wiring, error-handling audit, and
>    deliverables checklist.

## Endpoint contracts

```http
POST /refunds/create
Content-Type: application/json

{
  "orderId":   "gid://shopify/Order/5234567890",
  "productId": "gid://shopify/Product/7590021333086",
  "refundTo":  "original_method",
  "amount":    87.50,
  "cancel":    true,
  "refund":    true,
  "restockTo": "general",
  "notify":    true,
  "approvedBy": "U123ABC",
  "isTest":    false
}

→ 200 OK
{
  "ok": true,
  "cancel":  { "jobId": "gid://shopify/Job/...", "jobDone": true } | null,
  "refund":  { "refundId": "gid://shopify/Refund/...", "amount": 87.50, "currency": "USD",
               "createdAt": "2025-02-12T19:11:43Z" } | null,
  "errors":  []
}
```

```http
DELETE /orders/{order_id}
Content-Type: application/json

{
  "approvedBy":     "U123ABC",
  "reason":         "CUSTOMER",
  "restock":        false,
  "notifyCustomer": false
}

→ 200 OK
{
  "jobId":   "gid://shopify/Job/...",
  "jobDone": true
}
```

### Field requirements (CreateRefundRequest)

| Field        | Required                                     | Notes                                                                                                          |
| ------------ | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `orderId`    | REQUIRED                                     | Shopify order GID — round-tripped from `/refunds/validate` response.                                           |
| `productId`  | REQUIRED                                     | Shopify product GID — round-tripped from `/refunds/validate` response.                                         |
| `refundTo`   | REQUIRED                                     | `"original_method" \| "store_credit"`.                                                                         |
| `amount`     | REQUIRED on refund; `null` when cancel-only. | Number.                                                                                                        |
| `cancel`     | OPTIONAL                                     | Defaults to `false` when omitted.                                                                              |
| `refund`     | OPTIONAL                                     | Defaults to `false` when omitted.                                                                              |
| `restockTo`  | OPTIONAL                                     | One of `"veteran" \| "early" \| "general" \| "waitlist"`. Omit the field entirely when no restock is intended. |
| `notify`     | OPTIONAL                                     | Defaults to `false` when omitted.                                                                              |
| `approvedBy` | REQUIRED                                     | Slack user id of the approver.                                                                                 |
| `isTest`     | OPTIONAL                                     | Defaults to `false` when omitted.                                                                              |

`orderId` and `productId` round-trip through the picker modal's
`private_metadata` and the `ApproveModalMeta` (`{orderId, productId}`). The
backend re-fetches the order on `/refunds/create` to derive transactions,
currency, and customer info fresh from Shopify. No opaque `orderMetadata`
blob is round-tripped — the small field set keeps Slack `private_metadata`
well within its 3 KB ceiling. (D17.)

**No `idempotencyKey` field** (D18). Shopify's own dedup on `refundCreate`
rejects duplicate refund attempts (the canonical `refund_create` op in
`backend/lib/clients/shopify-client/shop_client.py` is declared
`idempotent=True`, and the Admin API rejects a second mutation with a
user-error response). A duplicate `/refunds/create` POST surfaces to the
operator as a 422 with the user-error message; the backend does not
maintain its own dedup store.

## Shopify mutations involved (existing pattern verbatim — D31)

Per D31, Stage 5 uses the existing `client.run(schema.x.y.z, **kwargs)`
pattern verbatim — verified against
`backend/lib/clients/shopify-client/shop_client.py` and existing successful
call sites (`backend/legacy/services/refunds/service.py:187,225,238` and
`backend/legacy/services/orders/service.py:45`). NO constructor-based
mutation invocations, NO typed input dataclasses, NO `MutationOp(...)`
direct construction, NO new client primitives. The deprecated
`backend/lib/clients/shopify_client/` (underscore) directory is NOT
referenced.

Per the user's direction "ensure that `orderCancel` and `refundCreate` are
not combined into a wrapper. call path should call them separately in the
logic. no overloaded methods", Stage 5 deletes the `ShopifyRefundService`
class entirely (Stage 3 introduced it as a thin wrapper around
`client.run(...)`; that wrapper layer adds nothing and is gone). The
cancel + refund mutations are invoked directly from the controller via
the canonical `shopify_client.run(schema.<resource>.<mutations|queries>.<name>, **kwargs)`
client method:

- **Cancel** (when `cancel === true`):
  `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
  — does NOT pass `refund_method` (Property 7 — cancel never implicitly
  refunds).
- **Refund to original payment** (when `refund === true && refund_to === "original_method"`):
  `shopify_client.run(schema.refunds.mutations.create, **refund_kwargs)`
  with `transactions=[OrderTransactionInput!]` built from the order's
  parent SALE/CAPTURE.
- **Refund to store credit** (when `refund === true && refund_to === "store_credit"`):
  `shopify_client.run(schema.refunds.mutations.create, **refund_kwargs)`
  with `refund_methods=[{ "storeCreditRefund": { "amount": { ... } } }]`.

Each call is a single line in the controller. The controller's if/else
picks WHICH call to make. There is no `cancel_and_refund(...)` wrapper,
no `create_refund(refund_to=...)` overload, no service class — the
controller is the call site.

Input building (turning the `CreateRefundRequest` body + a re-fetched
order into the `**kwargs` for each `client.run`) lives in plain
module-level functions:

- `backend/modules/refunds/inputs.py::build_cancel_kwargs(order_id, approved_by, restock, notify_customer)`
  → `dict[str, Any]` ready for splatting into `client.run`.
- `backend/modules/refunds/inputs.py::build_refund_kwargs(order_id, amount, refund_to, currency, notify, transactions=None)`
  → `dict[str, Any]` ready for splatting into `client.run`. Internally
  delegates to the business-agnostic helpers in
  `backend/utils/shopify_refunds.py` (next bullet) to translate the
  raw transactions list into `[OrderTransactionInput!]` or to build
  `[RefundMethodInput!]` for the store-credit branch.

The transaction-side primitives are business-agnostic and live one level
out, in `backend/utils/shopify_refunds.py`:

- `parent_capture_txn(transactions: list[dict]) -> dict | None`
- `build_refund_transactions_for_shopify(order_id: str, amount: Decimal, transactions: list[dict]) -> list[dict]`
- `build_store_credit_refund_methods(amount: Decimal, currency: str) -> list[dict]`

These take and return primitives only (`list[dict]`, `Decimal`, `str`).
They have NO domain knowledge of refund requests / Slack approvals /
estimate ladders. Tests exercise them as pure functions with no Shopify
client involved.

> **Cancel + refund stay separate end-to-end.** When both are requested
> the controller calls cancel first (one `client.run`), then calls one
> of the two refund variants (one `client.run`). They are NOT combined
> into a single `cancel_and_refund(...)` wrapper anywhere — the call
> path invokes each Shopify mutation through its own `client.run`,
> preserving independent observability / error surface for each step.

## Happy-path-only callout

Per user preference, Stage 5 assumes:

- Order validated; ids match; transactions array is well-formed.
- No partial-refund or split-payment edge cases.
- No deny path — Slack does not call `/refunds/deny` in this stage. (The
  existing `handleDenyButton` handler stays as-is and remains a Slack-only
  finalizer. D9.)

Errors from Shopify (user errors, network) are surfaced through the global
exception handler registered in `backend/main.py` (Stage 3 § 3.e). The
controller adds a small local try/except around the cancel-then-refund
sequence ONLY to capture partial-success state (cancel succeeded, refund
failed) — see § 5.d.

---

## 5.a — File inventory (concrete)

```
backend/modules/refunds/
├── controllers/
│   └── refunds_controller.py        # EXTEND — Stage 2 created the file with /validate;
│                                    #   Stage 5 adds POST /refunds/create.
├── inputs.py                        # NEW — module-level functions only:
│                                    #   build_cancel_kwargs(order_id, approved_by, restock, notify_customer) -> dict
│                                    #   build_refund_kwargs(order_id, amount, refund_to, currency, notify, transactions=None) -> dict
│                                    #   NO class. NO methods. Domain helpers that build the **kwargs
│                                    #   dicts the controller splats into shopify_client.run(...).
├── models/
│   ├── refund_request.py            # EXISTING (Stage 2) — RefundRequest (incoming /validate body).
│   ├── estimate.py                  # EXISTING (Stage 2) — TypedDicts for the validate response;
│                                    #   camelCase keys per § 5.b.1.
│   ├── create_request.py            # NEW — CreateRefundRequest (incoming Pydantic, /refunds/create body).
│   └── create_response.py           # NEW — TypedDicts for outgoing response shape (D28);
│                                    #   camelCase keys declared directly per § 5.b.1.
└── services/
    ├── estimate_service.py          # EXISTING (Stage 2) — untouched by Stage 5.
    └── shopify_refund_service.py    # DELETED in § 5.k.0 — Stage 3's wrapper class is gone.
                                     #   The static helpers move to utils/shopify_refunds.py.

backend/utils/
└── shopify_refunds.py               # NEW (§ 5.k.0) — module-level functions only,
                                     #   moved from ShopifyRefundService static helpers:
                                     #     parent_capture_txn(transactions) -> dict | None
                                     #     build_refund_transactions_for_shopify(order_id, amount, transactions) -> list[dict]
                                     #     build_store_credit_refund_methods(amount, currency) -> list[dict]
                                     #   Takes/returns primitives only — no domain types.

backend/modules/orders/
└── controllers/
    └── orders_controller.py         # NEW — DELETE /orders/{order_id} lives here because the
                                     #   refunds_controller's APIRouter prefix is `/refunds` and
                                     #   FastAPI does not let one router emit a path under a
                                     #   different prefix. See § 5.f.

backend/routes.py                    # EXTEND — include the new orders_controller; Stage 2 already
                                     #   wired refunds_controller. Stage 5 also DELETES the inline
                                     #   stubs at lines 76 (`@orders.delete("")`) and 80
                                     #   (`@refunds.post("")`).

backend/main.py                      # NO CHANGE — the Stage 3 ShopifyUserError exception handler
                                     #   already covers Stage 5's error surface. The exception
                                     #   class itself moves out of the deleted shopify_refund_service.py
                                     #   into utils/shopify_refunds.py in § 5.k.0; main.py's
                                     #   import path updates accordingly (one-line change, listed
                                     #   in § 5.k.0 deliverables).

slack-apps/registrations/domain/refund/action_requests.ts  # UPDATE — point at POST /refunds/create
                                     #   when `BARS_API_URL` is set; existing Lambda path stays as
                                     #   the fallback. Touched only at the URL-resolution boundary;
                                     #   the body shape is already aligned with `CreateRefundRequest`
                                     #   from Stage 1.
```

> **Stage 4 already cleaned up legacy Lambda code paths.** The previous
> draft of Stage 5 listed `backend/legacy/services/refunds/service.py:execute_refund_create`
> as an "OPTIONAL DELETE" cleanup target and called out the legacy
> `RefundEvaluationPayload` type. Stage 4 owns those cleanups and they
> have already landed; Stage 5 does NOT re-do them. The legacy file is
> referenced here only as historical context for where the
> business-agnostic helpers in `backend/utils/shopify_refunds.py` were
> originally lifted from.

> **Sub-agent: read first.** Before extending `refunds_controller.py`,
> confirm Stage 2's existing `validate` controller layout (router prefix,
> `Depends(EstimateService)` form post-§5.k.1, response*model handling).
> The Stage 5 additions reuse `Depends(ShopifyClient)` for the canonical
> client and match the `response_model=dict` (or omitted) convention so
> the module reads cohesively. NO `get*\*\_service()` factories anywhere.

---

## 5.b — Pydantic model — `CreateRefundRequest` (incoming validation)

Pydantic is used here because this is an INCOMING external request body
(D28). Outgoing responses below are constructed as plain dicts / TypedDicts.

```python
# backend/modules/refunds/models/create_request.py
from typing import Literal
from pydantic import BaseModel, Field


class CreateRefundRequest(BaseModel):
    """The full /refunds/create request body sent by the Slack handler.

    Renamed from the legacy `RefundExecuteRequest` shape for naming
    consistency with `RefundRequest` (Stage 2 / `POST /refunds/validate`)
    and `RefundRequestEval` (the validate-response wire shape).

    Field-requirement deltas vs. the prior shape:

    - `restockTo` REPLACES `restock`. The old `"none"` / `"no_restock"` /
      `"admin_hold"` / `"full"` literals are gone; the field is OMITTED
      entirely when no restock is intended. The final lane set is
      `"veteran"`, `"early"`, `"general"`, `"waitlist"` — four lanes
      only. If "full restock" semantics are needed downstream the
      inventory consumer infers it from `restockTo` being absent vs.
      present, not from a separate enum value.
    - `cancel`, `refund`, `notify`, `isTest` are OPTIONAL with `False`
      defaults.
    - `amount` is `float | None` — `None` when cancel-only.
    - NO `idempotencyKey` (D18) — Shopify's own dedup is sufficient.
    - NO top-level `restock` boolean (replaced by `restockTo`).
    - NO `slackChannel` (channel routing happens entirely on the Slack
      side; the backend never receives a channel hint).
    - NO `source` (the request always originates from Slack — there is no
      other source).
    - NO `policyConfirmation` (form gates submission on it; backend does
      not consume it).
    """

    order_id:    str                                                       = Field(..., alias="orderId")
    product_id:  str                                                       = Field(..., alias="productId")
    refund_to:   Literal["original_method", "store_credit"]                = Field(..., alias="refundTo")
    amount:      float | None                                              = None
    cancel:      bool                                                      = False
    refund:      bool                                                      = False
    restock_to:  Literal["veteran", "early", "general", "waitlist"] | None = Field(None, alias="restockTo")
    notify:      bool                                                      = False
    approved_by: str                                                       = Field(..., alias="approvedBy")
    is_test:     bool                                                      = Field(False, alias="isTest")

    model_config = {"populate_by_name": True}
```

REMOVED from the previous shape:

- `restock` boolean (renamed/replaced with the richer `restock_to` enum).
- The `"none"`, `"no_restock"`, `"admin_hold"` literals (gone — the field
  is omitted when no restock is intended).
- `idempotency_key` (Shopify's own dedup is sufficient; D18).
- `slackChannel`, `source`, `policyConfirmation` (none consumed by the
  backend).

ADDED:

- `restock_to` literals `"veteran"`, `"early"`, `"general"` alongside the
  existing `"waitlist"`. The final wire enum is the four lanes only —
  the prior `"full"` literal is dropped (it never matched a Shopify
  primitive; "full restock" was conceptual and is now expressed as
  `restock=True` at the cancel-mutation boundary regardless of which
  lane the inventory consumer routes to).

---

## 5.b.1 — Casing conventions

> **Python files — snake_case.** All Python identifiers (function
> names, variables, parameters, model field names) use `snake_case`.
> Pydantic models bridge to camelCase wire JSON via
> `Field(..., alias="camelCase")` + `model_config = {"populate_by_name": True}`
> on each model class. Internal-only dataclasses / TypedDicts that are
> never serialized to JSON (e.g. `EstimateRequest` consumed inside
> `EstimateService`) use snake_case with no aliases.
>
> **TypeScript / JavaScript files — camelCase.** All TS/JS identifiers
> (interface fields, function names, variables) use `camelCase`. Wire
> JSON between Slack and the backend uses camelCase keys; the backend's
> Pydantic aliases handle the snake_case ↔ camelCase translation on
> incoming bodies.
>
> **Wire JSON — camelCase only.** All `POST` / `DELETE` request bodies
> and response payloads use camelCase keys. The backend's outgoing
> `RefundRequestEval` and `CreateRefundResponse` are TypedDicts with
> camelCase keys (matching what the Slack app expects) — that is the
> wire-shape exception to the "Python identifiers are snake*case"
> rule. The TypedDict's keys are quoted strings that mirror the wire
> JSON; they are NOT Python identifiers (you cannot `eval*.amountPaid`them; you must subscript`eval\_["amountPaid"]`), so the convention
> stays consistent: Python identifiers are snake_case end-to-end, and
> wire-shape TypedDict keys are camelCase strings to match the JSON
> they describe.
>
> **No mixed casing within a single file.** A Python file does not
> contain `camelCase` Python identifiers (variable names, function
> names, dataclass field names, Pydantic field names). A TS file does
> not contain `snake_case` identifiers (other than string-literal
> field names that match the wire JSON, which the wire shape demands
> — but the wire JSON itself is camelCase, so even string literals on
> the TS side stay camelCase).
>
> **Boundary helpers.** Pydantic's `Field(..., alias="...")` mechanism
> handles the camelCase → snake_case conversion on incoming bodies
> automatically (no helper function needed). Outgoing TypedDicts that
> mirror the wire shape are built with camelCase keys directly at the
> construction site; the dict the controller builds IS the wire JSON.

---

## 5.c — Outgoing response shape — `CreateRefundResponse` TypedDict (NOT Pydantic — D28; camelCase keys per § 5.b.1)

Per D28, outgoing responses constructed by the backend use TypedDict /
dataclass / dict — never Pydantic `BaseModel`. Per § 5.b.1 the
TypedDict keys are camelCase strings — they mirror the wire JSON
directly, so no boundary helper is needed; the controller returns the
TypedDict as-is.

```python
# backend/modules/refunds/models/create_response.py
from typing import TypedDict


class CancelOutcome(TypedDict):
    """Payload returned when `body.cancel` was True and the cancel
    succeeded. Mirrors `OrderCancelPayload.job` from Shopify.

    camelCase keys per § 5.b.1 — the TypedDict mirrors the wire JSON
    directly (`jobId` / `jobDone`).
    """

    jobId: str
    jobDone: bool


class RefundOutcome(TypedDict):
    """Payload returned when `body.refund` was True and the refund
    succeeded. Mirrors `RefundCreatePayload.refund.{id, …}` from Shopify.

    camelCase keys per § 5.b.1 — the TypedDict mirrors the wire JSON
    directly (`refundId` / `createdAt`).
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

    camelCase keys per § 5.b.1 — the TypedDict mirrors the wire JSON
    directly; the controller returns it as-is.
    """

    ok: bool
    cancel: CancelOutcome | None
    refund: RefundOutcome | None
    errors: list[dict]       # Shopify user-error dicts (`{field, message, code?}`)
```

The Slack-side TypeScript mirror (`CreateRefundResponse` in
`slack-apps/registrations/domain/refund/types.ts` post-§ 5.k.4) reads
the camelCase wire JSON and is field-compatible. The backend half of the
contract is owned by Stage 5; the camelCase boundary is the only place
the two sides meet — no shared schema file, no codegen.

> **TS-side relocation.** The Slack-side `CreateRefundResponse`,
> `CancelOutcome`, `RefundOutcome`, and `RefundRestockTo` types currently
> live in `slack-apps/registrations/domain/refund/api.ts` (the
> domain-coupled API wrapper file the user wants gone). The Stage 5
> retroactive cleanup substage (§ 5.k.4) physically moves these to
> `slack-apps/registrations/domain/refund/types.ts`, deletes
> `domain/refund/api.ts` outright, and updates `RefundRestockTo` to drop
> `"full"`. Stage 5's design references the wire shape from `types.ts`
> only.

---

## 5.d — Controller body (full code, NO orchestrator, NO service class)

Extend `backend/modules/refunds/controllers/refunds_controller.py` (Stage 2
created it with `@router.post("/validate")`):

> **Why `Depends(ShopifyClient)` and not a one-line factory?** The
> user's directive: every one-line wrapper must be inlined. FastAPI's
> `Depends(...)` accepts any callable; passing the class itself works
> because `ShopifyClient.__init__(...)` reads its config from the
> environment when no args are passed (the constructor reads
> `SHOPIFY__STORE_ID` / `SHOPIFY__API_VERSION` / `SHOPIFY__TOKEN__ADMIN`).
> Tests override the dependency the standard FastAPI way:
> `app.dependency_overrides[ShopifyClient] = lambda: FakeShopifyClient(...)`.
> No `get_shopify_client()` / `get_shopify_refund_service()` /
> `get_estimate_service()` factories exist anywhere in the codebase
> after this stage; they were one-line indirection that earned no
> abstraction value.
>
> **Inlining: FastAPI accepts the class directly as a `Depends`
> callable; no factory wrapper needed.** The form
> `service: SomeClass = Depends(SomeClass)` is the FastAPI-idiomatic
> way to inline a zero-argument factory. A `def get_some_class() -> SomeClass: return SomeClass()`
> definition next to it is pure indirection — it has the same observable
> behavior as `Depends(SomeClass)` and exists only to give the parameter
> a different referent in the source. Stage 5 deletes every such
> wrapper in scope (§ 5.k.1 covers Stage 2's `get_estimate_service`;
> § 5.k.5 covers any others discovered during execution).

### Refund-domain input builders (NO class)

Per the user's "no overloaded methods / no orchestrator class /
controller calls each `client.run` separately" directive, refund-domain
input building lives in plain module-level functions at
`backend/modules/refunds/inputs.py`. NO class. NO methods. Each function
takes the small set of primitives the controller already has and returns
a `dict[str, Any]` ready to splat into `shopify_client.run(...)`.

```python
# backend/modules/refunds/inputs.py
from decimal import Decimal
from typing import Any, Literal

from utils.shopify_refunds import (
    build_refund_transactions_for_shopify,
    build_store_credit_refund_methods,
)


def build_cancel_kwargs(
    *,
    order_id: str,
    approved_by: str,
    restock: bool = False,
    notify_customer: bool = False,
    reason: str = "CUSTOMER",
) -> dict[str, Any]:
    """Build the **kwargs for `client.run(schema.orders.mutations.cancel, ...)`.

    Does NOT include `refund_method` (Property 7 — cancel never
    implicitly refunds). The returned dict is splat directly into
    `client.run(...)` at the call site.
    """
    return {
        "order_id": order_id,
        "reason": reason,
        "restock": restock,
        "notify_customer": notify_customer,
        "staff_note": f"Slack-approved cancel (by {approved_by})",
    }


def build_refund_kwargs(
    *,
    order_id: str,
    amount: Decimal,
    refund_to: Literal["original_method", "store_credit"],
    currency: str = "USD",
    notify: bool = False,
    note: str | None = None,
    transactions: list[dict] | None = None,
) -> dict[str, Any]:
    """Build the **kwargs for `client.run(schema.refunds.mutations.create, ...)`.

    Routes to the original-payment branch or the store-credit branch
    based on `refund_to`. Both branches share the common kwargs
    (`order_id`, `currency`, `note`, `notify`); the branch-specific
    field (`transactions=` vs. `refund_methods=`) is added by the
    business-agnostic helpers in `utils.shopify_refunds`.

    For the original-payment branch the caller MUST pass `transactions`
    (the order's existing transactions list, used to derive the parent
    SALE/CAPTURE for the refund). The controller's call path always
    re-fetches the order before calling this function so `transactions`
    is always populated.
    """
    note = note or "Refund approved via Slack workflow"
    common: dict[str, Any] = {
        "order_id": order_id,
        "currency": currency,
        "note": note,
        "notify": notify,
    }
    if refund_to == "store_credit":
        common["refund_methods"] = build_store_credit_refund_methods(amount, currency)
    else:  # original_method
        if transactions is None:
            raise ValueError(
                "build_refund_kwargs(refund_to='original_method') requires transactions list",
            )
        common["transactions"] = build_refund_transactions_for_shopify(
            order_id, amount, transactions,
        )
    return common
```

### Controller body — the call site

The controller picks WHICH `client.run(...)` to invoke and splats the
kwargs the input builder returned. The check on `payload.user_errors`
that used to live inside the deleted `ShopifyRefundService` methods
moves inline — one line per mutation.

> **Invariant — separate calls, no combined wrapper.** The cancel and
> refund mutations are issued separately, end-to-end. Concretely:
>
> - `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
>   issues the cancel mutation. Its kwargs come from
>   `build_cancel_kwargs(...)` and contain only cancel-specific
>   primitives (`order_id`, `reason`, `restock`, `notify_customer`,
>   `staff_note`).
> - `shopify_client.run(schema.refunds.mutations.create, **refund_kwargs)`
>   issues the refund mutation. Its kwargs come from
>   `build_refund_kwargs(...)` and contain only refund-specific
>   primitives (`order_id`, `currency`, `note`, `notify`, plus either
>   `transactions` or `refund_methods` depending on the branch).
>
> The two are never combined into a single method or "execute both"
> helper. The controller calls them sequentially based on `body.cancel`
> and `body.refund` flags. There are no overloaded method signatures —
> `build_cancel_kwargs` takes one set of inputs and `build_refund_kwargs`
> takes another; neither function inspects nor invokes the other; and
> there is no `cancel_and_refund(...)` / `execute_refund_with_cancel(...)`
> / `cancel_then_refund(...)` wrapper at any layer (controller,
> `inputs.py`, `utils/shopify_refunds.py`).
>
> Earlier drafts of Stage 5 considered a `ShopifyRefundService` class
> with `cancel_order(...)` and `create_refund(...)` methods; § 5.k.0
> deletes that class outright (the wrapper layer added nothing the
> controller can't do at the call site). The invariant restated in
> service-class terms — for any reviewer comparing the diff: even if
> the class were resurrected, `cancel_order(...)` would issue
> `schema.orders.mutations.cancel` and `create_refund(...)` would
> issue `schema.refunds.mutations.create`; the two would never be
> combined into a single method, and no method would be overloaded
> across the two operations.

```python
# backend/modules/refunds/controllers/refunds_controller.py (Stage 5 addition)
from decimal import Decimal

from fastapi import Depends

from shopify_client.shop_client import ShopifyClient, schema

from modules.refunds.inputs import build_cancel_kwargs, build_refund_kwargs
from modules.refunds.models.create_request import CreateRefundRequest
from modules.refunds.models.create_response import CreateRefundResponse
from utils.shopify_refunds import ShopifyUserError


# `response_model` is `dict` (or omitted entirely) — D28: outgoing responses
# constructed by the backend are NOT Pydantic models. The controller
# returns a dict shaped per `CreateRefundResponse` (TypedDict in
# modules/refunds/models/create_response.py) with camelCase keys
# declared directly per § 5.b.1 — no boundary helper, the dict is the
# wire JSON.
@router.post("/create")
async def create_refund(
    body: CreateRefundRequest,
    shopify_client: ShopifyClient = Depends(ShopifyClient),
) -> dict:
    """Cancel-then-refund execution.

    NO orchestrator service (D30). NO `ShopifyRefundService` class —
    the controller calls `shopify_client.run(...)` directly for each
    mutation (user directive: "ensure that orderCancel and refundCreate
    are not combined into a wrapper. call path should call them
    separately in the logic. no overloaded methods").

    Branching contract:
      - `cancel=True, refund=False` → cancel only (no refund mutation).
      - `cancel=False, refund=True` → refund only (no cancel mutation).
      - `cancel=True, refund=True`  → cancel first, then refund. If the
        cancel raises, the refund is skipped and the error surfaces. If
        the refund raises after a successful cancel, the response includes
        `cancel` populated, `refund=None`, and `errors[]` non-empty —
        partial-success state visible to the operator.
      - `cancel=False, refund=False, amount=None` → no-op; returns
        `{ok: True, cancel: None, refund: None, errors: []}`.

    Property 7 (cancel without implicit refund) is preserved because
    `build_cancel_kwargs(...)` does NOT include a `refund_method` key
    in the dict it returns; that key never reaches
    `schema.orders.mutations.cancel`.
    """

    cancel_outcome: dict | None = None
    refund_outcome: dict | None = None
    errors: list[dict] = []

    try:
        if body.cancel:
            # Shopify's `orderCancel` mutation takes a single boolean
            # `restock`; the richer `restock_to` lane (veteran / early /
            # general / waitlist) is consumed by the inventory layer
            # downstream — NOT by the cancel mutation itself. Mapping:
            # presence-of-restock_to → restock=True. See § 5.e.
            cancel_kwargs = build_cancel_kwargs(
                order_id=body.order_id,
                approved_by=body.approved_by,
                restock=bool(body.restock_to),
                notify_customer=body.notify,
            )
            cancel_payload = shopify_client.run(
                schema.orders.mutations.cancel, **cancel_kwargs,
            )
            if cancel_payload.user_errors:
                raise ShopifyUserError("orderCancel", list(cancel_payload.user_errors))
            cancel_outcome = _cancel_outcome_from_payload(cancel_payload.to_dict())

        if body.refund and body.amount is not None and body.amount > 0:
            # `Decimal(str(...))` round-trip preserves the exact decimal
            # representation Slack sent us (avoids 1.20 → 1.2 truncation
            # that bare `Decimal(body.amount)` would produce on a float).
            amount = Decimal(str(body.amount))

            # For original-payment refunds we need the order's
            # transactions list to derive the parent SALE/CAPTURE.
            # Re-fetch fresh from Shopify (D17 — the round-trip is small,
            # the re-fetch is intentional and cheap).
            transactions: list[dict] | None = None
            if body.refund_to == "original_method":
                order = shopify_client.run(
                    schema.orders.queries.by_id, id=body.order_id,
                )
                transactions = list(order.transactions or []) if order else []

            refund_kwargs = build_refund_kwargs(
                order_id=body.order_id,
                amount=amount,
                refund_to=body.refund_to,
                notify=body.notify,
                transactions=transactions,
            )
            refund_payload = shopify_client.run(
                schema.refunds.mutations.create, **refund_kwargs,
            )
            if refund_payload.user_errors:
                raise ShopifyUserError("refundCreate", list(refund_payload.user_errors))
            refund_outcome = _refund_outcome_from_payload(
                refund_payload.to_dict(), refund_to=body.refund_to,
            )
    except ShopifyUserError as exc:
        # The exception handler registered in main.py (Stage 3 § 3.e)
        # ALSO catches `ShopifyUserError` and maps to 422 — but we catch
        # locally here so a partial-success cancel-then-refund (cancel
        # succeeded, refund failed) is still surfaced with both outcomes.
        # The local except never escapes to the global handler; the
        # response carries `errors[]` populated and `ok=False`.
        errors = exc.errors

    response: CreateRefundResponse = {
        "ok": not errors,
        "cancel": cancel_outcome,
        "refund": refund_outcome,
        "errors": errors,
    }
    # camelCase keys per § 5.b.1 — `_cancel_outcome_from_payload` and
    # `_refund_outcome_from_payload` already return camelCase-keyed
    # dicts that mirror the wire shape, so the controller returns the
    # response dict as-is.
    return response

def \_cancel_outcome_from_payload(payload: dict) -> dict:
"""Map Shopify's `OrderCancelPayload` dict → `CancelOutcome` shape
(camelCase keys per § 5.b.1 — mirrors the wire shape directly)."""
job = payload.get("job") or {}
return {
"jobId": job.get("id", ""),
"jobDone": bool(job.get("done", False)),
}

def \_refund_outcome_from_payload(payload: dict, \*, refund_to: str) -> dict:
"""Map Shopify's `RefundCreatePayload` dict → `RefundOutcome` shape
(camelCase keys per § 5.b.1 — mirrors the wire shape directly).
For the store-credit branch the `currency` field is set to
`"STORE_CREDIT"` so downstream consumers can distinguish it from
the original-payment branch without re-inspecting the request
body."""
refund = payload.get("refund") or {}
total = (refund.get("total_refunded_set") or {}).get("shop_money") or {}
currency = "STORE_CREDIT" if refund_to == "store_credit" else (total.get("currency_code") or "USD")
return {
"refundId": refund.get("id", ""),
"amount": float(total.get("amount") or 0.0),
"currency": currency,
"createdAt": refund.get("created_at", ""),
}

```

The response is constructed as a plain dict (D28: outgoing shapes are NOT
Pydantic) shaped per the `CreateRefundResponse` TypedDict in § 5.c. The
TypedDict keys are camelCase strings declared directly per § 5.b.1, so
the dict the controller builds IS the wire JSON — no boundary helper
involved.

> **Why not a global-handler-only error path?** When both `cancel` and
> `refund` are requested and the cancel succeeds but the refund fails, a
> globally-handled 422 would lose the cancel-succeeded outcome. The local
> try/except is a one-line cost that keeps partial-success state visible
> to the operator. For all other failure modes (cancel-only that fails,
> refund-only that fails, network errors), the global handler still
> produces the standard error response — there is no behavioral
> divergence between local and global paths for non-partial cases.

---

## 5.e — `restockTo` → Shopify mapping table

Shopify's `orderCancel` mutation only accepts a boolean `restock` flag;
the richer `restockTo` lane (veteran / early / general / waitlist) is
consumed by the inventory layer downstream, which is OUT OF SCOPE for
Stage 5. Stage 5's controller maps presence-of-restockTo into a boolean
and calls `cancel_order(restock=...)` with that boolean.

| `restock_to` value (Pydantic model field) | Boolean passed to `orderCancel` (Shopify) | Downstream "lane" (consumed where?) |
| ----------------------------------------- | ----------------------------------------- | ----------------------------------- |
| `None` (field omitted from request body)  | `False`                                   | _no restock_                        |
| `"veteran"`                               | `True`                                    | veteran lane (future — see Q7)      |
| `"early"`                                 | `True`                                    | early-bird lane (future — see Q7)   |
| `"general"`                               | `True`                                    | general lane (future — see Q7)      |
| `"waitlist"`                              | `True`                                    | waitlist lane (future — see Q7)     |

**Open question — Q7** (to be added to design.md's Open Questions section
by the orchestrator):

> **Q7 — How is the `restockTo` lane consumed downstream?** The cancel
> mutation receives only a boolean; the richer per-lane semantics
> (veteran / early / general / waitlist) need a separate consumer
> — likely an inventory-restock service that subscribes to a Shopify
> webhook (or that the controller calls in sequence after a successful
> cancel). Stage 5 deliberately scopes that work out: it accepts the
> field, persists it on the wire (round-tripped through Slack), and maps
> it down to the boolean Shopify expects today. Future stage (or follow-up
> spec) wires the inventory consumer.

---

## 5.f — `DELETE /orders/{order_id}` route

The component-inventory table in design.md specifies a `DELETE /orders/{id}`
route. The existing stub in `backend/routes.py:76` is `@orders.delete("")`
(no path parameter, returning 204). Stage 5 replaces that stub with a real
controller mounted under the `/orders` prefix.

**Where it lives.** The refunds controller's `APIRouter` is declared with
`prefix="/refunds"` (Stage 2). FastAPI does not let one router emit a
path under a different prefix, so `DELETE /orders/{id}` lives in a NEW
file `backend/modules/orders/controllers/orders_controller.py` with its
own `APIRouter(prefix="/orders", tags=["orders"])`. The orders controller
calls `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
directly — same pattern as the cancel branch of `POST /refunds/create`,
no service-class wrapper in between.

```python
# backend/modules/orders/controllers/orders_controller.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shopify_client.shop_client import ShopifyClient, schema

from modules.refunds.inputs import build_cancel_kwargs
from utils.shopify_refunds import ShopifyUserError


router = APIRouter(prefix="/orders", tags=["orders"])


class CancelOrderRequest(BaseModel):
    """Incoming body for `DELETE /orders/{order_id}`. Pydantic because this
    is an incoming external request (D28)."""

    approved_by:     str        = Field(..., alias="approvedBy")
    reason:          str        = "CUSTOMER"
    restock:         bool       = False
    notify_customer: bool       = Field(False, alias="notifyCustomer")
    staff_note:      str | None = Field(None, alias="staffNote")

    model_config = {"populate_by_name": True}


@router.delete("/{order_id}")
async def cancel_order_route(
    order_id: str,
    body: CancelOrderRequest,
    shopify_client: ShopifyClient = Depends(ShopifyClient),
) -> dict:
    """Cancel a Shopify order.

    Pure cancel — no refund (Property 7). Builds the kwargs via
    `build_cancel_kwargs(...)` and invokes
    `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
    directly. NO service-class wrapper, NO orchestrator.

    Property 7 holds because `build_cancel_kwargs(...)` does NOT include
    a `refund_method` key in the dict it returns; that key never reaches
    `schema.orders.mutations.cancel`.

    Returns a `CancelOutcome`-shaped dict with camelCase keys
    (`{jobId, jobDone}`) per § 5.b.1 — the dict mirrors the wire JSON
    directly, no boundary helper.
    """
    cancel_kwargs = build_cancel_kwargs(
        order_id=order_id,
        approved_by=body.approved_by,
        reason=body.reason,
        restock=body.restock,
        notify_customer=body.notify_customer,
    )
    payload = shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)
    if payload.user_errors:
        raise ShopifyUserError("orderCancel", list(payload.user_errors))
    job = payload.to_dict().get("job") or {}
    return {
        "jobId": job.get("id", ""),
        "jobDone": bool(job.get("done", False)),
    }
```

`backend/routes.py` includes the new orders router and removes the inline
stubs:

```python
# backend/routes.py — Stage 5 deltas
from modules.orders.controllers.orders_controller import router as orders_router

# DELETE the inline `orders = APIRouter(prefix="/orders", ...)` block
# (lines 50-77 currently) — its three handlers are 204 stubs that this
# spec does not extend (`get_orders`, `update_order`, `cancel_order`).
# Stage 5 only owns DELETE /orders/{id}; the other two stubs are left in
# the new orders_controller.py as 204-returning placeholders so the route
# table doesn't regress.

router.include_router(orders_router)
```

> **Sub-agent: prefix conflict check.** Before deleting the inline
> `orders = APIRouter(...)` block, run
> `grep -rn "from routes import" backend/` to confirm no other module
> imports the inline router by name. Stage 2's refunds-controller
> precedent already moved the inline `refunds` router into
> `modules/refunds/controllers/refunds_controller.py`; Stage 5 mirrors
> that move for orders.

---

## 5.g — Error handling

Reuses Stage 3's `ShopifyUserError` → 422 mapping (already registered in
`backend/main.py` per Stage 3 § 3.e). Stage 5 does not register any new
exception handlers. The exception class itself moves out of the deleted
`shopify_refund_service.py` into `backend/utils/shopify_refunds.py`
(§ 5.k.0); `main.py` and any other importer update to the new path
(one-line import edit per file).

| Failure mode                                   | Where caught                                                                                           | HTTP response                                                                                                                                                 |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `orderCancel` user error (cancel-only)         | Global `ShopifyUserError` handler                                                                      | **422** with the `errors[]` payload from Shopify.                                                                                                             |
| `refundCreate` user error (refund-only)        | Global `ShopifyUserError` handler                                                                      | **422** with the `errors[]` payload.                                                                                                                          |
| `orderCancel` ok + `refundCreate` user error   | LOCAL try/except in `create_refund` controller (§ 5.d)                                                 | **200** with `{ok: false, cancel: <populated>, refund: null, errors: [...]}`. The local catch surfaces the cancel-succeeded state alongside the refund error. |
| Network failure (`httpx` exception)            | Bubbles up; global `handle_unhandled_exception` middleware in `backend/main.py`                        | **502** with a redacted error message; full trace logged.                                                                                                     |
| Pydantic validation failure on incoming body   | FastAPI's built-in 422 handler                                                                         | **422** with the standard FastAPI Pydantic-error payload.                                                                                                     |
| `body.amount is None` while `body.refund=True` | Controller short-circuits — falls into the no-op branch (returns `ok=True` with both outcomes `null`). | **200**. The Slack handler should never send this combination, but the controller is permissive.                                                              |
| Both `cancel=False` and `refund=False`         | Controller short-circuits                                                                              | **200** with `{ok: true, cancel: null, refund: null, errors: []}` — defensive no-op.                                                                          |

The global handler still catches any uncaught `ShopifyUserError` instances;
the controller's local try/except is purely to capture `errors[]` for
partial-success reporting.

---

## 5.k — Retroactive cleanup of Stages 1–3 (RUNS FIRST)

> **This substage runs BEFORE every other Stage 5 substage.** The
> dependent code in `refunds_controller.py`, `approve_modal.ts`,
> `send_request_for_eval.ts`, and `domain/refund/api.ts` must be in its
> final shape BEFORE the new Stage 5 code (§ 5.b through § 5.j) lands —
> otherwise Stage 5's new controller would be wiring against a Stage 1/2
> code shape that the user has since redirected.
>
> Per the user's directives "all one-line wrappers must be inlined", "api
> related signature logic should NOT be in the refund domain. it should
> ONLY be called via a domain-agnostic api layer", "ensure that
> orderCancel and refundCreate are not combined into a wrapper. call
> path should call them separately in the logic. no overloaded methods",
> and "go through stages 1/2/3 and add as a substage to stage 5".

### 5.k.0 — Stage 3 service-class teardown (delete `ShopifyRefundService`)

Stage 3 introduced `backend/modules/refunds/services/shopify_refund_service.py`
exposing a `ShopifyRefundService` class with `cancel_order(...)` /
`create_refund(...)` / `fetch_order_for_refund(...)` methods. Each
method is a 1:1 wrapper around `client.run(schema.x.y.z, **kwargs)`:
the wrapper layer adds nothing the controller can't do at the call site.

Per the user's directive ("ensure that orderCancel and refundCreate are
not combined into a wrapper. call path should call them separately in
the logic. no overloaded methods") this substage deletes the class
entirely and redistributes its content:

1. **DELETE the file** `backend/modules/refunds/services/shopify_refund_service.py`
   in full once the moves below are landed and all imports updated.

2. **MOVE** the static helpers (`_parent_capture_txn`,
   `_build_refund_transactions_for_shopify`,
   `_build_store_credit_refund_methods`) to
   `backend/utils/shopify_refunds.py` as **business-agnostic
   module-level functions**. Strip the leading underscore (they're now
   part of the module's public API). The new signatures:

   ```python
   # backend/utils/shopify_refunds.py
   from decimal import Decimal


   class ShopifyUserError(Exception):
       """Raised when Shopify returns non-empty user_errors on a mutation.

       Mapped to HTTP 422 by the FastAPI exception handler in `main.py`.
       Lifted out of the deleted `shopify_refund_service.py` so the
       exception class stays available to the new controller call sites
       and to any retained legacy callers.
       """

       def __init__(self, mutation: str, errors: list[dict]) -> None:
           super().__init__(f"{mutation}: {errors}")
           self.mutation = mutation
           self.errors = errors


   def parent_capture_txn(transactions: list[dict]) -> dict | None:
       """First txn whose `(kind, status)` matches `("CAPTURE"|"SALE", "SUCCESS")`."""

   def build_refund_transactions_for_shopify(
       order_id: str,
       amount: Decimal,
       transactions: list[dict],
   ) -> list[dict]:
       """Build `[OrderTransactionInput!]` for refund-to-original-payment.

       Raises `ShopifyUserError("refundCreate", ...)` when no eligible
       parent SALE/CAPTURE transaction is found.
       """

   def build_store_credit_refund_methods(
       amount: Decimal,
       currency: str,
   ) -> list[dict]:
       """Build `[RefundMethodInput!]` for the store-credit refund branch."""
   ```

   These functions take and return primitives only (`list[dict]`,
   `Decimal`, `str`). They have NO knowledge of refund requests / Slack
   approvals / estimate ladders. The implementation bodies are lifted
   verbatim from the deleted `ShopifyRefundService.@staticmethod` blocks
   (just the leading-underscore name change and module-level move).

3. **MOVE** refund-domain "input building" to a new
   `backend/modules/refunds/inputs.py` as **module-level functions**
   (NO class). These are domain-aware (they know about
   `refund_to == "original_method" | "store_credit"`) but they take and
   return only the small set of primitives the controller already has;
   they call the business-agnostic helpers in `utils/shopify_refunds.py`
   to fill in the branch-specific kwargs. Full code in § 5.d.

4. **REWRITE** the call paths to invoke
   `shopify_client.run(schema.<resource>.<mutations|queries>.<name>, **kwargs)`
   directly:
   - `backend/modules/refunds/controllers/refunds_controller.py` —
     `POST /refunds/create` (full body in § 5.d).
   - `backend/modules/orders/controllers/orders_controller.py` —
     `DELETE /orders/{order_id}` (full body in § 5.f).
   - `backend/modules/refunds/services/estimate_service.py` —
     replace `self.shopify_refund_service.fetch_order_for_refund(...)`
     with the equivalent inline `client.run(schema.orders.queries.by_name, ...)`
     / `client.run(schema.orders.queries.by_id, ...)` calls. The
     estimate service grows a `shopify_client: ShopifyClient | None = None`
     constructor argument (defaulting to `None` and lazy-initializing
     from env on first use) replacing the old
     `shopify_refund_service: ShopifyRefundService | None = None`
     argument. The `shopify_refund_service` property goes away;
     `_safe_get(_safe_get(...))` order-shape access is unchanged.

5. **UPDATE** every import of `ShopifyRefundService` /
   `ShopifyUserError` across the codebase. The sub-agent runs:

   ```bash
   grep -rn "ShopifyRefundService\|from modules.refunds.services.shopify_refund_service" backend/
   ```

   and rewrites each hit. Expected hits (Stage 3's diff plus Stage 5's
   own pending wiring, all owned by Stage 5 to update):
   - `backend/main.py` — exception handler import → `from utils.shopify_refunds import ShopifyUserError`.
   - `backend/modules/refunds/services/estimate_service.py` — see step 4.
   - any test stubs added by Stage 3 — update to instantiate
     `ShopifyClient` directly (or the test fake).

6. **VERIFY** zero references remain after the rewrite:

   ```bash
   ! grep -rn "ShopifyRefundService" backend/
   ! grep -rn "shopify_refund_service" backend/
   ! test -f backend/modules/refunds/services/shopify_refund_service.py
   ```

7. **VERIFY** every Shopify mutation call goes through
   `client.run(schema.x.y.z, **kwargs)` directly (D31 is preserved at
   the call-site level — the wrapper layer is gone but the canonical
   pattern stays):

   ```bash
   # The only places that import `schema` are call sites and tests.
   # No wrapper class re-exports `schema.x.y.z`.
   grep -rn "schema.refunds.mutations.create\|schema.orders.mutations.cancel\|schema.orders.queries.by_id\|schema.orders.queries.by_name" backend/modules/ backend/utils/
   ```

   Expected matches: the controllers (`refunds_controller.py`,
   `orders_controller.py`), the estimate service
   (`estimate_service.py`), and tests. NO matches in
   `backend/modules/refunds/services/` (the directory's only remaining
   file is `estimate_service.py`, which calls `client.run` directly
   for order lookups).

### 5.k.1 — Inline `get_estimate_service()` and audit for any other one-liner factory wrappers (Stage 2 cleanup)

Per the user's directive: every one-line factory wrapper must be
inlined. The orchestrator's grep across `backend/modules/refunds/`,
`backend/modules/orders/`, and `backend/utils/` confirmed there is
exactly ONE such wrapper today:

```bash
grep -rn "^def get_\w*\s*\(\) -> " backend/modules/refunds/ backend/modules/orders/ backend/utils/
```

→ `backend/modules/refunds/controllers/refunds_controller.py:25`

```python
def get_estimate_service() -> EstimateService:
    return EstimateService()


@router.post("/validate")
async def validate_refund(
    body: RefundRequest,
    estimate: EstimateService = Depends(get_estimate_service),
) -> dict:
    ...
```

Change to inline the dependency the same way Stage 5's controller wires
the canonical Shopify client:

```python
@router.post("/validate")
async def validate_refund(
    body: RefundRequest,
    estimate: EstimateService = Depends(EstimateService),
) -> dict:
    ...
```

`Depends(EstimateService)` works because — after § 5.k.0 lands —
`EstimateService.__init__(self, shopify_client: ShopifyClient | None = None)`
takes no required arguments (FastAPI calls it with no args by default
and the constructor lazy-builds a `ShopifyClient` from env on first
use). DELETE the `get_estimate_service()` function entirely.

Stage 5 does NOT add `get_shopify_refund_service()` — that factory was
on the original Stage 5 design but R2 deleted the
`ShopifyRefundService` class outright, so the factory has nothing to
wrap. The controllers use `Depends(ShopifyClient)` directly (§ 5.d, § 5.f).

**Re-grep after the inline edit** to confirm no factories remain in
scope:

```bash
! grep -rn "^def get_\w*\s*\(\) -> " backend/modules/refunds/ backend/modules/orders/ backend/utils/
```

Pre-existing factories at `backend/routers/admin.py:get_admin_controller`,
`backend/routers/admin.py:get_google_controller`,
`backend/routers/slack_api.py:get_slack_controller`, and
`backend/lib/clients/shopify_client/shopify_url_builder.py:get_shopify_store_id`
are out of scope (they belong to other modules / the deprecated
underscore client). The Stage 5 sub-agent does NOT inline them.

### 5.k.2 — Update `RESTOCK_OPTIONS` (Stage 1 cleanup)

In `slack-apps/registrations/views/refund/approve_modal.ts`, the current
constant is:

```typescript
export const RESTOCK_OPTIONS = [
  { label: "None", value: "none" },
  { label: "Full restock", value: "full" },
  { label: "To waitlist", value: "waitlist" },
  { label: "Admin hold", value: "admin_hold" },
  { label: "Do not restock", value: "no_restock" },
] as const;
```

Replace with the new lane set:

```typescript
export const RESTOCK_OPTIONS = [
  { label: "Veteran lane", value: "veteran" },
  { label: "Early lane", value: "early" },
  { label: "General lane", value: "general" },
  { label: "Waitlist", value: "waitlist" },
] as const;
```

DROP `"none"`, `"full"`, `"admin_hold"`, `"no_restock"` outright. The
default behavior when the operator doesn't intend to restock: don't
pre-select any option (no default). The picker renders empty.

### 5.k.3 — `extractApproveModalValues` returns `restock: RestockAction | undefined`

The current `ApproveModalValues` interface declares
`restock: RestockAction` and the extractor defaults to `"none"`. Change
to:

```typescript
export interface ApproveModalValues {
  action: ApproveAction;
  amount: number | null;
  restock: RestockAction | undefined;   // was: RestockAction (defaulted to "none")
  sendNotification: boolean;
}

export function extractApproveModalValues(
  stateValues: Record<string, Record<string, StateCell>>,
): ApproveModalValues {
  // ...
  const restock = stateValues[RESTOCK_BLOCK_ID]?.[RESTOCK_ACTION_ID]
    ?.selected_option?.value as RestockAction | undefined;
  // ...
  return { action, amount, restock, sendNotification: ... };
}
```

The Slack handler passes `restock` only when it is not `undefined`. On
the wire body sent to `POST /refunds/create`, `restockTo` is OMITTED
when `restock === undefined` — the field never arrives at the backend
with a `"none"` literal, because that literal no longer exists.

### 5.k.4 — Move wire-shape types out of `domain/refund/api.ts` (delete the file)

The user's directive: "api related signature logic should NOT be in the
refund domain. it should ONLY be called via a domain-agnostic api
layer."

Concretely:

1. **MOVE** the following types from
   `slack-apps/registrations/domain/refund/api.ts` to
   `slack-apps/registrations/domain/refund/types.ts`:
   - `ValidateRefundRequest`
   - `RefundRequestEval`
   - `RefundEvalOrder`
   - `RefundEvalProduct`
   - `RefundEvalEstimate`
   - `TierEstimate`
   - `CreateRefundRequest`
   - `CreateRefundResponse`
   - `CancelOutcome`
   - `RefundOutcome`
   - `RefundRestockTo`
   - `ShopifyUserError`

2. **UPDATE `RefundRestockTo`** to drop `"full"`. Final shape:

   ```typescript
   export type RefundRestockTo = "veteran" | "early" | "general" | "waitlist";
   ```

3. **DELETE** `slack-apps/registrations/domain/refund/api.ts` entirely.
   The typed wrappers `validateRefund(client, body)` and
   `executeRefund(client, body)` are GONE — they were one-line wrappers
   around `client.post<...>({ endpoint, body })` and earned no
   abstraction value. Refund-specific call sites construct the request
   body and call the generic `BarsApiClient` directly:

   ```typescript
   // BEFORE — Stage 1's typed wrapper
   import { validateRefund } from "../domain/refund/api.ts";
   const response = await validateRefund(client, body);

   // AFTER — direct generic-client call
   import type {
     ValidateRefundRequest,
     RefundRequestEval,
   } from "../domain/refund/types.ts";
   const body: ValidateRefundRequest = {
     /* ... */
   };
   const response = await client.post<RefundRequestEval>({
     endpoint: "/refunds/validate",
     body,
   });
   ```

   The HTTP wrapper (`clients/bars_api/client.ts`) is the ONLY API layer.

4. **UPDATE** `slack-apps/registrations/functions/send_request_for_eval.ts`
   to import `ValidateRefundRequest` / `RefundRequestEval` /
   `CreateRefundRequest` / `CreateRefundResponse` from `types.ts` and
   call `client.post<...>(...)` directly. Drop any
   `from "../domain/refund/api.ts"` imports.

5. **MOVE the `normalizeRefundOrCredit(...)` helper into
   `sheet_loader.ts`.** Per the user's direction "API-related signature
   logic should NOT be in the refund domain", the typed wrappers
   `validateRefund(...)` / `executeRefund(...)` are deleted (covered by
   step 3 above). The OTHER export from `domain/refund/api.ts` —
   `normalizeRefundOrCredit(raw: string | null): RefundTo` — stays
   because it's pure domain logic (a string-normalization mapping),
   not HTTP. **Decision: put it in `sheet_loader.ts`** (where it's
   actually called — the loader hands the raw cell value to it before
   constructing a `RefundSheetEntry`). Co-locating the normalizer with
   its only consumer keeps the `domain/refund/` directory free of any
   "API wrapper" file post-Stage-5. Once the function moves out,
   `api.ts` is empty and can be deleted entirely:

   ```bash
   ! test -f slack-apps/registrations/domain/refund/api.ts
   ```

   Concrete callers of `normalizeRefundOrCredit` after the move:
   `sheet_loader.ts::parseRow(...)` (existing — was already calling it
   via `import { normalizeRefundOrCredit } from "./api.ts"`; updates
   to a same-module reference) and `functions/send_request_for_eval.ts`
   (which constructs the validate body and currently imports
   `normalizeRefundOrCredit` from `api.ts` — updates to import from
   `domain/refund/sheet_loader.ts`).

   Caller migration example:

   ```typescript
   // BEFORE
   const eval_ = await validateRefund(barsApi, body);

   // AFTER (caller-owned; no refund-domain HTTP wrapper)
   const eval_ = await barsApi.post<RefundRequestEval>({
     endpoint: "/refunds/validate",
     body,
   });
   ```

### 5.k.6 — Verify Pydantic-model casing in `models/refund_request.py`

Stage 2 introduced `RefundRequest` and `SheetRowRef` in
`backend/modules/refunds/models/refund_request.py`. Verify Python field
names are snake_case and aliases are camelCase:

- `RefundRequest`: `order_number` (alias `"orderNumber"`),
  `requested_refund_to` (alias `"requestedRefundTo"`), `requester_email`
  (alias `"requesterEmail"`), `requester_first_name` (alias
  `"requesterFirstName"`), `requester_last_name` (alias
  `"requesterLastName"`), `notes`, `transfer_request` (alias
  `"transferRequest"`), `sheet_row_ref` (alias `"sheetRowRef"`),
  `is_test` (alias `"isTest"`).
- `SheetRowRef`: `spreadsheet_id` (alias `"spreadsheetId"`), `tab_id`
  (alias `"tabId"`), `row_number` (alias `"rowNumber"`).
- `model_config = {"populate_by_name": True}` on both.

Action if any field uses camelCase Python names: rename to snake_case
and add aliases. Action if already correct: check the box and move on.

### 5.k.7 — Sub-stage ordering inside § 5.k

Run § 5.k.1 → 5.k.7 in order. The Slack-side TypeScript changes
(5.k.2 / 5.k.3 / 5.k.4) can run in parallel with the Python-side
changes (5.k.1 / 5.k.5 / 5.k.6) because they touch disjoint code paths,
but each sub-stage is sequential within its own track. Verify each
sub-stage by running the relevant build/lint command before continuing:

```bash
# After Python-side work
uv run ruff check backend/modules/refunds/

# After TS-side work
deno check slack-apps/registrations/
deno lint slack-apps/registrations/
```

### 5.k.8 — Search/destroy other `get_<x>_service()` one-liners

Beyond § 5.k.1's targeted inlining of `get_estimate_service()`, run a
broad sweep for any other one-line factory wrappers in scope:

```bash
grep -rn "def get_\\w\\+_service() -> " backend/
```

For each hit IN SCOPE (under `backend/modules/refunds/`,
`backend/modules/orders/`, or `backend/utils/`), inline `Depends(<class>)`
and delete the factory. For each hit OUT OF SCOPE
(`backend/routers/admin.py`, `backend/routers/slack_api.py`, etc.), the
Stage 5 sub-agent does NOT touch the factory — it belongs to a
different module / spec. Pre-existing factories at:

- `backend/routers/admin.py:get_admin_controller`
- `backend/routers/admin.py:get_google_controller`
- `backend/routers/slack_api.py:get_slack_controller`
- `backend/lib/clients/shopify_client/shopify_url_builder.py:get_shopify_store_id`

are explicitly out of scope.

### 5.k.9 — Verify casing for Stage 5's NEW files only

> **Stage 6 owns the FULL retroactive Python-conventions cleanup
> across stages 1–5.** Stage 5 covers ONLY the new files Stage 5
> itself created (those introduced in § 5.b, § 5.c, § 5.f, and the
> new helper modules in § 5.k.0 / § 5.k.5). The retroactive sweep
> across stages 1–4 lives in Stage 6 § 6.g.

Run the user's deprecated-typing grep against ONLY the files Stage 5
created or directly modified:

```bash
grep -rn "List\\[\\|Dict\\[\\|Optional\\[\\|Tuple\\[\\|Union\\[\\|Set\\[" \
  backend/modules/refunds/models/create_request.py \
  backend/modules/refunds/models/create_response.py \
  backend/modules/refunds/inputs.py \
  backend/modules/orders/controllers/orders_controller.py \
  backend/utils/shopify_refunds.py
```

Expected: zero hits. (These are NEW files; they MUST start clean.)

The broader retroactive sweep across Stages 1–4 files (e.g.
`backend/utils/dates.py`, `backend/utils/money.py`,
`backend/utils/orders.py`, `backend/modules/refunds/models/estimate.py`,
`backend/modules/refunds/services/estimate_service.py`,
`backend/modules/refunds/models/refund_request.py`) is OWNED BY STAGE 6
§ 6.g — Stage 5's § 5.l also runs that sweep today as a defensive
double-check, but the canonical owner is Stage 6. If Stage 6 ships
before Stage 5's § 5.l would have caught a violation, the violation
is already gone; if Stage 5's § 5.l fires first, it lands the same
fix Stage 6 would have applied. The two are idempotent; running
both is safe.

### 5.k — Substage deliverables checklist

- [ ] `get_estimate_service()` factory deleted; controller uses
      `Depends(EstimateService)` inline. NO `get_shopify_refund_service()`
      / `get_shopify_client()` ever added — Stage 5's controllers use
      `Depends(ShopifyClient)` directly. Verifiable by
      `! grep -rn "^def get_\\w*\\s*\\(\\) -> " backend/modules/refunds/ backend/modules/orders/ backend/utils/`
      returning no matches.
- [ ] `RESTOCK_OPTIONS` is the canonical four-lane set
      (`"veteran"`, `"early"`, `"general"`, `"waitlist"`); the legacy
      `"none"` / `"admin_hold"` / `"no_restock"` literals are gone, and
      `"full"` is NOT a member of the lane enum (the field is omitted
      entirely when the operator picks no restock — see § 5.b's
      `restock_to` Pydantic literal). Verifiable by
      `! grep -nE '"full"|"none"|"admin_hold"|"no_restock"' slack-apps/registrations/views/refund/approve_modal.ts`
      returning no matches.
- [ ] `ApproveModalValues.restock` is `RestockAction | undefined`; the
      Slack handler omits `restockTo` from the wire body when
      `undefined`.
- [ ] `domain/refund/api.ts` is DELETED. Verifiable:
      `! test -f slack-apps/registrations/domain/refund/api.ts`.
- [ ] `domain/refund/types.ts` exports the relocated wire types
      (`ValidateRefundRequest`, `RefundRequestEval`, `RefundEvalOrder`,
      `RefundEvalProduct`, `RefundEvalEstimate`, `TierEstimate`,
      `CreateRefundRequest`, `CreateRefundResponse`, `CancelOutcome`,
      `RefundOutcome`, `RefundRestockTo`, `ShopifyUserError`).
      `RefundRestockTo` is the four-lane string-union.
- [ ] `functions/send_request_for_eval.ts` calls `client.post<...>(...)`
      directly with no `from "../domain/refund/api.ts"` import remaining.
- [ ] All TypedDicts that mirror the wire shape (in
      `models/estimate.py` and `models/create_response.py`) declare
      camelCase keys directly per § 5.b.1. Verifiable by
      `grep -rn "^class.*TypedDict" backend/modules/refunds/models/`
      producing classes whose fields are camelCase strings.
- [ ] `RefundRequest` / `SheetRowRef` use snake_case Python names with
      camelCase aliases and `model_config = {"populate_by_name": True}`
      (audit).
- [ ] `uv run ruff check backend/modules/refunds/` passes.
- [ ] `deno check slack-apps/registrations/` passes.
- [ ] `deno lint slack-apps/registrations/` passes.

---

## 5.l — Python conventions sweep across stages 1–5

> **Runs after § 5.k and before § 5.b–§ 5.j.** This substage is the
> retroactive Python-conventions cleanup the user requested:
> "no `List`, no `Dict`, only lowercase. no `from __future__ import
annotations`. others that have been deprecated by python3.14 must
> not be present in my python files in the final version."
>
> Stages 1–4 already landed several files that violate the convention.
> Stage 5 owns the cleanup so the new code (§ 5.b–§ 5.j) is added on
> top of a clean baseline rather than perpetuating the legacy typing
> style.

### Decision D33 — Python 3.14+ conventions

> **D33 — Python 3.14+ conventions: no `from __future__ import
annotations`, no `Optional[X]` (use `X | None`), no `Union[X, Y]`
> (use `X | Y`), no uppercase `List` / `Dict` / `Tuple` / `Set` /
> `FrozenSet` / `Type` (use lowercase `list` / `dict` / `tuple` /
> `set` / `frozenset` / `type`). Applies to all files in stages 1–7.
> Pre-existing legacy code under `backend/utils/dict_utils/`,
> `backend/utils/date_utils/`, `backend/legacy/`, and the deprecated
> `backend/lib/clients/shopify_client/` directory is out of scope.**
>
> The remaining `from typing import …` imports keep symbols that are
> still standard at 3.14+: `Literal`, `TypedDict`, `Protocol`, `Self`,
> `TypeAlias`, `Annotated`, `Any`, `Callable`, `ClassVar`, `Final`,
> `NewType`, `NoReturn`, `cast`, `overload`. The deprecated
> `Optional` / `List` / `Dict` / `Tuple` / `Set` / `FrozenSet` / `Type`
> / `Union` symbols must NOT appear in any new or migrated file.

D33 is owned by this design (Stage 5).

### Files in scope (audit list from orchestrator's grep)

The orchestrator ran these scans across the new backend code (Stages
1–5 in scope; legacy code out of scope):

```bash
grep -rn "^from __future__ import annotations" backend/modules/ backend/utils/ backend/main.py backend/routes.py
grep -rn "Optional\[\|Union\[\|List\[\|Dict\[\|Tuple\[\|Set\[\|FrozenSet\[\|Type\[" backend/modules/ backend/utils/ backend/main.py backend/routes.py
```

The hits to fix (NOT under `backend/legacy/` /
`backend/utils/dict_utils/` / `backend/utils/date_utils/` /
`backend/lib/clients/shopify_client/`):

| File                                                                     | What to change                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/utils/dates.py`                                                 | DELETE `from __future__ import annotations`. Already uses lowercase `list[date]` so no other rewrites needed.                                                                                                                                                                                  |
| `backend/utils/money.py`                                                 | DELETE `from __future__ import annotations`.                                                                                                                                                                                                                                                   |
| `backend/utils/orders.py`                                                | DELETE `from __future__ import annotations`.                                                                                                                                                                                                                                                   |
| `backend/modules/refunds/refund_calculator.py`                           | DELETE `from __future__ import annotations`. Verify no `Optional` / `List` / `Dict` left.                                                                                                                                                                                                      |
| `backend/modules/refunds/models/refund_request.py`                       | DELETE `from __future__ import annotations`. Replace `Optional[str]` / `Optional[SheetRowRef]` with `str \| None` / `SheetRowRef \| None`. Drop `Optional` from the `typing` import.                                                                                                           |
| `backend/modules/refunds/models/estimate.py`                             | DELETE `from __future__ import annotations`. Replace every `Optional[X]` with `X \| None` and every `List[X]` with `list[X]`. Drop `List`, `Optional` from the `typing` import (keep `Literal`, `TypedDict`).                                                                                  |
| `backend/modules/refunds/services/estimate_service.py`                   | DELETE `from __future__ import annotations`. Replace every `Optional[X]` / `List[X]` / `Tuple[Optional[str], ...]` with `X \| None` / `list[X]` / `tuple[str \| None, ...]`. Drop `List`, `Optional` from the `typing` import (keep `Any`, `Literal`, `TYPE_CHECKING`).                        |
| `backend/modules/refunds/controllers/refunds_controller.py`              | Audit only — file already imports nothing from `typing` that violates D33; verify no `Optional` / `List` slipped in via § 5.k.1's edits.                                                                                                                                                       |
| Stage 3 files (`shopify_refund_service.py` and `tests/`)                 | `shopify_refund_service.py` is DELETED in § 5.k.0 so its `Optional[ShopifyClient]` / `Optional[list[dict]]` / `Optional[str]` / `Optional[ShopifyOrder]` violations exit with the file. Any test stubs that referenced it are rewritten by § 5.k.0 step 5 to use the new module-level helpers. |
| `backend/main.py`                                                        | Audit only — Stage 3 added the `ShopifyUserError` exception handler. Verify the handler signature uses lowercase `list[dict]` / `dict[str, Any]` (not `List[Dict[str, Any]]`); replace `Optional[X]` with `X \| None` if found.                                                                |
| `backend/routes.py`                                                      | Audit only — Stage 2 wired the refunds router. Verify no D33 violations in the file's import block or function signatures.                                                                                                                                                                     |
| `backend/modules/orders/services/orders_service.py`                      | Audit — Stage 2 migration touched it. Replace any `Optional[X]` / `List[X]` / `Dict[K, V]` / `Union[X, Y]` per D33; drop the legacy `typing` import members.                                                                                                                                   |
| `backend/modules/refunds/inputs.py` (NEW in § 5.k.0)                     | NEW file — must comply with D33 from creation: `dict[str, Any]`, `list[dict]`, `Decimal`, `Literal[...]`, `X \| None`.                                                                                                                                                                         |
| `backend/utils/shopify_refunds.py` (NEW in § 5.k.0)                      | NEW file — must comply with D33 from creation.                                                                                                                                                                                                                                                 |
| `backend/modules/refunds/models/create_request.py` (NEW in § 5.b)        | NEW file — must comply with D33 from creation: `Literal[...] \| None`, `float \| None`, etc.                                                                                                                                                                                                   |
| `backend/modules/refunds/models/create_response.py` (NEW in § 5.c)       | NEW file — must comply with D33 from creation.                                                                                                                                                                                                                                                 |
| `backend/modules/orders/controllers/orders_controller.py` (NEW in § 5.f) | NEW file — must comply with D33 from creation.                                                                                                                                                                                                                                                 |

### Out-of-scope files (DO NOT TOUCH)

The orchestrator's grep flagged plenty of `from __future__ import
annotations` / `Optional[...]` hits under these directories. They are
**explicitly out of scope** for D33 and must NOT be touched by Stage 5:

- `backend/legacy/**` — pre-existing legacy code.
- `backend/utils/dict_utils/**` — pre-existing legacy utilities.
- `backend/utils/date_utils/**` — pre-existing legacy utilities.
- `backend/utils/datetime/**` — pre-existing legacy utilities.
- `backend/lib/clients/shopify_client/**` — deprecated underscore
  client (D10).
- `backend/modules/integrations/slack/client/**` — out of refund-cancel
  spec scope.
- `backend/services/refunds/**` — pre-existing legacy services
  (separate from `backend/modules/refunds/services/**`).
- `backend/routers/**` (NOT `backend/routes.py`) — pre-existing legacy
  routers (`admin.py`, `slack_api.py`).

### Verification commands

```bash
# No __future__ annotations in scope.
! grep -rn "^from __future__ import annotations" \
    backend/modules/refunds/ \
    backend/modules/orders/services/orders_service.py \
    backend/modules/orders/controllers/ \
    backend/utils/dates.py \
    backend/utils/money.py \
    backend/utils/orders.py \
    backend/utils/shopify_refunds.py \
    backend/main.py \
    backend/routes.py

# No deprecated typing forms in scope.
! grep -rnE "(Optional|Union|List|Dict|Tuple|Set|FrozenSet|Type)\[" \
    backend/modules/refunds/ \
    backend/modules/orders/services/orders_service.py \
    backend/modules/orders/controllers/ \
    backend/utils/dates.py \
    backend/utils/money.py \
    backend/utils/orders.py \
    backend/utils/shopify_refunds.py \
    backend/main.py \
    backend/routes.py

# `from typing import …` lines in scope contain only the kept symbols.
grep -rn "^from typing import" \
    backend/modules/refunds/ \
    backend/modules/orders/services/orders_service.py \
    backend/modules/orders/controllers/ \
    backend/utils/dates.py \
    backend/utils/money.py \
    backend/utils/orders.py \
    backend/utils/shopify_refunds.py \
    backend/main.py \
    backend/routes.py
# Manually review each line: only Literal / TypedDict / Protocol / Self /
# TypeAlias / Annotated / Any / Callable / ClassVar / Final / NewType /
# NoReturn / cast / overload may appear.

# `uv run ruff check` passes (the project's ruff config flags UP006 and
# UP007 which together cover the lowercase-typing + X|None enforcement).
uv run ruff check backend/modules/refunds/ backend/modules/orders/ backend/utils/ backend/main.py backend/routes.py
```

### § 5.l deliverables checklist

- [ ] All in-scope files have `from __future__ import annotations`
      removed. Verifiable by the first grep above returning no matches.
- [ ] All in-scope files use lowercase / `X | None` typing forms.
      Verifiable by the second grep returning no matches.
- [ ] `from typing import …` lines in scope keep only the kept symbols
      (`Literal`, `TypedDict`, `Any`, `Callable`, etc.); `Optional`,
      `List`, `Dict`, `Tuple`, `Set`, `FrozenSet`, `Type`, `Union` are
      gone. Verifiable by the third grep + manual review.
- [ ] `uv run ruff check backend/modules/refunds/ backend/modules/orders/ backend/utils/ backend/main.py backend/routes.py`
      passes.

---

## 5.m — Stage 1 deferred backend wire-up (validate POST + approval modal push)

> **Runs after § 5.l and before § 5.b–§ 5.j.** Stage 1 deferred the
> actual `validateRefund(barsApi, body)` POST + approval-modal push to
> "Stage 1b". Stage 5 absorbs that wire-up here so the Slack-side flow
> is end-to-end functional once `POST /refunds/create` lands.

### Files touched

- `slack-apps/registrations/functions/send_request_for_eval.ts` — the
  picker-modal submission handler. Currently posts a placeholder "row
  picked" follow-up message; this substage replaces that with the
  actual validate-and-render flow.

### Behavior changes

`functions/send_request_for_eval.ts` on picker submit performs:

1. **Construct the BARS API client.** Use the env-driven factory
   `makeBarsApiClient(env)` from
   `slack-apps/registrations/clients/bars_api/client.ts` (the generic,
   refund-agnostic HTTP wrapper introduced in Stage 1). The factory
   reads `BARS_API_URL` / auth env vars.

2. **POST to `/refunds/validate`.** The body is a `ValidateRefundRequest`
   shaped from the picked sheet row (post-§ 5.k.4 the type lives at
   `slack-apps/registrations/domain/refund/types.ts`). Concrete call:

   ```typescript
   import type {
     ValidateRefundRequest,
     RefundRequestEval,
   } from "../domain/refund/types.ts";

   const validateBody: ValidateRefundRequest = {
     orderNumber: row.orderNumber,
     requestedRefundTo: normalizeRefundTo(row.refundOrCredit),
     requesterEmail: row.email,
     requesterFirstName: row.firstName,
     requesterLastName: row.lastName,
     notes: row.notes,
     transferRequest: row.transferRequest,
     sheetRowRef: { spreadsheetId, tabId, rowNumber: row.rowNumber },
     isTest: env.IS_TEST === "true",
   };

   const eval_ = await barsApi.post<RefundRequestEval>({
     endpoint: "/refunds/validate",
     body: validateBody,
   });
   ```

   The wire JSON is camelCase per § 5.b.1; `RefundRequestEval`
   declares the camelCase TS interface.

3. **Push the approval modal pre-filled from the validate response.**
   The existing `views/refund/approve_modal.ts` thin caller (post-§ 5.k.2
   four-lane `RESTOCK_OPTIONS`) reads fields off `eval_` and produces
   the modal blocks. Concrete call:

   ```typescript
   import { buildApproveModal } from "../views/refund/approve_modal.ts";

   await client.views.push({
     trigger_id: pickerSubmission.trigger_id,
     view: buildApproveModal({
       eval: eval_,
       privateMetadata: JSON.stringify({
         orderId: eval_.order.id,
         productId: eval_.product.id,
         sheetRowRef: validateBody.sheetRowRef,
       }),
     }),
   });
   ```

   The "row picked" follow-up message becomes the actual review card
   built from the validate response (the existing
   `views/refund/eval_blocks.ts` builders consume `eval_` directly).

4. **On approval submit (separate handler).** When the operator
   approves the modal, the approval-submit handler (existing in the
   app's interactivity router; this substage keeps the wiring) builds
   a `CreateRefundRequest` and POSTs `/refunds/create`:

   ```typescript
   import type {
     CreateRefundRequest,
     CreateRefundResponse,
   } from "../domain/refund/types.ts";

   const meta = JSON.parse(view.private_metadata) as {
     orderId: string;
     productId: string;
     sheetRowRef: SheetRowRef;
   };
   const values = extractApproveModalValues(view.state.values);

   const createBody: CreateRefundRequest = {
     orderId: meta.orderId,
     productId: meta.productId,
     refundTo: row.refundTo,
     amount: values.amount,
     cancel:
       values.action === "cancel" || values.action === "cancel_and_refund",
     refund:
       values.action === "refund" || values.action === "cancel_and_refund",
     restockTo: values.restock, // undefined when no restock intended
     notify: values.sendNotification,
     approvedBy: body.user.id,
     isTest: env.IS_TEST === "true",
   };

   const createResp = await barsApi.post<CreateRefundResponse>({
     endpoint: "/refunds/create",
     body: createBody,
   });
   ```

5. **Update the message** with the result. The existing message-update
   helper renders `createResp.cancel` / `createResp.refund` /
   `createResp.errors` into the final confirmation card.

### Boundary properties

- The Slack handler talks JSON over HTTP — no shared schema file with
  the backend; the type-level contract is duplicated across
  `domain/refund/types.ts` (TS) and `models/create_request.py` /
  `models/estimate.py` / `models/create_response.py` (Python).
- Wire JSON is camelCase end-to-end per § 5.b.1 — the Python
  TypedDicts mirroring the wire shape declare camelCase keys directly,
  so the dict the backend builds IS the wire JSON. Pydantic's aliases
  on incoming bodies do the camel→snake flip on the way in.
- `restockTo` is omitted from the create body when the operator did
  not select a restock lane (post-§ 5.k.3
  `ApproveModalValues.restock: RestockAction | undefined`). The
  backend's Pydantic model has `restock_to: Literal[...] | None = None`,
  so the absent field is handled transparently.

### § 5.m deliverables checklist

- [ ] `functions/send_request_for_eval.ts` constructs `barsApi` via
      `makeBarsApiClient(env)` and POSTs `/refunds/validate` on picker
      submit. Verifiable by
      `grep -n 'barsApi.post<RefundRequestEval>' slack-apps/registrations/functions/send_request_for_eval.ts`
      returning one match.
- [ ] Approval modal is pushed from the validate response via
      `client.views.push(...)`. Verifiable by
      `grep -n 'views.push' slack-apps/registrations/functions/send_request_for_eval.ts`
      returning one match.
- [ ] The approval-submit handler POSTs `/refunds/create` and updates
      the message. Verifiable by
      `grep -rn 'barsApi.post<CreateRefundResponse>' slack-apps/registrations/`
      returning one match.
- [ ] No imports remain from the deleted `domain/refund/api.ts`
      (already covered by § 5.k.4 deliverable).
- [ ] `deno check slack-apps/registrations/` passes.
- [ ] `deno lint slack-apps/registrations/` passes.

---

## 5.h — Stage 5 deliverables checklist

- [ ] **§ 5.k retroactive cleanup of Stages 1–3 is COMPLETE** (all
      sub-checks in § 5.k passing) — gates every other Stage 5
      deliverable below.
- [ ] **§ 5.k.0 — `ShopifyRefundService` is DELETED.** Verifiable by
      `! test -f backend/modules/refunds/services/shopify_refund_service.py`
      and
      `! grep -rn "ShopifyRefundService\|shopify_refund_service" backend/`
      returning no matches.
- [ ] `backend/utils/shopify_refunds.py` exists and exposes
      `ShopifyUserError`, `parent_capture_txn`,
      `build_refund_transactions_for_shopify`,
      `build_store_credit_refund_methods` as module-level symbols
      (NO class). Verifiable by
      `grep -n "^class ShopifyUserError\|^def parent_capture_txn\|^def build_refund_transactions_for_shopify\|^def build_store_credit_refund_methods" backend/utils/shopify_refunds.py`
      returning four matches.
- [ ] `backend/modules/refunds/inputs.py` exists and exposes
      `build_cancel_kwargs` and `build_refund_kwargs` as module-level
      functions (NO class). Verifiable by
      `! grep -n "^class " backend/modules/refunds/inputs.py`
      returning no matches.
- [ ] **§ 5.l Python conventions sweep is COMPLETE** (all sub-checks
      in § 5.l passing) — D33 enforced across stages 1–5 in-scope
      files (`from __future__ import annotations` removed, lowercase
      typing forms, `X | None` instead of `Optional[X]`).
- [ ] **§ 5.m Stage 1 deferred backend wire-up is COMPLETE** (all
      sub-checks in § 5.m passing) — Slack handler issues real
      `/refunds/validate` and `/refunds/create` POSTs; approval modal
      is pushed from the validate response.
- [ ] `backend/modules/refunds/models/create_request.py` —
      `CreateRefundRequest` Pydantic v2 model per § 5.b. Class docstring
      enumerates all field-requirement deltas vs. the prior shape.
- [ ] `backend/modules/refunds/models/create_response.py` —
      `CreateRefundResponse` / `CancelOutcome` / `RefundOutcome` TypedDicts
      per § 5.c (NO Pydantic `BaseModel` — D28). Keys are camelCase
      strings declared directly per § 5.b.1; the dict the controller
      returns IS the wire JSON.
- [ ] All TypedDicts that mirror the wire shape (in
      `models/estimate.py` and `models/create_response.py`) declare
      camelCase keys directly. Verifiable by
      `grep -rn "^class.*TypedDict" backend/modules/refunds/models/`
      producing classes whose fields are camelCase strings.
- [ ] `backend/modules/refunds/controllers/refunds_controller.py` —
      extended with `POST /refunds/create` per § 5.d. Controller's
      `response_model` is `dict` (or omitted). The controller calls
      `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
      and `shopify_client.run(schema.refunds.mutations.create, **refund_kwargs)`
      directly. Verifiable by
      `grep -n "shopify_client.run(schema" backend/modules/refunds/controllers/refunds_controller.py`
      returning two matches (cancel + refund) plus the
      `schema.orders.queries.by_id` re-fetch when `refund_to == "original_method"`.
- [ ] `backend/modules/orders/controllers/orders_controller.py` — NEW.
      `DELETE /orders/{order_id}` plus a stubbed `CancelOrderRequest`
      Pydantic body. The route calls
      `shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)`
      directly (no service-class wrapper). Mounted via
      `router.include_router(orders_router)` in `backend/routes.py`
      per § 5.f.
- [ ] `backend/routes.py` — inline `orders = APIRouter(...)` block
      (lines 50-77 currently) replaced with
      `from modules.orders.controllers.orders_controller import router as orders_router` + `router.include_router(orders_router)`.
- [ ] **NO `ExecuteService` exists** (D30). Verifiable by
      `! find backend/modules/refunds -name 'execute_service.py'`
      returning no results.
- [ ] **NO orchestrator-method wrappers exist** anywhere in the new
      backend code (user directive: "no overloaded methods / no
      `cancel_order` + `create_refund` wrapper"). Verifiable by
      `! grep -rn "def cancel_and_refund\|def execute_refund\|def create_refund_with_cancel" backend/modules/ backend/utils/`
      returning no matches.
- [ ] **No combined `cancel-and-refund` wrapper exists** in
      `ShopifyRefundService` or anywhere else. Verifiable by
      `! grep -rn "def.*cancel.*refund\|def.*refund.*cancel" backend/modules/`
      returning no matches.
- [ ] **No method overloading** — Python doesn't natively support it,
      but the design must not document multiple signatures for the
      same name. A single `cancel_order` (or its post-§ 5.k.0 successor
      `build_cancel_kwargs`) plus a single `create_refund` (or its
      successor `build_refund_kwargs`) is the rule. Verifiable by
      inspection of `backend/modules/refunds/inputs.py`: each function
      name appears at most once with a single signature.
- [ ] All Shopify mutations in the new code path go through
      `client.run(schema.<resource>.<mutations|queries>.<name>, **kwargs)`
      directly (D31 — pattern preserved at the call site, no wrapper
      class). Verifiable by
      `grep -rn "schema.refunds.mutations.create\|schema.orders.mutations.cancel" backend/modules/ backend/utils/`
      returning matches only inside controllers and tests; NO matches
      inside `backend/modules/refunds/services/`.
- [ ] `restock_to` mapping documented per § 5.e; the cancel mutation
      receives only the `restock` boolean. Q7 added to design.md's
      Open Questions section in this design refactor pass (R8).
- [ ] `Decimal` is used for the refund `amount` passed to Shopify (not
      `float`). The `Decimal(str(body.amount))` round-trip avoids
      float→string truncation. Verifiable by
      `grep -n "Decimal(str(body.amount))" backend/modules/refunds/controllers/refunds_controller.py`
      returning one match.
- [ ] Stage 1's `slack-apps/registrations/domain/refund/action_requests.ts`
      updated to point at `POST /refunds/create` when `BARS_API_URL` is
      set; Lambda path stays as fallback (covered by § 5.m).
- [ ] `uv run python -c "import backend.modules.refunds.controllers.refunds_controller"`
      succeeds (smoke import).
- [ ] `uv run python -c "import backend.modules.orders.controllers.orders_controller"`
      succeeds (smoke import).
- [ ] `uv run python -c "from backend.utils.shopify_refunds import ShopifyUserError, parent_capture_txn, build_refund_transactions_for_shopify, build_store_credit_refund_methods"`
      succeeds (smoke import).
- [ ] `uv run python -c "from backend.modules.refunds.inputs import build_cancel_kwargs, build_refund_kwargs"`
      succeeds (smoke import).
- [ ] `uv run ruff check backend/modules/refunds/ backend/modules/orders/ backend/utils/ backend/main.py backend/routes.py`
      passes.

---

## 5.i — Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `backend/modules/refunds/tests/test_create_request_model.py`
- `backend/modules/refunds/tests/test_refunds_controller_create.py`
- `backend/modules/refunds/tests/test_inputs.py` (for the new
  `inputs.py` module-level functions — `build_cancel_kwargs`,
  `build_refund_kwargs`)
- `backend/modules/orders/tests/test_orders_controller_cancel.py`
- `backend/utils/tests/test_shopify_refunds.py` (for the
  module-level helpers `parent_capture_txn`,
  `build_refund_transactions_for_shopify`,
  `build_store_credit_refund_methods` — covers cancel + refund happy
  paths, store-credit branch, missing parent transaction,
  `ShopifyUserError` raises; supersedes Stage 3's planned
  `test_shopify_refund_service.py` since the service class is gone)

---

## 5.j — Cross-references

- **Depends on:** Stage 3 only as historical context — Stage 5 deletes
  Stage 3's `ShopifyRefundService` class outright (§ 5.k.0). The
  business-agnostic helpers (`parent_capture_txn`,
  `build_refund_transactions_for_shopify`,
  `build_store_credit_refund_methods`) move to
  `backend/utils/shopify_refunds.py`; the call sites become direct
  `shopify_client.run(...)` invocations from the controllers. Stage 3
  registers the `ShopifyUserError` handler in `backend/main.py`;
  Stage 5 does not need to re-register it (Stage 5 only updates the
  one-line import path because the exception class moves to
  `utils/shopify_refunds.py`).
- **Can run in parallel with:** Stage 4 — once the wire contract for
  `RefundRequestEval` is fixed (Stage 2), Stage 4 (Slack-side review-card
  refactor) and Stage 5 (cancel + refund execution) proceed independently.
- **Blocks:** Stage 6 (the final response shape — what Slack renders after
  approval — consumes Stage 5's outputs verbatim).

---

## 5.todo — Orchestrator TODOs (apply to design.md when accumulating)

These items are sub-agent feedback for the orchestrator; they affect
`design.md` (decisions log + open questions section) and are out of
scope for the Stage 5 implementation sub-agent itself.

1. **Casing convention lives in § 5.b.1.** Python files use snake_case
   identifiers everywhere. TS files use camelCase everywhere.
   TypedDicts that mirror the wire shape declare camelCase keys
   directly at construction time (the dict the backend builds IS the
   wire JSON — no boundary helper). Pydantic incoming bodies use
   snake_case Python field names with camelCase aliases. The
   orchestrator does NOT re-export this to design.md — § 5.b.1 is
   the canonical statement and applies across all stages.

2. **Q7 deferred — DO NOT BLOCK Stage 5 on it.** The user accepted the
   `restockTo` lane semantics earlier; Q7 only flags that the inventory-
   restock consumer (the thing that interprets the lane string) is
   future work tracked by a follow-up spec. Stage 5 already documents
   the boolean → lane mapping table in § 5.e and is complete without
   Q7's resolution. The orchestrator adds Q7 to design.md's Open
   Questions section in this design refactor pass — see R8 — confirming
   it is deferred to the inventory-restock follow-up spec.

3. **Q6 store-credit parity-port location.** § 5.k.0 lifts the
   store-credit logic into the module-level
   `build_store_credit_refund_methods(amount, currency)` in
   `backend/utils/shopify_refunds.py`. The parity-port from
   `aws/lambda/functions/ShopifyRefundHandler/handler.py` lives there.
   No design.md change required.
