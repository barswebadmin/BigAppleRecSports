# Deletion queue

Workbench for the consolidation. Nothing gets deleted until every caller row
below is `update` or `delete` (never `wait`).

## Legend

**Tiers**:
- **A — pure duplicates** (byte-identical to a survivor). Cheap to delete.
- **B — superseded** (functionally replaced by codegen ops or the DSL client).
- **C — dead code** (`__pycache__`, orphaned `copy.py` files, empty stubs).
- **D — relocate first, then delete** (move-outs: webhook models, theme templates, scripts).

**Caller disposition**:
- `update` — rewrite to point at the survivor.
- `delete` — retire the caller entirely.
- `wait` — not yet inspected; blocks the deletion.

---

## ✅ Executed (2026-07-01)

- **A1** — `lib/clients/shopify_client-legacy/` deleted (37 files, byte-identical to `backend_shopify_client_old/` minus one net-new `models/responses.py`; zero repo-wide callers).
- **A2** — 3 shell/curl files deleted from `backend/lib/clients/shopify_client_old/` (`aws_add_inventory_to_variant.sh`, `aws_move-inv.sh`, `shopify-requests.curl`). Byte-identical to copies in `lib/clients/shopify-client/`; zero callers by filename.
- **C2** — `lib/clients/shopify-client-py/` deleted (empty stub; zero real callers, 7 dead deprecation-shim references in `backend/modules/integrations/shopify/**/client/shopify_client.py` pointing at a phantom module — flagged as separate Tier C cleanup).

---

## 🎯 Ready to execute (Phase 3, once Phase 2 drains any remaining unique logic)

### `backend/lib/clients/shopify_client_old/` — wholesale delete

Every GQL surface has a `superseded` tracker entry pointing at the new op. `shopify_url_builder.py` was preserved as `backend/src/clients/shopify/urls.py`. What remains in the source dir is either duplicated in `new/`, superseded by codegen, or out-of-scope (webhook models, theme template models, scripts, sgqlc schemas).

**Blockers**:
- Webhook payload models (`models/webhooks/order_create.py`, `models/webhooks/product_update.py`, `models/base.py:WebhookBase`) — decide relocation home (`backend/src/webhooks/shopify/`) or drop.
- Business scripts (`populate_league_metaobjects.py`, `export_products_to_csv.py`, `create_league_metaobject_definition.py`, `get_orders_by_contact.py`, `get_product_with_orders.py`, `populate_missing_player_info.py`) — decide relocation to `backend/scripts/shopify/` or retire.
- Legacy monolith clients (`client.py`, `client_backup.py`, `shopify_client copy.py`) — none of these should survive; confirm no runtime imports.
- Filter param models (`models/requests.py`, filter classes in `models/gql_models.py`) — decide whether they're still useful as call-site convenience.

Once resolved: `git rm -r backend/lib/clients/shopify_client_old`.

### `lib/clients/shopify-client/` — wholesale delete

Python content already at `backend/src/clients/shopify/`:
- `shop_client.py` → duplicated
- `2026-07.graphql.pickle` → duplicated
- `add_tag_to_customers.py` → variant exists in target; needs merge decision

Also has: `_get_product_details.py` (smoke test), `pyproject.toml` (deps already in `backend/pyproject.toml`), 3 shell scripts + curl (already deleted from `backend_shopify_client_old`).

Once the DSL merge + `add_tag_to_customers.py` decision land: `rm -rf lib/clients/shopify-client`.

**Downstream break** — `aws/lambda/layers/lib/shopify-client` was a symlink into this dir. User is retiring most Lambdas; ignore.

---

## Tier B — superseded (all tracked in individual tracker files)

Every legacy GQL op has a `structure/{queries,mutations}/backend_shopify_client_old/*.md` entry with `Status: superseded (2026-07-01)` and a pointer to its new-op replacement. Full list of what's been ported:

| Legacy op | New op |
|---|---|
| `GetCustomer` | `GetCustomer` (direct-id form, uses `Customer` fragment) |
| `SearchCustomerByEmail` | `FindCustomers(query: "email:...")` |
| `SearchCustomersByEmails` | `FindCustomers(query: "email:a OR email:b")` |
| `UpdateCustomerTags` | `CustomerUpdate(input: {id, tags})` |
| `GetOrdersByProduct` | `FindOrders(query: "product_id:...")` |
| `searchOrders` (inline) | `FindOrders(query: ...)` |
| `GetAllOrdersForExport` | Deferred — Phase 2 script dir (specialty CSV report op) |
| `GetProduct` | `GetProduct` + `Product` fragment |
| `UpdateProduct` | `ProductUpdate(product: ProductUpdateInput)` (non-deprecated arg name) |
| `BulkUpdateVariantPrices` | `ProductVariantsBulkUpdate` |
| `GetVariant` | `GetVariant` + `ProductVariant` fragment |
| `GetInventoryInfo` | `GetVariant` (folded into same op via `ProductVariant` fragment) |
| `AdjustInventory` | `InventoryAdjustQuantities` |
| `GetMediaImageUrl` | `GetMediaImage` |
| `FileUpdateProductRef` | `FileUpdate` |
| `AttachProductMedia` | `FileCreate` + `FileUpdate` (two-step; legacy `productCreateMedia` is deprecated) |
| `DeleteProductMedia` | `FileUpdate(referencesToRemove:)` or `FileDelete` (legacy `productDeleteMedia` is deprecated) |
| `metaobjectDefinitionCreate` (inline) | `MetaobjectDefinitionCreate` |
| `metaobjectDefinitionByType` (inline) | `MetaobjectDefinitionByType` |
| `metaobjects` (inline) | `FindMetaobjects` |
| `metaobjectCreate` (inline) | `MetaobjectCreate` |
| `productUpdate_metafields` (inline) | Fold into `ProductUpdate` — pass `metafields` in `ProductUpdateInput` |

---

## Tier C — dead code (deferred cleanup)

### C1 — `backend/lib/clients/shopify_client_old/shopify_client copy.py`

Filename contains a literal space (`shopify_client copy.py`). Not importable by conventional means. Distinct hash from `client.py` and `client_backup.py` — three diverged copies of the same legacy client. Delete along with the parent dir in Phase 3.

### Dead deprecation shims (follow-up)

Discovered during A1 caller grep — `backend/modules/integrations/shopify/{client,shopify/client}/shopify_client.py` have deprecation docstrings pointing at `lib.clients.shopify-client-py.client.ShopifyClient`, a module that never existed. Dead code. Task spawned earlier to clean up. Not on this tracker.

---

## Tier D — relocate first, then delete original

### D1 — Webhook payload models

**Source**: `backend/lib/clients/shopify_client_old/models/{base.py, webhooks/order_create.py, webhooks/product_update.py, webhooks/__init__.py}`

**Destination**: TBD — likely `backend/src/webhooks/shopify/` (out of shopify-admin-client scope).

Classes: `WebhookBase`, `MoneySet`, `PriceSet`, `Address`, `CustomerAddress`, `Customer`, `ClientDetails`, `NoteAttribute`, `LineItemProperty`, `AttributedStaff`, `LineItem`, `ShippingLine`, `OrderCreateWebhook`, `OrderLineItemResult`, `OrderCreateResult`, `process_order_create`, `ProductVariant` (webhook flavor — different from GQL), `ProductOption`, `WebhookProductImage`, `MediaPreviewImage`, `ProductMedia`, `VariantGid`, `ProductCategory`, `ProductUpdateWebhook`, `ProductUpdateResult`, `process_product_update`.

### D2 — Theme template models

**Source**: `backend/lib/clients/shopify_client_old/models/theme_template_models.py`

**Destination**: TBD — `backend/src/clients/shopify_theme/` or a theme editor module (not admin GQL).

Classes: `FontWeight`, `FontStyle`, `FontConfig`, `PaddingConfig`, `BlockSettings`, `Block`, `SectionSettings`, `Section`, `ThemeTemplate`.

### D3 — Data samples / dumps

**Source (all under `backend/lib/clients/shopify_client_old/`)**:
- `shopify_orders_for_7590021333086.csv`, `shopify_orders_for_provided_email.csv` — one-off order exports
- `webhook_payloads.json` — webhook payload samples that seeded the models above
- `shopify_schema.json` (~9 MB), `shopify_schema_filtered.json` (~8 MB) — raw introspection dumps for sgqlc (superseded by `backend/src/clients/shopify/schema.graphql` SDL + `2026-07.graphql.pickle` parsed schema)

**Destination**: `backend/scripts/samples/` (for the CSVs + webhook JSON) or outright delete (the sgqlc schemas are truly obsolete).

### D4 — Legacy sgqlc schema modules (drop)

**Source**: `backend/lib/clients/shopify_client_old/shopify_schema.py`, `shopify_schema_filtered.py` (sgqlc-typed).

Superseded by ariadne codegen + the pickled schema. Drop, do not relocate.

### D5 — Business scripts

**Source (all under `backend/lib/clients/shopify_client_old/`)**:
- `populate_league_metaobjects.py`
- `populate_missing_player_info.py`
- `create_league_metaobject_definition.py`
- `export_products_to_csv.py`
- `get_orders_by_contact.py`
- `get_product_with_orders.py`
- `product_image.py` (`ProductImage` helper — resolves tags → media IDs)

**Destination**: `backend/scripts/shopify/` (or drop if no longer needed). Switch to using the new codegen `ShopifyClient`; drop inline GQL strings (replaced by the metaobject ops we just ported).

`product_image.py` may want a domain module (`backend/src/domain/…`) if it's imported by runtime code.

### D6 — Legacy monolith clients (drop)

- `backend/lib/clients/shopify_client_old/client.py`, `client_backup.py`, `shopify_client copy.py` — legacy `GqlQuery`-based clients. Superseded by codegen `ShopifyClient` + DSL wrapper. Drop.

---

## How this list grows

- Every time we finalize the disposition of a source file, its tracker file
  gets a `Status: superseded / migrated / deleted` frontmatter and its entry
  here gets a `Callers` table (populated on-demand via grep).
- When every `Callers` row for an entry is `update` or `delete` (no `wait`),
  the entry moves to `## ✅ Executed` and we batch the deletion.
- External-caller `wait` rows (published Lambda layers, other repos) get
  split out and deferred until we confirm we can break them.
