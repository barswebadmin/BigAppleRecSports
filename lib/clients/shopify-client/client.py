"""POC: gql DSL client using pre-pickled Shopify schema."""

import os
import dotenv
import pickle
from dataclasses import dataclass
from typing import Any

from pathlib import Path

from gql import Client
from gql.transport.httpx import HTTPXTransport
from gql.dsl import DSLFragment, DSLQuery, DSLMutation, DSLSchema, dsl_gql, DSLType, DSLExecutable, DSLSelector, GraphQLRequest, DSLVariableDefinitions, DSLVariable, DSLSelectable

from autoregistry import Registry




dotenv.load_dotenv()

# --- CONFIG (replace with real values) ---
EMAIL = "jdazz87@gmail.com"
# ------------------------------------------

PICKLE_PATH = Path(__file__).parent / "2026-07.graphql.pickle"
SCHEMA_CACHE = None




def parse_pickle(path: Path):
    """Load pre-parsed schema from pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)




class ShopifyClient:
    """Shopify Admin GraphQL client."""

    def __init__(
        self,
        *,
        store_id: int = os.environ["SHOPIFY__STORE_ID"],
        api_version: str = os.environ["SHOPIFY__API_VERSION"],
        token: str = os.environ["SHOPIFY__TOKEN__ADMIN"]
    ):
        global SCHEMA_CACHE
        if SCHEMA_CACHE is None:
            SCHEMA_CACHE = parse_pickle(PICKLE_PATH)

        self.gql_schema = SCHEMA_CACHE
        self.dsl_schema = DSLSchema(SCHEMA_CACHE)
        transport = HTTPXTransport(
            url=f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json",
            headers={"X-Shopify-Access-Token": token},
        )
        self.client = Client(schema=self.gql_schema, transport=transport)


    def load_schema(self):
        global SCHEMA_CACHE
        SCHEMA_CACHE = parse_pickle(PICKLE_PATH)
        return DSLSchema(SCHEMA_CACHE)


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
    client: ShopifyClient | None = ShopifyClient()


    def get(self, *, variables: dict[str, Any], returns: list[str]):
        return self.client.query(self.query_name, self.resource_name, self.connection_name, variables, returns)




# class Customers(ShopifySchema):
#     query_name = "customers"
#     resource_name = "Customer"
#     connection_name = "CustomerConnection"

#     def get(self, *, variables: dict[str, Any], returns: list[str]):
#         return self.client.query(self.query_name, self.resource_name, self.connection_name, variables, returns)


shopify["customers"] = ShopifySchema(query_name="customers", resource_name="Customer", connection_name="CustomerConnection")


















if __name__ == "__main__":
    customer = shopify["customers"].get(variables={"query": "email:jdazz87@gmail.com", "first": 1}, returns=["id", "email"])
    print(customer)
