import os
import json
import urllib.request


SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "your_shopify_token")
SHOPIFY_API_URL = "https://09fe59-3.myshopify.com/admin/api/2025-04/graphql.json"

def fetch_shopify(query, variables=None):
    payload = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN
    }

    req = urllib.request.Request(SHOPIFY_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode()
            print("📬 Raw Shopify Response:", response_text)
            response_json = json.loads(response_text)

        if "errors" in response_json:
            print("❌ Shopify GraphQL Errors:", json.dumps(response_json["errors"], indent=2))
            raise Exception(f"GraphQL error: {response_json['errors']}")
            
        return response_json.get("data")

    except Exception as e:
        print("❌ fetch_shopify failed:", str(e))
        raise