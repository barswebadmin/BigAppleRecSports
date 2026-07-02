Status: mixed — Phase 2 executed 2026-07-01
Old dir: backend/lib/clients/shopify_client_old/ (now deleted wholesale)

## Migrated (moved to backend/scripts/shopify/)

- `create_league_metaobject_definition.py` → `backend/scripts/shopify/create_league_metaobject_definition.py`
- `populate_league_metaobjects.py` → `backend/scripts/shopify/populate_league_metaobjects.py`
- `populate_missing_player_info.py` → `backend/scripts/shopify/populate_missing_player_info.py`
- `export_products_to_csv.py` → `backend/scripts/shopify/export_products_to_csv.py`
- `get_orders_by_contact.py` → `backend/scripts/shopify/get_orders_by_contact.py`
- `get_product_with_orders.py` → `backend/scripts/shopify/get_product_with_orders.py`

## Migrated (moved to backend/src/domain/shopify/)

- `product_image.py` → `backend/src/domain/shopify/product_image.py` (`ProductImage` dataclass — tag → media_id lookup)

## Deleted with the source dir

- `client.py`, `client_backup.py`, `shopify_client copy.py` — legacy monolithic `GqlQuery`-based clients. Superseded by codegen `ShopifyClient` (`backend/src/clients/shopify/shopify_client.py`) + DSL wrapper (`shop_client.py`, pending merge).

## Follow-up work (per script)

All 6 relocated scripts still import from the deleted `lib.clients.shopify_client_old.*` paths. Two of them (`get_product_with_orders.py`, `get_orders_by_contact.py`) explicitly showed stale imports at Phase-2 execution time. Migration path per script: rewrite to use the new codegen `ShopifyClient` + the ported ops (`GetProduct`, `FindOrders`, `MetaobjectCreate`, etc.). User will migrate when getting to each.
