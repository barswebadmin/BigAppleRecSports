"""POC: gql DSL client using pre-pickled Shopify schema."""

import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dotenv
from autoregistry import Registry
from gql import Client
from gql.dsl import DSLQuery, DSLSchema, DSLSelector, DSLType, DSLVariableDefinitions, GraphQLRequest, dsl_gql
from gql.transport.httpx import HTTPXTransport
from graphql import GraphQLSchema




dotenv.load_dotenv()

# --- CONFIG (replace with real values) ---
EMAIL = "jdazz87@gmail.com"
# ------------------------------------------

PICKLE_PATH = Path(__file__).parent / "2026-07.graphql.pickle"


def parse_pickle(path: Path):
    """Load pre-parsed schema from pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)


class ShopifyClient:
    """Shopify Admin GraphQL client."""

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
        self.client = Client(schema=self.gql_schema, transport=transport)


    def to_query(self, query_name: str) -> DSLQuery:
        return getattr(self.dsl_schema, query_name)


    def to_resource(self, resource_name: str) -> DSLType:
        return getattr(self.dsl_schema, resource_name)

    def to_connection(self, connection_name: str) -> DSLSelector:
        return getattr(self.dsl_schema, connection_name)





    def _build_op(
        self,
        query: DSLType,
        resource: DSLType,
        connection: DSLSelector,
        variables: dict[str, Any],
        return_fields: list[str],
    ) -> GraphQLRequest:
        var = DSLVariableDefinitions()


        selections = [getattr(resource, field) for field in return_fields]

        op = DSLQuery(query.args(**variables).select(
            connection.nodes.select(*selections)
        ))
        op.variable_definitions = var
        return dsl_gql(op)




    def _run_op(self, operation: GraphQLRequest, variables: dict[str, Any]) -> dict[str, Any]:
        with self.client as session:
            return session.execute(operation, variable_values=variables)


    def query(
        self,
        query_name: str,
        resource_name: str,
        connection_name: str,
        variables: dict[str, Any],
        return_fields: list[str],
    ) -> dict[str, Any]:
        query_root = self.dsl_schema.QueryRoot
        resource_query = getattr(query_root, query_name)
        resource = self.to_resource(resource_name)
        connection = self.to_connection(connection_name)
        operation = self._build_op(resource_query, resource, connection, variables, return_fields)
        return self._run_op(operation, variables)







shopify = Registry()

@dataclass
class ShopifySchema:
    query_name: str
    resource_name: str
    connection_name: str
    default_return_fields: list[str]
    client: ShopifyClient | None = None

    def __post_init__(self):
        if self.client is None:
            self.client = ShopifyClient()

    def get(self, *, variables: dict[str, Any], returns: list[str] | None = None):
        fields = returns if returns is not None else self.default_return_fields
        return self.client.query(self.query_name, self.resource_name, self.connection_name, variables, fields)




shopify["customers"] = ShopifySchema(
    query_name="customers",
    resource_name="Customer",
    connection_name="CustomerConnection",
    default_return_fields=[
        "id",
        "email",
        "firstName",
        "lastName",
        "phone",
        "createdAt",
        "updatedAt",
        "numberOfOrders",
        "amountSpent",
        "note",
        "tags",
        "verifiedEmail",
        "state",
    ],
)

shopify["orders"] = ShopifySchema(
    query_name="orders",
    resource_name="Order",
    connection_name="OrderConnection",
    default_return_fields=[
        "id",
        "name",
        "email",
        "createdAt",
        "updatedAt",
        "displayFinancialStatus",
        "displayFulfillmentStatus",
        "cancelledAt",
        "cancelReason",
        "note",
        "tags",
        "totalPriceSet",
        "subtotalPriceSet",
        "totalTaxSet",
        "totalDiscountsSet",
        "totalRefundedSet",
    ],
)















if __name__ == "__main__":
    customer = shopify["customers"].get(
        variables={"query": "email:jdazz87@gmail.com", "first": 1},
    )
    print("Customer:", customer)

    orders = shopify["orders"].get(
        variables={"query": "email:jdazz87@gmail.com", "first": 5},
    )
    print("Orders:", orders)
