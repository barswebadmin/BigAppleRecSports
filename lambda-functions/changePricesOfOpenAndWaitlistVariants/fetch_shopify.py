import os
import json
import urllib.request


SHOPIFY_API_URL = "https://09fe59-3.myshopify.com/admin/api/2025-04/graphql.json"

_CACHED_SHOPIFY_TOKEN = None

def _get_shopify_access_token():
    global _CACHED_SHOPIFY_TOKEN
    env_token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    if env_token:
        return env_token
    if _CACHED_SHOPIFY_TOKEN:
        return _CACHED_SHOPIFY_TOKEN
    name = os.environ.get("SHOPIFY_TOKEN_PARAM_NAME", "/shopify/api/web-admin-token")
    try:
        # Lazy import to avoid test dependency on boto3
        import boto3  # type: ignore
        from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
        ssm = boto3.client("ssm")
        resp = ssm.get_parameter(Name=name, WithDecryption=True)
        token = resp["Parameter"]["Value"]
        _CACHED_SHOPIFY_TOKEN = token
        return token
    except (NameError, ModuleNotFoundError) as e:
        raise RuntimeError("boto3 is required at runtime to fetch Shopify token from SSM") from e
    except Exception as e:
        print(f"❌ Failed to load Shopify token from SSM parameter '{name}': {e}")
        raise

def fetch_shopify(query, variables=None):
    payload = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": _get_shopify_access_token()
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