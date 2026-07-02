Status: drop (superseded by codegen)
Path: backend/lib/clients/shopify_client_old/models/gql_models.py

Hand-written pydantic overlays that predate ariadne-codegen. Every class here
has a codegen equivalent (or a call-site substitute).

Envelopes (drop — codegen returns typed results directly, no envelope):
- `SuccessResponse`, `ListResponse`
- `OrderResponse`, `OrderListResponse`
- `ProductResponse`, `ProductListResponse`
- `CustomerResponse`, `CustomerListResponse`

Domain models (drop — codegen fragments own these):
- `LineItemModel`, `CustomerModel`, `VariantModel`, `AddressModel`

Local enums (drop — codegen `enums.py` owns these):
- `OrderCancelReason`, `RefundType`, `DiscountType`, `OrderStatus`, `ProductStatus`

Request bodies (drop — codegen `input_types.py` owns these; the old classes
are pydantic wrappers around the same shape):
- `OrderCancelRequest`, `OrderRefundRequest`, `OrderDiscountRequest`
- `ProductUpdateRequest`, `CustomerUpdateRequest`

Filter params (keep as call-site convenience OR drop and let call sites pass
raw dicts — decide with the caller migration):
- `OrderFilterParams`, `ProductFilterParams`, `CustomerFilterParams`
