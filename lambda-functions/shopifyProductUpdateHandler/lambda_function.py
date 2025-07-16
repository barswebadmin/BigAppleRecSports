import json
import os
import urllib.request
import urllib.error
import time

ACCESS_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
SHOP_DOMAIN = "09fe59-3.myshopify.com"

IMAGE_URLS = {
    "bowling": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Bowling_ClosedWaitList.png?v=1750988743",
    "dodgeball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Dodgeball_Closed.png?v=1750214647",
    "kickball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Kickball_WaitlistOnly.png?v=1751381022",
    "pickleball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Pickleball_WaitList.png?v=1750287195"
}

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    try:
        body = json.loads(event.get("body", "{}"))
        product_id = body.get("id")
        product_gid = body.get("admin_graphql_api_id")
        product_title = body.get("title", "").lower()
        product_tags = body.get("tags", "").lower()
        product_image = body.get("image", {}).get("src")
        variants = body.get("variants", [])

        if not product_id or not product_gid or not variants:
            print("⚠️ Missing product ID, GID, or variants.")
            return respond()

        if is_all_closed(variants):
            sport = detect_sport(product_title, product_tags)
            print(f"🏷️ Detected sport: {sport}")

            if sport in IMAGE_URLS:
                sold_out_url = IMAGE_URLS[sport]
                success = try_rest_image_update(product_id, sold_out_url)
                success = False
                if not success:
                    print("⚠️ REST image update failed. Trying media delete-and-replace fallback.")
                    fallback_success = replace_media(product_gid, sold_out_url, sport)
                    if not fallback_success:
                        print("⚠️ Fallback failed. Re-applying original image.")
                        if product_image:
                            try_rest_image_update(product_id, product_image)
                        else:
                            print("⚠️ No original image available.")
            else:
                print("ℹ️ Unrecognized sport. No action taken.")
        else:
            print("ℹ️ Product still has inventory.")

    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    return respond()

def is_all_closed(variants):
    def is_relevant(title):
        title = title.lower()
        return (
            "vet" in title or
            "bipoc" in title or
            "trans" in title or
            "early" in title or
            "open" in title
        ) and "wait" not in title and "team" not in title

    relevant = [v for v in variants if is_relevant(v.get("title", ""))]
    print(f"🔍 Relevant variants: {[v['title'] for v in relevant]}")
    return all(v.get("inventory_quantity", 1) == 0 for v in relevant)

def detect_sport(title, tags):
    for sport in IMAGE_URLS:
        if sport in title or sport in tags:
            return sport
    return None

def try_rest_image_update(product_id, image_url):
    url = f"https://{SHOP_DOMAIN}/admin/api/2025-10/products/{product_id}.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": ACCESS_TOKEN
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
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print("✅ REST image update succeeded.")
            print(json.dumps(result, indent=2))
            return True
    except urllib.error.HTTPError as e:
        print("❌ REST image update failed:", e.read().decode())
        return False

def replace_media(product_gid, image_url, sport):
    try:
        # Step 1: Get current media IDs
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
        result = send_graphql(query)
        media_nodes = result.get("data", {}).get("product", {}).get("media", {}).get("nodes", [])
        media_ids = [node["id"] for node in media_nodes]
        print(f"🧹 Found {len(media_ids)} media items to delete")

        # Step 2: Delete all media using productDeleteMedia
        if media_ids:
            delete_query = """
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
            delete_vars = {
                "mediaIds": media_ids,
                "productId": product_gid
            }

            delete_result = send_graphql(delete_query, delete_vars)
            print("🗑️ Deleted media:")
            print(json.dumps(delete_result, indent=2))

        # Step 3: Add new media image
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

        media_result = send_graphql(mutation, variables)
        print("✅ Media replaced via GraphQL.")
        print(json.dumps(media_result, indent=2))
        return True

    except Exception as e:
        print(f"❌ Media replace failed: {str(e)}")
        return False

def send_graphql(query, variables=None):
    url = f"https://{SHOP_DOMAIN}/admin/api/2025-10/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def respond():
    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }