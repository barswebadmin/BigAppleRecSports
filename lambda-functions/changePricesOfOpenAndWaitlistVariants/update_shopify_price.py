import json

from bars_common_utils.shopify_utils import fetch_shopify

def update_shopify_price(product_gid, open_variant_gid, waitlist_variant_gid, updated_price):

    query = (
        'mutation updatePrice { '
        'productVariantsBulkUpdate('
        f'productId: "{product_gid}", '
        'variants: ['
        f'{{id: "{open_variant_gid}", price: "{float(updated_price):.2f}"}},'
        f'{{id: "{waitlist_variant_gid}", price: "{float(updated_price):.2f}"}}'
        ']'
        ') { '
        'productVariants { id price } '
        'userErrors { field message } '
        '} '
        '}'
    )

    try:
        # fetch_shopify returns the "data" portion of the response
        data = fetch_shopify(query)

        print("✅ Shopify response:", json.dumps(data, indent=2))

        user_errors = data.get("productVariantsBulkUpdate", {}).get("userErrors", [])
        if user_errors:
            raise Exception(f"Shopify User Errors: {user_errors}")

        return data["productVariantsBulkUpdate"]["productVariants"]

    
    except Exception as e:
        print("❌ update_shopify_price failed:", str(e))
        raise