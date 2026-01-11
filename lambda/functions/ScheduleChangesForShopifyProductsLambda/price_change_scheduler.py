"""
Price change scheduling logic
Handles creating EventBridge schedules for changing product prices
"""

from typing import Dict, Any
from bars_common_utils.event_utils import get_field_safe
from get_discount_dates_and_prices import get_discount_dates_and_prices
from send_scheduled_price_updates import send_scheduled_price_updates

def create_scheduled_price_changes(event_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create EventBridge schedules for price changes throughout a season
    
    Expected event_body structure:
    {
        "actionType": "create-scheduled-price-changes",
        "sport": "Kickball",
        "day": "Monday", 
        "division": "Social",
        "productGid": "gid://shopify/Product/123456789",
        "openVariantGid": "gid://shopify/ProductVariant/123456789",
        "waitlistVariantGid": "gid://shopify/ProductVariant/123456789",
        "price": 115,
        "seasonStartDate": "2024-09-20",
        "sportStartTime": "21:00:00",
        "offDatesCommaSeparated": "2024-10-14,2024-11-28" (optional)
    }
    """
    print("💰 Creating scheduled price changes")
    
    # Validate required fields
    required_fields = [
        "sport", "day", "division", "price", 
        "seasonStartDate", "sportStartTime", "productGid", 
        "openVariantGid", "waitlistVariantGid"
    ]
    
    for field in required_fields:
        if field not in event_body:
            raise ValueError(f"❌ Missing required field: {field}")
    
    # Calculate price schedule
    updated_price_schedule = get_discount_dates_and_prices(
        season_start_date=event_body["seasonStartDate"],
        off_dates_comma_separated=get_field_safe(event_body, "offDatesCommaSeparated"),
        sport_start_time=event_body["sportStartTime"],
        price=event_body["price"]
    )
    
    # Update schedules
    failed_updates = send_scheduled_price_updates(
        action=event_body["actionType"],
        updated_price_schedule=updated_price_schedule,
        product_gid=event_body["productGid"],
        open_variant_gid=event_body["openVariantGid"],
        waitlist_variant_gid=event_body["waitlistVariantGid"],
        sport=event_body["sport"],
        day=event_body["day"],
        division=event_body["division"],
        season_start_date=event_body["seasonStartDate"],
        off_dates_comma_separated=get_field_safe(event_body, "offDatesCommaSeparated")
    )

    if failed_updates:
        raise ValueError(f"Some schedules failed to update: {failed_updates}")

    return {
        "message": "✅ All price change schedules updated successfully!",
        "price_schedule": updated_price_schedule
    }
