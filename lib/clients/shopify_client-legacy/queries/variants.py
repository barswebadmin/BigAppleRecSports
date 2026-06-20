"""Variant and inventory GraphQL queries and mutations."""

import requests

from shared_utilities.clients.shopify_client.gql import (
    GqlQuery,
    GqlResult,
    build_shopify_gid,
)


class GetVariant(GqlQuery):
    query = """
query getVariant($id: ID!) {
  node(id: $id) {
    ... on ProductVariant {
      id title inventoryItem { id }
    }
  }
}
"""
    data_key = "node"
    errors_key = None
    result_key = None

    def build_query(self, *, variant_id: str | int) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.query, {
            "id": build_shopify_gid("ProductVariant", variant_id),
        }

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        if not data or not data.get("inventoryItem"):
            return None, [{"message": "Variant not found"}]
        return data, None


class GetInventoryInfo(GqlQuery):
    query = """
query getInventoryInfo($variantId: ID!) {
  node(id: $variantId) {
    ... on ProductVariant {
      id inventoryQuantity inventoryItem { id sku }
    }
  }
}
"""
    data_key = "node"
    errors_key = None
    result_key = None

    def build_query(self, *, variant_id: str | int) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.query, {
            "variantId": build_shopify_gid("ProductVariant", variant_id),
        }

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        if not data or not data.get("inventoryItem"):
            return None, [{"message": "Variant or inventory item not found"}]
        return data, None


class AdjustInventory(GqlQuery):
    query = """
mutation adjustInventory($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      reason
      changes { name delta quantityAfterChange }
    }
    userErrors { field message }
  }
}
"""
    data_key = "inventoryAdjustQuantities"
    errors_key = "userErrors"
    result_key = "inventoryAdjustmentGroup"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        inventory_item_id: str,
        location_gid: str,
        delta: int,
    ) -> tuple[str, dict]:
        return self.query, {
            "input": {
                "reason": "correction",
                "name": "available",
                "changes": [{
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_gid,
                    "delta": delta,
                }],
            }
        }
