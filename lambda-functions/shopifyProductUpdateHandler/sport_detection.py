"""
Sport detection and configuration utilities for product image updates
"""

from typing import List, Dict, Optional

# Sport-specific sold-out image URLs
SPORT_IMAGE_URLS = {
    "bowling": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Bowling_ClosedWaitList.png?v=1750988743",
    "dodgeball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Dodgeball_Closed.png?v=1750214647",
    "kickball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Kickball_WaitlistOnly.png?v=1751381022",
    "pickleball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Pickleball_WaitList.png?v=1750287195"
}

def detect_sport(title: str, tags: str) -> Optional[str]:
    """
    Detect the sport from product title and tags
    
    Args:
        title: Product title (case-insensitive)
        tags: Product tags (case-insensitive)
        
    Returns:
        Sport name if detected, None otherwise
    """
    title_lower = title.lower()
    tags_lower = tags.lower()
    
    for sport in SPORT_IMAGE_URLS:
        if sport in title_lower or sport in tags_lower:
            return sport
    return None

def get_sold_out_image_url(sport: str) -> Optional[str]:
    """
    Get the sold-out image URL for a given sport
    
    Args:
        sport: Sport name
        
    Returns:
        Image URL if sport is supported, None otherwise
    """
    return SPORT_IMAGE_URLS.get(sport)

def is_all_closed(variants: List[Dict]) -> bool:
    """
    Check if all relevant variants are sold out (inventory = 0)
    
    Relevant variants are those containing:
    - "vet", "bipoc", "trans", "early", or "open" in title
    - But NOT "wait" or "team" in title
    
    Args:
        variants: List of product variant dictionaries
        
    Returns:
        True if all relevant variants are sold out, False otherwise
    """
    def is_relevant_variant(variant_title: str) -> bool:
        """Check if a variant is relevant for sold-out detection"""
        title_lower = variant_title.lower()
        
        # Must contain one of these terms
        required_terms = ["vet", "bipoc", "trans", "early", "open"]
        has_required = any(term in title_lower for term in required_terms)
        
        # Must NOT contain these terms
        excluded_terms = ["wait", "team"]
        has_excluded = any(term in title_lower for term in excluded_terms)
        
        return has_required and not has_excluded
    
    # Find all relevant variants
    relevant_variants = [
        v for v in variants 
        if is_relevant_variant(v.get("title", ""))
    ]
    
    print(f"🔍 Relevant variants: {[v['title'] for v in relevant_variants]}")
    
    if not relevant_variants:
        print("ℹ️  No relevant variants found")
        return False
    
    # Check if all relevant variants are sold out
    return all(v.get("inventory_quantity", 1) == 0 for v in relevant_variants)

def get_supported_sports() -> List[str]:
    """
    Get list of all supported sports
    
    Returns:
        List of supported sport names
    """
    return list(SPORT_IMAGE_URLS.keys()) 