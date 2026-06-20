"""Media-related GraphQL queries and mutations."""

import requests

from shared_utilities.clients.shopify_client.gql import (
    GqlQuery,
    GqlResult,
    build_shopify_gid,
)


class GetMediaImageUrl(GqlQuery):
    query = """
query getMediaImageUrl($id: ID!) {
  node(id: $id) {
    ... on MediaImage {
      image { url }
    }
  }
}
"""
    data_key = "node"
    errors_key = None
    result_key = None

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, *, media_image_id: str | int
    ) -> tuple[str, dict]:
        return self.query, {
            "id": build_shopify_gid("MediaImage", media_image_id),
        }

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        url = (data or {}).get("image", {}).get("url")
        if not url:
            return None, [
                {"message": "MediaImage not found or has no URL"}
            ]
        return url, None


class FileUpdateProductRef(GqlQuery):
    """Associate or disassociate a Content > Files library file
    with a product via fileUpdate.

    file_id must be the numeric ID of the File node
    (not a product MediaImage node).
    """

    query = """
mutation fileUpdateProductRef($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) {
    files { id }
    userErrors { field message }
  }
}
"""
    data_key = "fileUpdate"
    errors_key = "userErrors"
    result_key = "files"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        file_id: str | int,
        product_id: str | int,
        attach: bool,
    ) -> tuple[str, dict]:
        product_gid = build_shopify_gid("Product", product_id)
        file_gid = build_shopify_gid("MediaImage", file_id)
        ref_input = (
            {"referencesToAdd": [product_gid]}
            if attach
            else {"referencesToRemove": [product_gid]}
        )
        return self.query, {"files": [{"id": file_gid, **ref_input}]}


class DeleteProductMedia(GqlQuery):
    query = """
mutation deleteProductMedia($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    userErrors { field message }
  }
}
"""
    data_key = "productDeleteMedia"
    errors_key = "userErrors"
    result_key = "deletedMediaIds"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, *, product_id: str | int, media_ids: list[str]
    ) -> tuple[str, dict]:
        return self.query, {
            "productId": build_shopify_gid("Product", product_id),
            "mediaIds": media_ids,
        }


class AttachProductMedia(GqlQuery):
    query = """
mutation attachProductMedia($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { id }
    userErrors { field message }
  }
}
"""
    data_key = "productCreateMedia"
    errors_key = "userErrors"
    result_key = "media"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, *, product_id: str | int, image_url: str
    ) -> tuple[str, dict]:
        return self.query, {
            "productId": build_shopify_gid("Product", product_id),
            "media": [
                {
                    "mediaContentType": "IMAGE",
                    "originalSource": image_url,
                }
            ],
        }
