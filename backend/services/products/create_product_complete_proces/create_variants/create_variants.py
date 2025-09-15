"""
Product variants creation service - matching Create Variants From Row.gs structure
"""

import logging
from typing import Dict, Any
from models.products.product_creation_request import ProductCreationRequest
from services.shopify.shopify_service import ShopifyService

logger = logging.getLogger(__name__)

# Shopify location GID (from GAS code)
SHOPIFY_LOCATION_GID = "gid://shopify/Location/61802217566"


def create_variants(
    validated_request: ProductCreationRequest, product_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create variants for a product matching Create Variants From Row.gs structure

    Args:
        validated_request: Validated ProductCreationRequest instance
        product_data: Data from the product creation step (must include product_gid and productUrl)

    Returns:
        Dict with success status and variant data matching GAS format
    """
    basic_details = validated_request.regularSeasonBasicDetails
    important_dates = validated_request.importantDates
    inventory_info = validated_request.inventoryInfo

    product_gid = product_data.get("product_gid")
    product_url = product_data.get("productUrl") or product_data.get("product_url")

    if not product_gid:
        logger.error("product_gid is required for variant creation")
        return {"success": False, "error": "product_gid is required"}

    if not product_url:
        logger.error("productUrl is required for variant creation")
        return {"success": False, "error": "productUrl is required"}

    # Extract product ID from URL (matching GAS logic)
    product_id_digits_only = product_url.split("/")[-1] if product_url else ""

    logger.info(f"Creating variants for product: {product_id_digits_only}")

    # For development/testing mode when Shopify credentials aren't available
    from config import settings

    if not settings.shopify_token:
        logger.warning(
            "No Shopify token available - returning mock variants data for testing"
        )
        mock_variants = [
            {
                "type": "veteran",
                "variant_gid": "gid://shopify/ProductVariant/45123456789012345678",
                "price": inventory_info.price,
            },
            {
                "type": "early",
                "variant_gid": "gid://shopify/ProductVariant/45123456789012345679",
                "price": inventory_info.price,
            },
            {
                "type": "open",
                "variant_gid": "gid://shopify/ProductVariant/45123456789012345680",
                "price": inventory_info.price,
            },
            {
                "type": "waitlist",
                "variant_gid": "gid://shopify/ProductVariant/45123456789012345681",
                "price": inventory_info.price,
            },
        ]

        variant_mapping = {
            "vet": "gid://shopify/ProductVariant/45123456789012345678",
            "early": "gid://shopify/ProductVariant/45123456789012345679",
            "open": "gid://shopify/ProductVariant/45123456789012345680",
            "waitlist": "gid://shopify/ProductVariant/45123456789012345681",
        }

        return {
            "success": True,
            "data": {
                "variants": mock_variants,
                "variant_mapping": variant_mapping,
                "total_variants": 4,
                "product_gid": product_gid,
                "options_created": True,
                "first_variant_updated": True,
                "bulk_variants_created": True,
            },
        }

    try:
        shopify_service = ShopifyService()

        # Build variants array dynamically (exact GAS logic)
        variants_to_create = []

        # Check if veteran registration exists (exact GAS conditional)
        vet_registration = getattr(
            important_dates, "vetRegistrationStartDateTime", None
        )
        has_vet_registration = bool(vet_registration)

        if has_vet_registration:
            logger.info("✅ Including Veteran Registration variant.")
            variants_to_create.append(
                {
                    "title": "Veteran Registration",
                    "price": inventory_info.price,
                    "inventory": 0,
                    "type": "veteran",
                }
            )
        else:
            logger.info("⏭️ Skipping Veteran Registration variant.")

        # Add remaining variants (exact GAS logic)
        logger.info("➕ Adding remaining variants...")
        division_prefix = "W" if basic_details.division == "Open" else ""

        variants_to_create.extend(
            [
                {
                    "title": f"{division_prefix}TNB+ and BIPOC Early Registration",
                    "price": inventory_info.price,
                    "inventory": 0,
                    "type": "early",
                },
                {
                    "title": "Open Registration",
                    "price": inventory_info.price,
                    "inventory": 0,
                    "type": "open",
                },
                {
                    "title": "Coming Off Waitlist Registration",
                    "price": inventory_info.price,
                    "inventory": 0,
                    "type": "waitlist",
                },
            ]
        )

        # Step 1: Create product option and first variant (exact GAS productOptionsCreate)
        first_variant = variants_to_create[0]

        options_mutation = {
            "query": """
                mutation createOptions($productId: ID!, $options: [OptionCreateInput!]!) {
                    productOptionsCreate(productId: $productId, options: $options) {
                        userErrors { field message code }
                        product { options { id name optionValues { id name } } }
                    }
                }""",
            "variables": {
                "productId": product_gid,
                "options": [
                    {
                        "name": "Registration",
                        "values": [{"name": first_variant["title"]}],
                    }
                ],
            },
        }

        options_response = shopify_service._make_shopify_request(options_mutation)
        logger.info(f"Options creation response: {options_response}")

        # Step 2: Get GID of the first variant (exact GAS query)
        first_variant_query = {
            "query": """
                query($identifier: ProductIdentifierInput!) {
                    product: productByIdentifier(identifier: $identifier) {
                        variants(first: 1) { nodes { id } }
                    }
                }""",
            "variables": {"identifier": {"id": product_gid}},
        }

        first_variant_response = shopify_service._make_shopify_request(
            first_variant_query
        )
        first_variant_gid = (
            first_variant_response.get("data", {})
            .get("product", {})
            .get("variants", {})
            .get("nodes", [{}])[0]
            .get("id")
        )

        if not first_variant_gid:
            logger.error("❌ No first variant found.")
            return {"success": False, "error": "Failed to get first variant GID"}

        # Step 3: Update price and inventory for first variant (exact GAS logic)
        # Get inventory item ID
        inventory_query = {
            "query": """
                query GetInventoryItemId($variantId: ID!) {
                    productVariant(id: $variantId) {
                        inventoryItem { id }
                    }
                }""",
            "variables": {"variantId": first_variant_gid},
        }

        inventory_response = shopify_service._make_shopify_request(inventory_query)
        inventory_item_id = (
            inventory_response.get("data", {})
            .get("productVariant", {})
            .get("inventoryItem", {})
            .get("id")
        )

        if not inventory_item_id:
            logger.error("❌ Error fetching inventory item ID.")
            return {"success": False, "error": "Failed to get inventory item ID"}

        # Update price (exact GAS productVariantsBulkUpdate)
        price_update_mutation = {
            "query": """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                    productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants { id }
                        userErrors { field message }
                    }
                }""",
            "variables": {
                "productId": product_gid,
                "variants": [
                    {"id": first_variant_gid, "price": str(first_variant["price"])}
                ],
            },
        }

        price_response = shopify_service._make_shopify_request(price_update_mutation)
        logger.info(f"Price update response: {price_response}")

        # Update inventory (exact GAS inventoryAdjustQuantities)
        inventory_update_mutation = {
            "query": """
                mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                    inventoryAdjustQuantities(input: $input) {
                        userErrors { field message }
                    }
                }""",
            "variables": {
                "input": {
                    "reason": "movement_created",
                    "name": "available",
                    "changes": [
                        {
                            "delta": first_variant["inventory"],
                            "inventoryItemId": inventory_item_id,
                            "locationId": SHOPIFY_LOCATION_GID,
                        }
                    ],
                }
            },
        }

        inventory_response = shopify_service._make_shopify_request(
            inventory_update_mutation
        )
        logger.info(f"Inventory update response: {inventory_response}")

        # Step 4: Create remaining variants (exact GAS productVariantsBulkCreate)
        remaining_variants = variants_to_create[1:]
        created_variant_gids = []

        if remaining_variants:
            bulk_create_mutation = {
                "query": """
                    mutation ProductVariantsCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                        productVariantsBulkCreate(productId: $productId, variants: $variants) {
                            productVariants { id title }
                            userErrors { field message }
                        }
                    }""",
                "variables": {
                    "productId": product_gid,
                    "variants": [
                        {
                            "price": str(variant["price"]),
                            "inventoryQuantities": [
                                {
                                    "availableQuantity": variant["inventory"],
                                    "locationId": SHOPIFY_LOCATION_GID,
                                }
                            ],
                            "optionValues": [
                                {"name": variant["title"], "optionName": "Registration"}
                            ],
                        }
                        for variant in remaining_variants
                    ],
                },
            }

            bulk_response = shopify_service._make_shopify_request(bulk_create_mutation)
            created_variants = (
                bulk_response.get("data", {})
                .get("productVariantsBulkCreate", {})
                .get("productVariants", [])
            )

            logger.info(f"Bulk create response: {bulk_response}")

            # Extract GIDs from created variants
            for variant in created_variants:
                created_variant_gids.append(variant.get("id"))

        # Build variant mapping (matching GAS logic for sheet writing)
        variant_mapping = {}
        all_variant_gids = [first_variant_gid] + created_variant_gids

        # Map variants to their types (exact GAS logic)
        for i, variant_gid in enumerate(all_variant_gids):
            variant_title = variants_to_create[i]["title"]

            # Match GAS conditional logic for mapping
            if variant_title.lower().find("veteran") != -1:
                variant_mapping["vet"] = variant_gid
            elif variant_title.lower().find("early") != -1:
                variant_mapping["early"] = variant_gid
            elif variant_title.lower().find("open") != -1:
                variant_mapping["open"] = variant_gid
            elif variant_title.lower().find("waitlist") != -1:
                variant_mapping["waitlist"] = variant_gid

        # Build variants array for response (matching GAS structure)
        variants_list = []
        for i, variant_gid in enumerate(all_variant_gids):
            variant_info = variants_to_create[i]
            variants_list.append(
                {
                    "variant_gid": variant_gid,
                    "variant_id": variant_gid.split("/")[-1] if variant_gid else "",
                    "title": variant_info["title"],
                    "price": variant_info["price"],
                    "inventory": variant_info["inventory"],
                    "type": variant_info["type"],
                }
            )

        # Success response (matching expected format for sendProductInfoToBackendForCreation)
        result = {
            "success": True,
            "message": "✅ Product and Variants created successfully!",
            "data": {
                "product_id": product_id_digits_only,
                "product_gid": product_gid,
                "product_url": product_url,
                "variants": variants_list,
                "variant_mapping": variant_mapping,  # For easy access by type
                "total_variants": len(variants_list),
            },
        }

        logger.info(
            f"✅ Created {len(variants_list)} variants for product {product_id_digits_only}"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Error creating variants: {e}")
        return {
            "success": False,
            "message": f"Variant creation failed: {str(e)}",
            "error": str(e),
        }
