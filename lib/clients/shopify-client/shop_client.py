"""Shopify Admin GraphQL client — schema registry above the client.

Architecture
────────────

    SCHEMA SIGNATURE (this file, above the client)
        │
        ├── Var / QueryOp / MutationOp / Resource     ← pure-data primitives,
        │                                               mutable (still iterating)
        │
        ├── products, customers, orders, …            ← Resource instances;
        │                                               queries / mutations are
        │                                               their attributes
        │
        └── schema = Box({...})                       ← single keyable registry
                                                        ────────────
                                                        schema.products.queries.by_id
                                                        schema["orders"]["mutations"]["cancel"]

    SHOPIFY CLIENT (transport + execution only)
        │
        └── ShopifyClient.run(op, **kwargs)
                │
                ├── stage 1: TYPES      — op.field/return_type/payload_type/connection_type
                │                         resolved against self.ds (DSLSchema from pickle)
                │
                ├── stage 2: FIELDS     — op.fields (or caller `returns=[...]`)
                │                         → build_selections(parent_type, paths)
                │
                └── stage 3: VARIABLES  — op.variables (dict[name, Var])
                                          → DSLVariableDefinitions (auto-typed by gql)
                                          → variable_values dict (split, NEVER inlined)

Variables are ALWAYS split from the document. The on-wire payload is:
    {"query": "mutation ($productId: ID!, $variants: [...!]!) { ... }",
     "variables": {"productId": "...", "variants": [...]}}
Never:
    {"query": "mutation { productVariantsBulkUpdate(productId: \"...\", ...) }"}

No I/O at import. The pickle loads on first ShopifyClient(...) construction.
"""

import hashlib
import json
import pickle
import random
import re
import time
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any, Callable

from box import Box
from gql import Client, GraphQLRequest
from gql.dsl import (
    DSLField,
    DSLMutation,
    DSLQuery,
    DSLSchema,
    DSLType,
    DSLVariableDefinitions,
    dsl_gql,
)
from gql.transport.exceptions import (
    TransportConnectionFailed,
    TransportError,
    TransportServerError,
)
from gql.transport.httpx import HTTPXTransport
from gql.utils import to_camel_case
from graphql import GraphQLSchema, get_named_type, print_ast
from graphql.language.ast import (
    ArgumentNode,
    DirectiveNode,
    NameNode,
    OperationDefinitionNode,
    OperationType,
    StringValueNode,
)

PICKLE_PATH = Path(__file__).parent / "2026-07.graphql.pickle"


def to_pascal(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(part.title() for part in snake.split("_"))


@dataclass(frozen=True)
class ResourceId:
    """All Shopify ID representations parsed from any input at once.

    Accepts: bare int or numeric string · ``gid://shopify/<Type>/<id>`` ·
    ``https://<store>/admin/<resource>/<id>[/...]``.
    Key into whichever form you need: ``.digits``, ``.gid``.
    """

    digits: str
    gid: str

    @classmethod
    def of(cls, resource_type: str, value: str | int) -> "ResourceId":
        if isinstance(value, int):
            d = str(value)
        else:
            s = value.strip()
            if s.startswith("gid://"):
                d = s.rstrip("/").split("/")[-1]
            elif s.startswith("http"):
                m = re.search(r"/[a-zA-Z_-]+/(\d+)", s)
                d = m.group(1) if m else s
            else:
                d = s
        return cls(digits=d, gid=f"gid://shopify/{to_pascal(resource_type)}/{d}")


def parse_pickle(path: Path) -> GraphQLSchema:
    with open(path, "rb") as f:
        return pickle.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Registry primitives — pure data, NOT frozen (still iterating).
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Var:
    """One variable declaration on a GraphQL operation.

    The variable name (the dict key in ``op.variables``) is snake_case; the
    client camelizes it for the wire (``product_id`` → ``$productId``).

    ``sdl_type`` is documentation only — gql infers the actual SDL type from
    the field signature in the loaded schema. It is used in validation error
    messages ("missing required arg 'id' (expected: ID!)").

    ``gid`` triggers top-level GID normalization: bare ``"123"`` →
    ``"gid://shopify/<Pascal(gid)>/123"``.

    ``nested_gid`` triggers per-list-item GID normalization for inputs shaped
    like ``[{"id": "...", "price": "..."}, ...]``: every dict in the list has
    its specified keys GID-normalized.
    """

    sdl_type: str = ""
    required: bool = True
    gid: str | None = None
    nested_gid: dict[str, str] = dc_field(default_factory=dict)

    def coerce(self, value: Any) -> Any:
        """Return *value* with Shopify GID normalization applied per this Var's spec."""
        if self.gid is not None:
            if isinstance(value, list):
                return [ResourceId.of(self.gid, v).gid for v in value]
            return ResourceId.of(self.gid, value).gid
        if self.nested_gid and isinstance(value, list):
            return [
                {
                    to_camel_case(k): (ResourceId.of(self.nested_gid[k], v).gid if k in self.nested_gid else v)
                    for k, v in item.items()
                }
                if isinstance(item, dict) else item
                for item in value
            ]
        return value


@dataclass
class QueryOp:
    """A query operation on a Resource.

    ``field``      — snake_case name; camelCased for the result key (``result.get(…)``).
    ``root``       — DSL accessor: ``lambda ds: ds.QueryRoot.product``.
    ``dsl_type``   — DSL type accessor: ``lambda ds: ds.Product``.
    ``connection`` — if set, the field returns a *Connection paginated via endCursor:
                     ``lambda ds: ds.CustomerConnection``.
    ``is_search``  — connection driven by a Shopify search string built from kwargs.
    ``fields``     — default return-field dot-paths; override with ``returns=[…]``.
    ``variables``  — snake_case name → Var (sdl_type + GID metadata).
    """

    field: str
    root: Callable[[DSLSchema], DSLField]
    dsl_type: Callable[[DSLSchema], DSLType]
    fields: list[str] = dc_field(default_factory=list)
    variables: dict[str, Var] = dc_field(default_factory=dict)
    connection: Callable[[DSLSchema], DSLType] | None = None
    is_search: bool = False

    def variable_values(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Validate required args, apply GID coercion, return camelCase wire dict."""
        missing = [f"{n} ({v.sdl_type})" for n, v in self.variables.items() if v.required and not kwargs.get(n)]
        if missing:
            raise ValueError(f"query {self.field}: missing required arg(s) {', '.join(missing)}")
        return {to_camel_case(n): v.coerce(kwargs[n]) for n, v in self.variables.items() if kwargs.get(n) is not None}

    def search_string(self, kwargs: dict[str, Any]) -> str:
        """Build a Shopify search string from caller kwargs (``email:foo AND …``)."""
        return " AND ".join(
            f"{to_camel_case(n)}:{ResourceId.of(v.gid, val).digits if v.gid else val}"
            for n, v in self.variables.items()
            if (val := kwargs.get(n)) is not None
        )

    def build(self, ds: DSLSchema, variable_values: dict[str, Any], selections: list[DSLField]) -> DSLQuery:
        """Wire variable_values into a DSLQuery using the declared root accessor."""
        var_defs = DSLVariableDefinitions()
        q = DSLQuery(
            self.root(ds).args(**{k: getattr(var_defs, k) for k in variable_values}).select(*selections)
        )
        q.variable_definitions = var_defs
        return q

    def build_page(self, ds: DSLSchema, page_values: dict[str, Any], node_selections: list[DSLField]) -> DSLQuery:
        """Build one page of a paginated connection query."""
        conn = self.connection(ds)  # type: ignore[misc]
        var_defs = DSLVariableDefinitions()
        q = DSLQuery(
            self.root(ds)
            .args(**{k: getattr(var_defs, k) for k in page_values})
            .select(
                conn.nodes.select(*node_selections),
                conn.pageInfo.select(ds.PageInfo.hasNextPage, ds.PageInfo.endCursor),
            )
        )
        q.variable_definitions = var_defs
        return q


@dataclass
class MutationOp:
    """A mutation operation on a Resource.

    ``field``        — snake_case name; camelCased for the result key.
    ``root``         — DSL accessor: ``lambda ds: ds.Mutation.productUpdate``.
    ``payload``      — DSL type accessor: ``lambda ds: ds.ProductUpdatePayload``.
    ``errors``       — selects the user-error field from the payload:
                       ``lambda ds, p: p.userErrors.select(ds.UserError.field, …)``.
    ``fields``       — return-field dot-paths on the payload.
    ``variables``    — snake_case kwarg → Var spec.
    ``wrap_into``    — if set, all variables fold into one GraphQL input variable;
                       ``wrap_into_type`` documents its SDL type.
    ``idempotent``   — attach ``@idempotent(key: …)`` directive automatically.
    """

    field: str
    root: Callable[[DSLSchema], DSLField]
    payload: Callable[[DSLSchema], DSLType]
    errors: Callable[[DSLSchema, DSLType], DSLField]
    fields: list[str] = dc_field(default_factory=list)
    variables: dict[str, Var] = dc_field(default_factory=dict)
    wrap_into: str | None = None
    wrap_into_type: str = ""
    idempotent: bool = False

    def variable_values(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Validate required args, apply GID coercion, wrap if needed, return wire dict."""
        missing = [f"{n} ({v.sdl_type})" for n, v in self.variables.items() if v.required and not kwargs.get(n)]
        if missing:
            raise ValueError(f"mutation {self.field}: missing required arg(s) {', '.join(missing)}")
        inner = {to_camel_case(n): v.coerce(kwargs[n]) for n, v in self.variables.items() if kwargs.get(n) is not None}
        return {to_camel_case(self.wrap_into): inner} if self.wrap_into else inner

    def build(
        self,
        ds: DSLSchema,
        variable_values: dict[str, Any],
        selections: list[DSLField],
        *,
        idempotency_key: str | None = None,
    ) -> GraphQLRequest:
        """Build the signed mutation request, attaching an idempotency directive when required."""
        var_defs = DSLVariableDefinitions()
        m = DSLMutation(
            self.root(ds).args(**{k: getattr(var_defs, k) for k in variable_values}).select(*selections)
        )
        m.variable_definitions = var_defs
        request = dsl_gql(m)
        if self.idempotent or idempotency_key:
            key_payload = {"op": self.field, "vars": variable_values}
            key = idempotency_key or hashlib.sha256(
                json.dumps(key_payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            key_arg = ArgumentNode(name=NameNode(value="key"), value=StringValueNode(value=key))
            directive = DirectiveNode(name=NameNode(value="idempotent"), arguments=(key_arg,))
            for defn in request.document.definitions:
                if isinstance(defn, OperationDefinitionNode) and defn.operation is OperationType.MUTATION:
                    for f in defn.selection_set.selections:
                        f.directives = (directive,)
        return request


@dataclass
class Resource:
    """The central concept. queries/mutations are its attributes.

    ``fields`` is the exhaustive list of returnable field names for this
    type — pass it as ``returns=schema.products.fields`` to get everything,
    or slice it to taste. ``queries`` and ``mutations`` are wrapped in
    ``Box`` so callers can use attribute *or* dict syntax:
    ``schema.products.queries.by_id`` ≡ ``schema["products"]["queries"]["by_id"]``.
    """

    type_name: str
    fields: list[str] = dc_field(default_factory=list)
    queries: dict[str, QueryOp] = dc_field(default_factory=dict)
    mutations: dict[str, MutationOp] = dc_field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.queries, Box):
            self.queries = Box(self.queries, default_box=False)
        if not isinstance(self.mutations, Box):
            self.mutations = Box(self.mutations, default_box=False)

    def __getitem__(self, key: str) -> Any:
        """Bracket access mirrors attribute access so callers can write either
        ``schema.orders.mutations.cancel`` or ``schema["orders"]["mutations"]["cancel"]``."""
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(key) from e


# ─────────────────────────────────────────────────────────────────────────────
# Resource definitions — pure data, no I/O. Schema registry is built below.
# ─────────────────────────────────────────────────────────────────────────────


products = Resource(
    type_name="product",
    fields=[
        "id", "title", "handle", "description_html",
        "product_type", "tags", "status", "created_at", "updated_at",
    ],
    queries={
        "by_id": QueryOp(
            field="product",
            root=lambda ds: ds.QueryRoot.product,
            dsl_type=lambda ds: ds.Product,
            fields=["id", "title", "handle", "status", "created_at", "updated_at"],
            variables={"id": Var(sdl_type="ID!", gid="product")},
        ),
    },
    mutations={
        "update": MutationOp(
            field="product_update",
            root=lambda ds: ds.Mutation.productUpdate,
            payload=lambda ds: ds.ProductUpdatePayload,
            errors=lambda ds, p: p.userErrors.select(ds.UserError.field, ds.UserError.message),
            fields=["product.id", "product.title", "product.handle", "product.status"],
            variables={
                "id": Var(sdl_type="ID!", gid="product"),
                "handle": Var(sdl_type="String", required=False),
                "title": Var(sdl_type="String", required=False),
                "description_html": Var(sdl_type="String", required=False),
                "product_type": Var(sdl_type="String", required=False),
                "tags": Var(sdl_type="[String!]", required=False),
                "status": Var(sdl_type="ProductStatus", required=False),
            },
            wrap_into="product",
            wrap_into_type="ProductInput!",
        ),
        "bulk_update_variants": MutationOp(
            field="product_variants_bulk_update",
            root=lambda ds: ds.Mutation.productVariantsBulkUpdate,
            payload=lambda ds: ds.ProductVariantsBulkUpdatePayload,
            errors=lambda ds, p: p.userErrors.select(
                ds.ProductVariantsBulkUpdateUserError.field,
                ds.ProductVariantsBulkUpdateUserError.message,
                ds.ProductVariantsBulkUpdateUserError.code,
            ),
            fields=[
                "product.id",
                "product_variants.id",
                "product_variants.title",
                "product_variants.price",
            ],
            variables={
                "product_id": Var(sdl_type="ID!", gid="product"),
                "variants": Var(
                    sdl_type="[ProductVariantsBulkInput!]!",
                    nested_gid={"id": "product_variant"},
                ),
            },
        ),
    },
)


variants = Resource(
    type_name="product_variant",
    fields=["id", "title", "sku", "price", "inventory_quantity"],
    queries={
        "by_id": QueryOp(
            field="product_variant",
            root=lambda ds: ds.QueryRoot.productVariant,
            dsl_type=lambda ds: ds.ProductVariant,
            fields=["id", "title", "sku", "price", "inventory_quantity"],
            variables={"id": Var(sdl_type="ID!", gid="product_variant")},
        ),
    },
)


customers = Resource(
    type_name="customer",
    fields=[
        "id", "email", "first_name", "last_name", "phone",
        "created_at", "updated_at", "number_of_orders",
        "note", "tags", "verified_email", "state",
    ],
    queries={
        "by_email": QueryOp(
            field="customers",
            root=lambda ds: ds.QueryRoot.customers,
            dsl_type=lambda ds: ds.Customer,
            connection=lambda ds: ds.CustomerConnection,
            is_search=True,
            fields=[
                "id", "email", "first_name", "last_name", "phone",
                "created_at", "updated_at", "number_of_orders",
                "note", "tags", "verified_email", "state",
            ],
            variables={"email": Var(sdl_type="String!")},
        ),
        "by_id": QueryOp(
            field="customer",
            root=lambda ds: ds.QueryRoot.customer,
            dsl_type=lambda ds: ds.Customer,
            fields=["id", "email", "first_name", "last_name", "phone", "tags"],
            variables={"id": Var(sdl_type="ID!", gid="customer")},
        ),
    },
    mutations={
        "update": MutationOp(
            field="customer_update",
            root=lambda ds: ds.Mutation.customerUpdate,
            payload=lambda ds: ds.CustomerUpdatePayload,
            errors=lambda ds, p: p.userErrors.select(ds.UserError.field, ds.UserError.message),
            fields=["customer.id", "customer.email"],
            variables={
                "id": Var(sdl_type="ID!", gid="customer"),
                "email": Var(sdl_type="String", required=False),
                "first_name": Var(sdl_type="String", required=False),
                "last_name": Var(sdl_type="String", required=False),
                "phone": Var(sdl_type="String", required=False),
                "note": Var(sdl_type="String", required=False),
                "tags": Var(sdl_type="[String!]", required=False),
            },
            wrap_into="input",
            wrap_into_type="CustomerInput!",
        ),
    },
)


_ORDER_MONEY_FIELDS = [
    "total_price_set.shop_money.amount",
    "total_price_set.shop_money.currency_code",
]

# Rich order selection — full detail for single-order fetches (UI display,
# cancellation eligibility, refund calculation). Consumed by orders.queries.by_id.
ORDER_DETAIL_FIELDS = [
    "id", "name", "email", "phone",
    "created_at", "updated_at", "cancelled_at", "cancel_reason",
    "display_financial_status", "display_fulfillment_status",
    "note", "tags",
    *_ORDER_MONEY_FIELDS,
    "subtotal_price_set.shop_money.amount",
    "total_tax_set.shop_money.amount",
    "total_discounts_set.shop_money.amount",
    "total_refunded_set.shop_money.amount",
    "custom_attributes.key", "custom_attributes.value",
    "customer.id", "customer.email",
    "customer.first_name", "customer.last_name", "customer.tags",
    "line_items.nodes.id",
    "line_items.nodes.title",
    "line_items.nodes.quantity",
    "line_items.nodes.custom_attributes.key",
    "line_items.nodes.custom_attributes.value",
    "line_items.nodes.variant.id",
    "line_items.nodes.variant.title",
    "line_items.nodes.product.id",
    "refunds.id",
    "refunds.note",
    "refunds.created_at",
    "refunds.total_refunded_set.shop_money.amount",
    "refunds.total_refunded_set.shop_money.currency_code",
]


orders = Resource(
    type_name="order",
    fields=[
        "id", "name", "email", "phone",
        "created_at", "updated_at", "cancelled_at", "cancel_reason",
        "display_financial_status", "display_fulfillment_status",
        "note", "tags",
        "total_price_set", "subtotal_price_set", "total_tax_set",
        "total_discounts_set", "total_refunded_set",
        "customer", "custom_attributes", "line_items", "refunds",
    ],
    queries={
        "by_id": QueryOp(
            field="order",
            root=lambda ds: ds.QueryRoot.order,
            dsl_type=lambda ds: ds.Order,
            fields=ORDER_DETAIL_FIELDS,
            variables={"id": Var(sdl_type="ID!", gid="order")},
        ),
        "by_email": QueryOp(
            field="orders",
            root=lambda ds: ds.QueryRoot.orders,
            dsl_type=lambda ds: ds.Order,
            connection=lambda ds: ds.OrderConnection,
            is_search=True,
            fields=[
                "id", "name", "email", "created_at", "updated_at",
                "display_financial_status", "display_fulfillment_status",
                "cancelled_at", "cancel_reason", "note", "tags",
                *_ORDER_MONEY_FIELDS,
                "subtotal_price_set.shop_money.amount",
                "total_tax_set.shop_money.amount",
                "total_discounts_set.shop_money.amount",
                "total_refunded_set.shop_money.amount",
            ],
            variables={"email": Var(sdl_type="String!")},
        ),
        "by_name": QueryOp(
            field="orders",
            root=lambda ds: ds.QueryRoot.orders,
            dsl_type=lambda ds: ds.Order,
            connection=lambda ds: ds.OrderConnection,
            is_search=True,
            fields=[
                "id", "name", "email", "created_at", "cancelled_at",
                "display_financial_status",
                *_ORDER_MONEY_FIELDS,
            ],
            variables={"name": Var(sdl_type="String!")},
        ),
        "by_product": QueryOp(
            field="orders",
            root=lambda ds: ds.QueryRoot.orders,
            dsl_type=lambda ds: ds.Order,
            connection=lambda ds: ds.OrderConnection,
            is_search=True,
            fields=[
                "id", "name", "created_at", "cancelled_at",
                *_ORDER_MONEY_FIELDS,
                "customer.id", "customer.email",
                "customer.first_name", "customer.last_name", "customer.tags",
                "custom_attributes.key", "custom_attributes.value",
                "line_items.nodes.id",
                "line_items.nodes.title",
                "line_items.nodes.quantity",
                "line_items.nodes.custom_attributes.key",
                "line_items.nodes.custom_attributes.value",
                "line_items.nodes.variant.id",
                "line_items.nodes.variant.title",
                "line_items.nodes.product.id",
            ],
            variables={"product_id": Var(sdl_type="ID!", gid="product")},
        ),
    },
    mutations={
        "cancel": MutationOp(
            field="order_cancel",
            root=lambda ds: ds.Mutation.orderCancel,
            payload=lambda ds: ds.OrderCancelPayload,
            errors=lambda ds, p: p.orderCancelUserErrors.select(
                ds.OrderCancelUserError.field,
                ds.OrderCancelUserError.message,
                ds.OrderCancelUserError.code,
            ),
            fields=["job.id", "job.done"],
            variables={
                "order_id": Var(sdl_type="ID!", gid="order"),
                "reason": Var(sdl_type="OrderCancelReason!"),
                "restock": Var(sdl_type="Boolean!"),
                "notify_customer": Var(sdl_type="Boolean", required=False),
                "staff_note": Var(sdl_type="String", required=False),
                "refund_method": Var(sdl_type="OrderCancelRefundMethodInput", required=False),
            },
        ),
    },
)


refunds = Resource(
    type_name="refund",
    fields=["id", "note", "created_at", "total_refunded_set"],
    mutations={
        "create": MutationOp(
            field="refund_create",
            root=lambda ds: ds.Mutation.refundCreate,
            payload=lambda ds: ds.RefundCreatePayload,
            errors=lambda ds, p: p.userErrors.select(ds.UserError.field, ds.UserError.message),
            fields=[
                "refund.id",
                "refund.note",
                "refund.created_at",
                "refund.total_refunded_set.presentment_money.amount",
                "refund.total_refunded_set.presentment_money.currency_code",
                "order.id",
                "order.name",
            ],
            variables={
                "order_id": Var(sdl_type="ID!", gid="order"),
                "currency": Var(sdl_type="CurrencyCode", required=False),
                "note": Var(sdl_type="String", required=False),
                "notify": Var(sdl_type="Boolean", required=False),
                "transactions": Var(sdl_type="[OrderTransactionInput!]", required=False),
                "refund_methods": Var(sdl_type="[RefundMethodInput!]", required=False),
                "refund_line_items": Var(sdl_type="[RefundLineItemInput!]", required=False),
                "shipping": Var(sdl_type="ShippingRefundInput", required=False),
            },
            wrap_into="input",
            wrap_into_type="RefundInput!",
            idempotent=True,
        ),
    },
)


# ─────────────────────────────────────────────────────────────────────────────
# The single keyable schema registry. Resource is the central concept.
# ─────────────────────────────────────────────────────────────────────────────
#
# Usage:
#     from shop_client import schema
#     schema.products.queries.by_id            → QueryOp
#     schema["orders"]["mutations"]["cancel"]  → MutationOp
#
# This is a Box (python-box dict subclass) — attribute *or* dict access,
# nested all the way down. Mutable; add/remove ops in tests freely.
schema = Box(
    {
        "products": products,
        "variants": variants,
        "customers": customers,
        "orders": orders,
        "refunds": refunds,
    },
    box_dots=False,
    default_box=False,
)


# ─────────────────────────────────────────────────────────────────────────────
# ShopifyClient — transport + execution. Owns the gql schema; the registry
# above describes WHAT to call, this class describes HOW.
# ─────────────────────────────────────────────────────────────────────────────


class ShopifyClient:
    schema_cache: GraphQLSchema | None = None

    @classmethod
    def load_schema(cls) -> GraphQLSchema:
        if cls.schema_cache is None:
            cls.schema_cache = parse_pickle(PICKLE_PATH)
        return cls.schema_cache

    def __init__(self, *, store_id: str, api_version: str, token: str):
        self.gql_schema = self.load_schema()
        self.ds = DSLSchema(self.gql_schema)
        transport = HTTPXTransport(
            url=f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json",
            headers={"X-Shopify-Access-Token": token},
        )
        self.gql_client = Client(schema=self.gql_schema, transport=transport)

    def build_selections(self, parent_type: DSLType, paths: list[str]) -> list[DSLField]:
        """Merge dot-paths sharing a parent into one DSL selection per parent.

        ``['refund.id', 'refund.note', 'order.id']`` →
        ``refund { id note } order { id }``
        """
        groups: dict[str, list[str]] = {}
        for path in paths:
            head, _, tail = path.partition(".")
            groups.setdefault(to_camel_case(head), []).append(tail)

        selections: list[DSLField] = []
        for head, tails in groups.items():
            dsl_field = getattr(parent_type, head)
            if get_named_type(dsl_field.field.type).name.endswith("Connection"):
                dsl_field = dsl_field.args(first=250)
            sub_paths = [t for t in tails if t]
            if sub_paths:
                nested_type = getattr(self.ds, get_named_type(dsl_field.field.type).name)
                dsl_field.select(*self.build_selections(nested_type, sub_paths))
            selections.append(dsl_field)
        return selections

    def execute(
        self,
        operation: GraphQLRequest,
        variable_values: dict[str, Any],
        *,
        dry_run: bool = False,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_cap: float = 8.0,
    ) -> dict[str, Any]:
        if dry_run:
            print("--- GraphQL operation ---")
            print(print_ast(operation.document))
            print("--- variables ---")
            print(json.dumps(variable_values, indent=2, default=str))
            return {}
        for attempt in range(max_retries + 1):
            try:
                with self.gql_client as session:
                    return session.execute(operation, variable_values=variable_values)
            except TransportError as e:
                transient = isinstance(e, TransportConnectionFailed) or (
                    isinstance(e, TransportServerError)
                    and (e.code is None or e.code in {408, 425, 429, 500, 502, 503, 504})
                )
                if attempt >= max_retries or not transient:
                    raise
                delay = min(backoff_cap, backoff_base * (2**attempt))
                time.sleep(delay + random.uniform(0, delay * 0.25))
        raise RuntimeError("unreachable")

    @staticmethod
    def boxify(data: Any) -> Any:
        """Wrap response dicts/lists in Box with camel→snake translation on access."""
        if data is None:
            return None
        if isinstance(data, list):
            return [ShopifyClient.boxify(item) for item in data]
        if isinstance(data, dict):
            return Box(data, camel_killer_box=True, default_box=False, box_recast=None)
        return data

    def run(
        self,
        op: QueryOp | MutationOp,
        *,
        returns: list[str] | None = None,
        dry_run: bool = False,
        page_size: int = 100,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a registry op.

        Returns (Box-wrapped, snake_case keys):
            QueryOp non-connection: resource Box (or None).
            QueryOp connection:     list[Box] of node Boxes (paginated).
            MutationOp:             payload Box (with ``.user_errors`` etc.).
        """
        if isinstance(op, MutationOp):
            variable_values = op.variable_values(kwargs)
            payload_type = op.payload(self.ds)
            selections = [*self.build_selections(payload_type, returns or op.fields), op.errors(self.ds, payload_type)]
            request = op.build(self.ds, variable_values, selections, idempotency_key=idempotency_key)
            result = self.execute(request, variable_values, dry_run=dry_run)
            return self.boxify(result.get(to_camel_case(op.field), {}) if result else {})

        if not isinstance(op, QueryOp):
            raise TypeError(f"unknown op type: {type(op).__name__}")

        selections = self.build_selections(op.dsl_type(self.ds), returns or op.fields)

        if op.connection is None:
            variable_values = op.variable_values(kwargs)
            result = self.execute(dsl_gql(op.build(self.ds, variable_values, selections)), variable_values, dry_run=dry_run)
            return self.boxify(result.get(to_camel_case(op.field)) if result else None)

        # Connection (paginated).
        # build_page() constructs a fresh DSLQuery each call — DSLField.args() mutates
        # ast_field.arguments in-place, so reusing a field across pages accumulates duplicates.
        base_values: dict[str, Any] = {"query": op.search_string(kwargs)} if op.is_search else op.variable_values(kwargs)
        all_nodes: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page_values = {**base_values, "first": page_size, **({"after": cursor} if cursor else {})}
            result = self.execute(dsl_gql(op.build_page(self.ds, page_values, selections)), page_values, dry_run=dry_run)
            if dry_run:
                return []
            page = result.get(to_camel_case(op.field), {}) or {}
            all_nodes.extend(page.get("nodes", []))
            page_info = page.get("pageInfo", {}) or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return self.boxify(all_nodes)


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo — dry-run a few ops. Reads env vars EXPLICITLY here, not in the
# library. Run: python shop_client.py
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    import dotenv

    dotenv.load_dotenv()
    client = ShopifyClient(
        store_id=os.environ["SHOPIFY__STORE_ID"],
        api_version=os.environ["SHOPIFY__API_VERSION"],
        token=os.environ["SHOPIFY__TOKEN__ADMIN"],
    )

    print("\n=== schema keys ===\n")
    print(list(schema.keys()))
    print("products ops:", "queries=", list(schema.products.queries), "mutations=", list(schema.products.mutations))

    print("\n=== run(schema.orders.mutations.cancel) dry_run ===\n")
    client.run(
        schema.orders.mutations.cancel,
        order_id="8888888888888",
        reason="CUSTOMER",
        restock=False,
        notify_customer=False,
        staff_note="Approved via Slack workflow",
        dry_run=True,
    )

    print("\n=== run(schema.refunds.mutations.create) dry_run (auto idempotency key) ===\n")
    client.run(
        schema.refunds.mutations.create,
        order_id="8888888888888",
        note="Refund approved via Slack workflow",
        notify=False,
        transactions=[
            {
                "order_id": "gid://shopify/Order/8888888888888",
                "parent_id": "gid://shopify/OrderTransaction/1111111111",
                "amount": "50.00",
                "kind": "REFUND",
                "gateway": "shopify_payments",
            }
        ],
        dry_run=True,
    )

    print("\n=== run(schema.products.mutations.bulk_update_variants) dry_run ===\n")
    client.run(
        schema.products.mutations.bulk_update_variants,
        product_id="7678746361950",
        variants=[
            {"id": "44444444444", "price": "9.99"},
            {"id": "44444444445", "price": "9.99"},
        ],
        dry_run=True,
    )

    print("\n=== run(schema.products.queries.by_id) dry_run ===\n")
    client.run(
        schema.products.queries.by_id,
        id="7678746361950",
        returns=["id", "title", "description_html"],
        dry_run=True,
    )
