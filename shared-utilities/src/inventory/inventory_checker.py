"""
Shared inventory checking utilities

This module provides functions to check product inventory status and determine
if products should be considered out of stock based on business rules.
"""

from typing import Dict, List, Any


def has_zero_inventory(product_data: Dict[str, Any]) -> bool:
    """
    Check if a product has zero inventory for all relevant variants.

    Args:
        product_data: Shopify product data containing variants

    Returns:
        bool: True if all relevant variants have zero inventory
    """
    if not product_data or "variants" not in product_data:
        return False

    variants = product_data["variants"]
    if not variants:
        return False

    # Get relevant variants (those that should be considered for inventory)
    relevant_variants = get_purchasable_variants_info(product_data)

    if not relevant_variants:
        return False

    # Check if all relevant variants have zero inventory
    return all(
        variant.get("inventory_quantity", 0) <= 0 for variant in relevant_variants
    )


def get_purchasable_variants_info(product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get variants that are considered purchasable (not wait or team variants).

    Args:
        product_data: Shopify product data containing variants

    Returns:
        List of variant dictionaries that are purchasable
    """
    if not product_data or "variants" not in product_data:
        return []

    variants = product_data["variants"]
    if not variants:
        return []

    purchasable_variants = []

    for variant in variants:
        title = variant.get("title", "").lower()

        # Skip variants that contain "wait" or "team" (case insensitive)
        if "wait" in title or "team" in title:
            continue

        # Only include variants that allow purchases when out of stock is deny
        inventory_policy = variant.get("inventory_policy", "deny")
        if inventory_policy == "deny":
            purchasable_variants.append(variant)

    return purchasable_variants


def is_sport_product(product_data: Dict[str, Any]) -> bool:
    """
    Determine if a product is a sport product based on its title.

    Args:
        product_data: Shopify product data

    Returns:
        bool: True if this appears to be a sport product
    """
    if not product_data:
        return False

    title = product_data.get("title", "").lower()

    # BARS sport keywords (only 4 sports)
    sport_keywords = ["kickball", "bowling", "pickleball", "dodgeball"]

    return any(keyword in title for keyword in sport_keywords)
