"""
Shopify image update operations for product sold-out handling
"""

import json
import os
import urllib.request
import urllib.error
from typing import Dict, List, Optional
def _get_ssm_param(name: str) -> str:
    try:
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
        ssm = boto3.client("ssm")
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    except (NameError, ModuleNotFoundError) as e:
        raise RuntimeError("boto3 is required at runtime to fetch Shopify token from SSM") from e
    except Exception as e:  # pylint: disable=broad-except
        print(f"❌ Failed to load Shopify token from SSM parameter '{name}': {e}")
        raise

# Configuration
SHOP_DOMAIN = "09fe59-3.myshopify.com"

class ShopifyImageUpdater:
    """Handles Shopify product image updates via REST and GraphQL APIs"""
    
    def __init__(self):
        self.access_token = self._resolve_access_token()
        self.shop_domain = SHOP_DOMAIN
    def _resolve_access_token(self) -> str:
        env_token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
        if env_token:
            return env_token
        name = os.environ.get("SHOPIFY_TOKEN_PARAM_NAME", "/shopify/api/web-admin-token")
        return _get_ssm_param(name)
    
    def update_product_image(self, product_id: str, product_gid: str, image_url: str, sport: str, original_image: Optional[str] = None) -> bool:
        """
        Update product image, with fallback strategy if needed
        
        Args:
            product_id: Shopify product ID (numeric)
            product_gid: Shopify product GID (gid://shopify/Product/...)
            image_url: New image URL to set
            sport: Sport name for alt text
            original_image: Original image URL for rollback if needed
            
        Returns:
            True if update succeeded, False otherwise
        """
        print(f"🖼️  Updating product {product_id} image to: {image_url}")
        
        # Try REST API first (simpler and faster)
        success = self._try_rest_image_update(product_id, image_url)
        
        if not success:
            print("⚠️ REST image update failed. Trying GraphQL media replacement fallback.")
            success = self._replace_media_graphql(product_gid, image_url, sport)
            
            if not success and original_image:
                print("⚠️ GraphQL fallback failed. Restoring original image.")
                self._try_rest_image_update(product_id, original_image)
        
        return success
    
    def _try_rest_image_update(self, product_id: str, image_url: str) -> bool:
        """
        Try updating product image via REST API
        
        Args:
            product_id: Shopify product ID 
            image_url: Image URL to set
            
        Returns:
            True if successful, False otherwise
        """
        url = f"https://{self.shop_domain}/admin/api/2025-10/products/{product_id}.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        payload = {
            "product": {
                "id": product_id,
                "image": {
                    "src": image_url
                }
            }
        }

        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode("utf-8"), 
                headers=headers, 
                method="PUT"
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                print("✅ REST image update succeeded.")
                print(json.dumps(result, indent=2))
                return True
                
        except urllib.error.HTTPError as e:
            error_details = e.read().decode()
            print(f"❌ REST image update failed: {error_details}")
            return False
        except Exception as e:
            print(f"❌ REST image update error: {str(e)}")
            return False

    def _replace_media_graphql(self, product_gid: str, image_url: str, sport: str) -> bool:
        """
        Replace product media using GraphQL (delete all, add new)
        
        Args:
            product_gid: Product GID 
            image_url: New image URL
            sport: Sport name for alt text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Get current media IDs
            media_ids = self._get_product_media_ids(product_gid)
            print(f"🧹 Found {len(media_ids)} media items to delete")

            # Step 2: Delete all existing media
            if media_ids:
                delete_success = self._delete_product_media(product_gid, media_ids)
                if not delete_success:
                    return False

            # Step 3: Add new media image
            return self._add_product_media(product_gid, image_url, sport)

        except Exception as e:
            print(f"❌ GraphQL media replacement failed: {str(e)}")
            return False

    def _get_product_media_ids(self, product_gid: str) -> List[str]:
        """Get all media IDs for a product"""
        query = f"""
        {{
          product(id: "{product_gid}") {{
            media(first: 100) {{
              nodes {{
                id
              }}
            }}
          }}
        }}
        """
        result = self._send_graphql(query)
        media_nodes = result.get("data", {}).get("product", {}).get("media", {}).get("nodes", [])
        return [node["id"] for node in media_nodes]

    def _delete_product_media(self, product_gid: str, media_ids: List[str]) -> bool:
        """Delete product media using GraphQL"""
        mutation = """
        mutation productDeleteMedia($mediaIds: [ID!]!, $productId: ID!) {
          productDeleteMedia(mediaIds: $mediaIds, productId: $productId) {
            deletedMediaIds
            deletedProductImageIds
            mediaUserErrors {
              field
              message
            }
            product {
              id
              title
              media(first: 5) {
                nodes {
                  alt
                  mediaContentType
                  status
                }
              }
            }
          }
        }
        """
        variables = {
            "mediaIds": media_ids,
            "productId": product_gid
        }

        result = self._send_graphql(mutation, variables)
        errors = result.get("data", {}).get("productDeleteMedia", {}).get("mediaUserErrors", [])
        
        if errors:
            print(f"❌ Media deletion errors: {errors}")
            return False
            
        print("🗑️ Media deleted successfully")
        return True

    def _add_product_media(self, product_gid: str, image_url: str, sport: str) -> bool:
        """Add new media to product using GraphQL"""
        mutation = """
        mutation UpdateProductWithNewMedia($product: ProductUpdateInput!, $media: [CreateMediaInput!]) {
          productUpdate(product: $product, media: $media) {
            product {
              id
              media(first: 10) {
                nodes {
                  alt
                  mediaContentType
                  preview { status }
                }
              }
            }
            userErrors { field message }
          }
        }
        """
        variables = {
            "product": {"id": product_gid},
            "media": [{
                "originalSource": image_url,
                "alt": f"Sold out image for {sport}",
                "mediaContentType": "IMAGE"
            }]
        }

        result = self._send_graphql(mutation, variables)
        errors = result.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        
        if errors:
            print(f"❌ Media addition errors: {errors}")
            return False
            
        print("✅ Media added successfully")
        return True

    def _send_graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Send GraphQL request to Shopify"""
        url = f"https://{self.shop_domain}/admin/api/2025-10/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        payload: Dict = {"query": query}
        if variables:
            payload["variables"] = variables

        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode()) 