"""Product-related GraphQL queries and mutations."""

import requests

from shared_utilities.clients.shopify_client.gql import (
    GqlQuery,
    GqlResult,
    build_shopify_gid,
)


class GetProduct(GqlQuery):
    query = """
query getProduct($id: ID!) {
  product(id: $id) {
    id title handle tags status descriptionHtml createdAt
    variants(first: 5) {
      nodes { id title inventoryItem { id } inventoryQuantity }
    }
    media(first: 10) {
      nodes { id }
    }
  }
}
"""
    data_key = "product"
    errors_key = None
    result_key = None

    def build_query(self, *, product_id: str | int) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.query, {"id": build_shopify_gid("Product", product_id)}

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        if not data:
            return None, [{"message": "Product not found"}]
        data["media_ids"] = [
            node["id"]
            for node in data.get("media", {}).get("nodes", [])
        ]
        return data, None


class UpdateProduct(GqlQuery):
    query = """
mutation updateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title tags media(first: 10) { nodes { id } } }
    userErrors { field message }
  }
}
"""
    data_key = "productUpdate"
    errors_key = "userErrors"
    result_key = "product"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, *, product_id: str | int, **fields
    ) -> tuple[str, dict]:
        return self.query, {
            "input": {
                "id": build_shopify_gid("Product", product_id),
                **fields,
            }
        }


class BulkUpdateVariantPrices(GqlQuery):
    query = """
mutation bulkUpdatePrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price }
    userErrors { field message }
  }
}
"""
    data_key = "productVariantsBulkUpdate"
    errors_key = "userErrors"
    result_key = "productVariants"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        product_id: str | int,
        variant_prices: list[dict],
    ) -> tuple[str, dict]:
        return self.query, {
            "productId": build_shopify_gid("Product", product_id),
            "variants": variant_prices,
        }
