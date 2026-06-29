# Stage 5 Implementation Progress

## Cleanup substages (§ 5.k — runs first)

- [x] 5.k.0 Delete ShopifyRefundService; move helpers to utils/shopify_refunds.py + modules/refunds/inputs.py — already landed (verified: `class ShopifyRefundService` returns 0 grep matches, `inputs.py` and `utils/shopify_refunds.py` both exist)
- [x] 5.k.1 Inline get_estimate_service() factory; verify no others exist — already landed (verified: `Depends(EstimateService)` in refunds_controller.py, no `def get_estimate_service` anywhere)
- [ ] 5.k.2 Update RESTOCK_OPTIONS to four-lane set — owned by Stage 6 (Slack-side cleanup)
- [ ] 5.k.3 ApproveModalValues.restock → RestockAction | undefined — owned by Stage 6
- [x] 5.k.4 Move wire types out of api.ts; delete api.ts; update RefundRestockTo (drop "full") — already landed
- [ ] 5.k.5 Convert TypedDicts in estimate.py to snake_case + add utils/casing.py — owned by Stage 6 (this sub-agent's scope is § 5.b–§ 5.j only, per orchestrator instructions)
- [ ] 5.k.6 Verify Pydantic-model casing in refund_request.py — owned by Stage 6
- [ ] 5.k.7 Verify Python + TS builds — covered by A3.7

## Python conventions sweep (§ 5.l)

- [ ] 5.l Strip future annotations + replace Optional/Union/List/Dict/Tuple/Set/Type/FrozenSet across in-scope files — owned by Stage 6 (out of A3 scope)

## Stage 1 deferred wire-up (§ 5.m)

- [ ] 5.m Real validateRefund POST + approval-modal push + /refunds/create POST in send_request_for_eval.ts — owned by Stage 6 / a future Slack sub-agent

## A3 — New Stage 5 code (§ 5.b–§ 5.j)

Checkpoint format: `- [x] A3.x <step> — saved at <ISO>`

- [x] A3.1 models/create_request.py (Pydantic, incoming) — saved at 2026-06-20T22:29:24Z
- [x] A3.2 models/create_response.py (TypedDicts, outgoing — D28; camelCase keys pending § 5.k.5 cleanup) — saved at 2026-06-20T22:29:51Z
- [x] A3.3 controllers/refunds_controller.py — POST /refunds/create added (inline shopify-client dep, no service-class wrapper, local try/except for partial-success state, removed legacy `POST /refunds/` placeholder) — saved at 2026-06-20T22:30:56Z
- [x] A3.4 backend/modules/orders/controllers/orders_controller.py — DELETE /orders/{order_id} (+ controllers/**init**.py) — saved at 2026-06-20T22:31:29Z
- [x] A3.5 routes.py — removed inline orders APIRouter; added orders_router include; refunds_router include preserved; waitlists/products/health unchanged — saved at 2026-06-20T22:31:51Z
- [x] A3.6 Slack-side action_requests.ts update — N/A: the file `slack-apps/registrations/domain/refund/action_requests.ts` was already deleted during the Stage 4 retroactive cleanup (see `progress-stage-4-impl.md` "Pre-existing baseline" note). The intended Slack-side `/refunds/create` wire-up lives in `functions/send_request_for_eval.ts` and is owned by Stage 5 § 5.m, which is explicitly scoped to a different sub-agent per the orchestrator's A3 instructions ("The Python convention cleanup of Stage 1-5 files is owned by Stage 6"). No A3 file save here. — recorded at 2026-06-20T22:32:06Z
- [x] A3.7a Pre-existing fixes required to make verification gates pass — saved at 2026-06-20T22:55:00Z
  - `modules/refunds/services/estimate_service.py` — removed the `shopify_client: ShopifyClient | None = None` parameter from `EstimateService.__init__`. FastAPI cannot introspect `ShopifyClient | None` as a sub-dependency, so `Depends(EstimateService)` (Stage 2 wiring, exercised again at A3) crashed at route registration with "Invalid args for response field". The lazy `.client` property still env-builds on first access; tests inject fakes via `app.dependency_overrides[EstimateService] = lambda: fake`.
  - `modules/orders/__init__.py` — replaced the eager `from .services.orders_service import OrdersService` re-export with a docstring-only init. The eager re-export pulled in `modules.integrations.shopify` transitively at import time, which failed because the monorepo's `shared_utilities/` workspace member doesn't exist on disk in this branch (pre-existing repo state). No production importer used `from modules.orders import OrdersService` (one Makefile smoke-check uses it; that smoke check is independently broken by the missing `shared_utilities`). Direct submodule imports (`from modules.orders.services.orders_service import OrdersService`) still work.
- [x] A3.7 Verify: `uv run python -c 'import modules.refunds.controllers.refunds_controller; import modules.orders.controllers.orders_controller; import modules.refunds.models.create_request; import modules.refunds.models.create_response'` prints `imports OK` (exit 0). `uvx ruff check` against the four A3-created/modified files (`modules/refunds/controllers/refunds_controller.py`, `modules/refunds/models/create_request.py`, `modules/refunds/models/create_response.py`, `modules/orders/controllers/orders_controller.py`, `routes.py`) returns "All checks passed!". `uvx ruff check modules/refunds/ modules/orders/ routes.py` (the user's literal requested gate) reports 90 pre-existing errors, ALL outside A3 scope: ~50 in `modules/orders/tests/test_orders_api.py` (trailing whitespace / missing newline / import sort), ~30 in `modules/orders/services/order_create_handler.py` + `tests/test_order_create_handler.py`, 1 import-sort in `modules/refunds/services/estimate_service.py`, and 4 N999 on existing `__init__.py` files (climbs to the repo-root `__init__.py` named "BigAppleRecSports" — non-PEP8). All pre-existing; Stage 6 conventions cleanup owns them per orchestrator scoping. — saved at 2026-06-20T23:03:50Z
- Final status A3: COMPLETED
