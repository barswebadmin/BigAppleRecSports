"""Shopify Admin GraphQL client using gql DSL with pre-pickled schema."""

import hashlib
import json
import os
import pickle
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import dotenv
from autoregistry import Registry
from gql import Client, GraphQLRequest
from gql.dsl import DSLField, DSLMutation, DSLQuery, DSLSchema, DSLType, dsl_gql
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

dotenv.load_dotenv()

PICKLE_PATH = Path(__file__).parent / "2026-07.graphql.pickle"

_client: "ShopifyClient | None" = None


def get_client() -> "ShopifyClient":
    global _client
    if _client is None:
        _client = ShopifyClient()
    return _client


def parse_pickle(path: Path) -> GraphQLSchema:
    with open(path, "rb") as f:
        return pickle.load(f)


class ShopifyClient:
    schema_cache: GraphQLSchema | None = None

    @classmethod
    def load_schema(cls) -> GraphQLSchema:
        if cls.schema_cache is None:
            cls.schema_cache = parse_pickle(PICKLE_PATH)
        return cls.schema_cache

    def __init__(
        self,
        *,
        store_id: str = os.environ.get("SHOPIFY__STORE_ID"),
        api_version: str = os.environ.get("SHOPIFY__API_VERSION"),
        token: str = os.environ.get("SHOPIFY__TOKEN__ADMIN"),
    ):
        self.gql_schema = self.load_schema()
        self.dsl_schema = DSLSchema(self.gql_schema)
        transport = HTTPXTransport(
            url=f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json",
            headers={"X-Shopify-Access-Token": token},
        )
        self.gql_client = Client(schema=self.gql_schema, transport=transport)

    @staticmethod
    def to_camel(snake: str) -> str:
        return to_camel_case(snake)

    @staticmethod
    def to_pascal(snake: str) -> str:
        return "".join(part.title() for part in snake.split("_"))

    def normalize_gid(self, value: str, resource_name: str) -> str:
        value = str(value).strip()
        return value if value.startswith("gid://") else f"gid://shopify/{self.to_pascal(resource_name)}/{value}"

    def camelize_kwargs(self, kwargs: dict[str, Any], gid_fields: dict[str, str] | None = None) -> dict[str, Any]:
        gid_fields = gid_fields or {}

        def convert(value: Any) -> Any:
            if isinstance(value, dict):
                return {self.to_camel(k): convert(v) for k, v in value.items()}
            if isinstance(value, list):
                return [convert(item) for item in value]
            return value

        result = {}
        for k, v in kwargs.items():
            camel_k = self.to_camel(k)
            result[camel_k] = self.normalize_gid(v, gid_fields[k]) if k in gid_fields else convert(v)
        return result

    def to_type(self, type_name: str) -> DSLType:
        return getattr(self.dsl_schema, self.to_pascal(type_name))

    def to_query(self, query_name: str) -> DSLField:
        return getattr(self.dsl_schema.QueryRoot, self.to_camel(query_name))

    def to_mutation(self, mutation_name: str) -> DSLField:
        return getattr(self.dsl_schema.Mutation, self.to_camel(mutation_name))

    @staticmethod
    def bind_if_connection(dsl_field: DSLField, nested_first: int = 250) -> DSLField:
        if get_named_type(dsl_field.field.type).name.endswith("Connection"):
            return dsl_field.args(first=nested_first)
        return dsl_field

    def build_selections(self, parent_type: DSLType, paths: list[str]) -> list[DSLField]:
        """Merge dot-paths sharing a parent into one selection per parent.

        ['refund.id', 'refund.note', 'order.id'] → refund { id note } order { id }
        instead of refund { id } refund { note } order { id }. Same wire result
        post-server-merge, but cleaner AST and avoids printing duplicates.
        """
        groups: dict[str, list[str]] = {}
        for path in paths:
            head, _, tail = path.partition(".")
            groups.setdefault(self.to_camel(head), []).append(tail)

        selections: list[DSLField] = []
        for head, tails in groups.items():
            dsl_field = self.bind_if_connection(getattr(parent_type, head))
            sub_paths = [t for t in tails if t]
            if sub_paths:
                nested_type_name = get_named_type(dsl_field.field.type).name
                nested_type = getattr(self.dsl_schema, nested_type_name)
                dsl_field.select(*self.build_selections(nested_type, sub_paths))
            selections.append(dsl_field)
        return selections

    # HTTP statuses worth retrying. 408 timeout, 429 throttle, 5xx server.
    RETRYABLE_HTTP_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

    def is_transient(self, error: TransportError) -> bool:
        if isinstance(error, TransportConnectionFailed):
            return True
        if isinstance(error, TransportServerError):
            return error.code is None or error.code in self.RETRYABLE_HTTP_STATUS
        return False

    def run_op(
        self,
        operation: GraphQLRequest,
        variables: dict[str, Any],
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
            print(json.dumps(variables, indent=2, default=str))
            return {}
        for attempt in range(max_retries + 1):
            try:
                with self.gql_client as session:
                    return session.execute(operation, variable_values=variables)
            except TransportError as e:
                if attempt >= max_retries or not self.is_transient(e):
                    raise
                # Exponential backoff with jitter
                delay = min(backoff_cap, backoff_base * (2 ** attempt))
                time.sleep(delay + random.uniform(0, delay * 0.25))
        raise RuntimeError("unreachable")  # mypy/lint: loop always returns or raises

    @staticmethod
    def idempotency_key_from(mutation_name: str, variables: dict[str, Any]) -> str:
        """Deterministic SHA-256 of mutation + variables.

        Same logical call → same key → Shopify dedupes on retry. Callers that need
        two independent identical calls must pass an explicit idempotency_key.
        """
        payload = json.dumps(
            {"name": mutation_name, "vars": variables}, sort_keys=True, default=str
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def attach_idempotent_directive(request: GraphQLRequest, key: str) -> None:
        """Inject @idempotent(key: "...") onto the mutation's top-level field."""
        directive = DirectiveNode(
            name=NameNode(value="idempotent"),
            arguments=(
                ArgumentNode(
                    name=NameNode(value="key"),
                    value=StringValueNode(value=key),
                ),
            ),
        )
        for defn in request.document.definitions:
            if (
                isinstance(defn, OperationDefinitionNode)
                and defn.operation == OperationType.MUTATION
            ):
                for f in defn.selection_set.selections:
                    f.directives = (directive,)

    # FUTURE REFACTOR: split caller-facing `query` (search/lookup kwargs) from
    # GraphQL `variables` (the wire payload). Today we conflate the two by
    # inlining values via `field.args(**variables)`; switching to
    # `DSLVariableDefinitions` would emit a parameterized document + separate
    # variable_values JSON. Pairs with the same change in `mutate()` below.
    def query(
        self,
        query_name: str,
        type_name: str,
        query: dict[str, Any],
        return_fields: list[str],
        *,
        connection_name: str | None = None,
        page_size: int = 100,
        dry_run: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if connection_name:
            # Connection queries take a single `query: String!` arg with Shopify search syntax
            search_parts = [f"{k}:{v}" for k, v in query.items()]
            variables = {"query": " AND ".join(search_parts)} if search_parts else {}
        else:
            variables = self.camelize_kwargs(
                query, gid_fields={"id": type_name} if "id" in query else None
            )
        selections = self.build_selections(self.to_type(type_name), return_fields)
        query_field = self.to_query(query_name)

        if not connection_name:
            op = DSLQuery(query_field.args(**variables).select(*selections))
            return self.run_op(dsl_gql(op), variables, dry_run=dry_run)

        all_nodes = []
        cursor = None
        connection_type = self.to_type(connection_name)
        page_info_type = self.to_type("page_info")

        while True:
            page_vars = {**variables, "first": page_size}
            if cursor:
                page_vars["after"] = cursor

            op = DSLQuery(query_field.args(**page_vars).select(
                connection_type.nodes.select(*selections),
                connection_type.pageInfo.select(
                    page_info_type.hasNextPage,
                    page_info_type.endCursor,
                ),
            ))

            result = self.run_op(dsl_gql(op), page_vars, dry_run=dry_run)
            if dry_run:
                return []
            data = result.get(self.to_camel(query_name), {})

            all_nodes.extend(data.get("nodes", []))

            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

        return all_nodes

    # FUTURE REFACTOR: split caller-facing input (`kwargs` / camelized
    # `wire_kwargs`) from GraphQL `variables` so the document carries
    # `$input: SomeInput!` and we send `variable_values={"input": {...}}`
    # instead of inlining literals. Pairs with the same change in `query()`.
    def mutate(
        self,
        mutation_name: str,
        kwargs: dict[str, Any],
        return_fields: list[str],
        *,
        input_key: str | None,
        gid_fields: dict[str, str],
        error_path: str,
        error_type: str,
        error_fields: list[str],
        idempotent: bool = False,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        wire_kwargs = self.camelize_kwargs(kwargs, gid_fields=gid_fields)
        variables = {input_key: wire_kwargs} if input_key else wire_kwargs

        payload_type = self.to_type(f"{mutation_name}_payload")
        selections = self.build_selections(payload_type, return_fields)

        err_type = self.to_type(error_type)
        selections.append(
            getattr(payload_type, self.to_camel(error_path)).select(
                *[getattr(err_type, self.to_camel(f)) for f in error_fields]
            )
        )

        op = DSLMutation(self.to_mutation(mutation_name).args(**variables).select(*selections))
        request = dsl_gql(op)
        if idempotent or idempotency_key is not None:
            key = idempotency_key or self.idempotency_key_from(mutation_name, variables)
            self.attach_idempotent_directive(request, key)
        return self.run_op(request, variables, dry_run=dry_run)

    # TODO: migrate product_variants_bulk_update to declarative MutationOp once
    # gid_fields supports list-of-dict normalization (e.g. "variants[].id": "product_variant").
    def mutate_bulk_variants(
        self,
        product_id: str,
        variants: list[dict[str, Any]],
        return_fields: list[str],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        normalized_product_id = self.normalize_gid(product_id, "product")
        normalized_variants = [
            self.camelize_kwargs(v, gid_fields={"id": "product_variant"}) for v in variants
        ]
        variables = {"productId": normalized_product_id, "variants": normalized_variants}
        selections = self.build_selections(self.to_type("product_variant"), return_fields)
        mutation_field = self.to_mutation("product_variants_bulk_update")
        payload_type = self.to_type("product_variants_bulk_update_payload")
        error_type = self.to_type("product_variants_bulk_update_user_error")

        op = DSLMutation(mutation_field.args(**variables).select(
            payload_type.product.select(self.to_type("product").id),
            payload_type.productVariants.select(*selections),
            payload_type.userErrors.select(
                error_type.field,
                error_type.message,
                error_type.code,
            ),
        ))

        return self.run_op(dsl_gql(op), variables, dry_run=dry_run)


@dataclass
class QueryOp:
    name: str
    type_name: str
    required_args: list[str] = field(default_factory=list)
    optional_args: list[str] = field(default_factory=list)
    return_fields: list[str] = field(default_factory=list)
    connection: str | None = None

    def __call__(
        self,
        *,
        returns: list[str] | None = None,
        first: int = 100,
        dry_run: bool = False,
        **kwargs,
    ) -> Any:
        return get_client().query(
            query_name=self.name,
            type_name=self.type_name,
            query=kwargs,
            return_fields=returns or self.return_fields,
            connection_name=self.connection,
            page_size=first,
            dry_run=dry_run,
        )


@dataclass
class MutationOp:
    name: str
    input_key: str | None = None
    gid_fields: dict[str, str] = field(default_factory=dict)
    required_args: list[str] = field(default_factory=list)
    optional_args: list[str] = field(default_factory=list)
    return_fields: list[str] = field(default_factory=list)
    error_path: str = "user_errors"
    error_type: str = "user_error"
    error_fields: list[str] = field(default_factory=lambda: ["field", "message"])
    # When True, client attaches @idempotent(key: <sha256 of mutation+vars>) so
    # retries dedupe at Shopify. Set for mutations whose schema docs declare
    # idempotency support (refundCreate, inventoryAdjustQuantities, ...).
    idempotent: bool = False

    def __call__(
        self,
        *,
        returns: list[str] | None = None,
        dry_run: bool = False,
        idempotency_key: str | None = None,
        **kwargs,
    ) -> Any:
        return get_client().mutate(
            mutation_name=self.name,
            kwargs=kwargs,
            return_fields=returns or self.return_fields,
            input_key=self.input_key,
            gid_fields=self.gid_fields,
            error_path=self.error_path,
            error_type=self.error_type,
            error_fields=self.error_fields,
            idempotent=self.idempotent,
            idempotency_key=idempotency_key,
            dry_run=dry_run,
        )


customers = Registry()
customers["by_email"] = QueryOp(
    name="customers",
    type_name="customer",
    required_args=["email"],
    return_fields=[
        "id",
        "email",
        "first_name",
        "last_name",
        "phone",
        "created_at",
        "updated_at",
        "number_of_orders",
        "note",
        "tags",
        "verified_email",
        "state",
    ],
    connection="customer_connection",
)
customers["by_id"] = QueryOp(
    name="customer",
    type_name="customer",
    required_args=["id"],
    return_fields=["id", "email", "first_name", "last_name", "phone", "tags"],
)
customers["update"] = MutationOp(
    name="customer_update",
    input_key="input",
    gid_fields={"id": "customer"},
    required_args=["id"],
    optional_args=["email", "first_name", "last_name", "phone", "note", "tags"],
    return_fields=["customer.id", "customer.email"],
)

orders = Registry()
orders["cancel"] = MutationOp(
    name="order_cancel",
    gid_fields={"order_id": "order"},
    required_args=["order_id", "reason", "restock"],
    optional_args=["notify_customer", "staff_note", "refund_method"],
    return_fields=["job.id", "job.done"],
    error_path="order_cancel_user_errors",
    error_type="order_cancel_user_error",
    error_fields=["field", "message", "code"],
)
orders["by_email"] = QueryOp(
    name="orders",
    type_name="order",
    required_args=["email"],
    return_fields=[
        "id",
        "name",
        "email",
        "created_at",
        "updated_at",
        "display_financial_status",
        "display_fulfillment_status",
        "cancelled_at",
        "cancel_reason",
        "note",
        "tags",
        "total_price_set.shop_money.amount",
        "total_price_set.shop_money.currency_code",
        "subtotal_price_set.shop_money.amount",
        "total_tax_set.shop_money.amount",
        "total_discounts_set.shop_money.amount",
        "total_refunded_set.shop_money.amount",
    ],
    connection="order_connection",
)
orders["by_product"] = QueryOp(
    name="orders",
    type_name="order",
    required_args=["product_id"],
    return_fields=[
        "id",
        "name",
        "created_at",
        "cancelled_at",
        "total_price_set.shop_money.amount",
        "total_price_set.shop_money.currency_code",
        "customer.id",
        "customer.email",
        "customer.first_name",
        "customer.last_name",
        "customer.tags",
        "custom_attributes.key",
        "custom_attributes.value",
        "line_items.nodes.id",
        "line_items.nodes.title",
        "line_items.nodes.quantity",
        "line_items.nodes.custom_attributes.key",
        "line_items.nodes.custom_attributes.value",
        "line_items.nodes.variant.id",
        "line_items.nodes.variant.title",
        "line_items.nodes.product.id",
    ],
    connection="order_connection",
)

products = Registry()
products["by_id"] = QueryOp(
    name="product",
    type_name="product",
    required_args=["id"],
    return_fields=["id", "title", "handle", "status", "created_at", "updated_at"],
)
products["update"] = MutationOp(
    name="product_update",
    input_key="product",
    gid_fields={"id": "product"},
    optional_args=["id", "handle", "title", "description_html", "product_type", "tags", "status"],
    return_fields=["product.id", "product.title", "product.handle", "product.status"],
)

variants = Registry()
variants["by_id"] = QueryOp(
    name="product_variant",
    type_name="product_variant",
    required_args=["id"],
    return_fields=["id", "title", "sku", "price", "inventory_quantity"],
)

refunds = Registry()
refunds["create"] = MutationOp(
    name="refund_create",
    input_key="input",
    gid_fields={"order_id": "order"},
    required_args=["order_id"],
    optional_args=["currency", "note", "notify", "transactions", "refund_methods", "refund_line_items", "shipping"],
    return_fields=[
        "refund.id",
        "refund.note",
        "refund.created_at",
        "refund.total_refunded_set.presentment_money.amount",
        "refund.total_refunded_set.presentment_money.currency_code",
        "order.id",
        "order.name",
    ],
    idempotent=True,
)







if __name__ == "__main__":
    # product_id = "7678746361950"
    # print(f"\n=== orders['by_product'] product_id={product_id} ===\n")
    # result = orders["by_product"](product_id=product_id, first=100)
    # print(f"Fetched {len(result)} orders")
    # for order in result[:3]:
    #     print(json.dumps(order, indent=2, default=str))

    print("\n=== orders['cancel'] dry_run ===\n")
    orders["cancel"](
        order_id="8888888888888",
        reason="CUSTOMER",
        restock=False,
        notify_customer=False,
        staff_note="Approved via Slack workflow",
        dry_run=True,
    )

    print("\n=== refunds['create'] dry_run (payment refund, auto idempotency key) ===\n")
    refunds["create"](
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

    print("\n=== refunds['create'] dry_run (store credit, explicit idempotency_key override) ===\n")
    refunds["create"](
        order_id="8888888888888",
        note="Store credit refund approved via Slack workflow",
        notify=True,
        refund_methods=[
            {
                "store_credit_refund": {
                    "amount": {"amount": "50.00", "currency_code": "USD"},
                    "expires_at": "2027-06-16T00:00:00Z",
                }
            }
        ],
        idempotency_key="slack:store-credit:8888888888888:50.00",
        dry_run=True,
    )
