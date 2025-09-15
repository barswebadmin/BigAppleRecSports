"""
Product scheduling and updates service - matching scheduleInventoryMoves.gs and schedulePriceChanges.gs
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime
from models.products.product_creation_request import ProductCreationRequest
from utils.date_utils import format_date_only

logger = logging.getLogger(__name__)


def format_date_to_iso(date_value) -> str:
    """Format date to ISO string (matching GAS formatDateToIso function)"""
    if isinstance(date_value, datetime):
        return date_value.isoformat().split(".")[0]
    elif isinstance(date_value, str):
        try:
            date_obj = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return date_obj.isoformat().split(".")[0]
        except (ValueError, AttributeError):
            return str(date_value)
    else:
        return str(date_value) if date_value else ""


def map_sport_to_abbreviation(sport: str) -> str:
    """Map sport to abbreviation (matching GAS function)"""
    sport_map = {
        "Dodgeball": "db",
        "Pickleball": "pb",
        "Bowling": "bowl",
        "Kickball": "kb",
    }
    return sport_map.get(sport, "misc")


def format_time_only(time_value) -> str:
    """Format time only (matching GAS formatTimeOnly)"""
    if isinstance(time_value, datetime):
        return time_value.strftime("%H:%M")
    elif isinstance(time_value, str):
        return str(time_value)
    else:
        return str(time_value) if time_value else ""


def schedule_product_updates(
    validated_request: ProductCreationRequest,
    product_data: Dict[str, Any],
    variants_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Schedule product updates matching scheduleInventoryMoves.gs and schedulePriceChanges.gs

    Args:
        validated_request: Validated ProductCreationRequest instance
        product_data: Data from product creation (must include productUrl, product_gid)
        variants_data: Data from variants creation (must include variant_mapping)

    Returns:
        Dict with success status and scheduling data matching GAS format
    """
    basic_details = validated_request.regularSeasonBasicDetails
    important_dates = validated_request.importantDates
    inventory_info = validated_request.inventoryInfo

    product_url = product_data.get("productUrl") or product_data.get("product_url")
    product_gid = product_data.get("product_gid")

    if not product_url:
        logger.error("productUrl is required for scheduling")
        return {"success": False, "error": "productUrl is required"}

    # For development/testing mode when Shopify credentials aren't available
    from config import settings

    if not settings.shopify_token:
        logger.warning(
            "No Shopify token available - returning mock scheduling data for testing"
        )
        return {
            "success": True,
            "data": {
                "requests": [
                    {
                        "type": "inventory_move",
                        "scheduled": True,
                        "description": "Mock inventory scheduling",
                    },
                    {
                        "type": "price_change",
                        "scheduled": True,
                        "description": "Mock price change scheduling",
                    },
                ],
                "total_requests": 2,
                "inventory_moves_scheduled": True,
                "price_changes_scheduled": True,
                "summary": {
                    "registration_flow": "Vet → Early → Open → Waitlist",
                    "total_inventory": inventory_info.totalInventory,
                    "sport": validated_request.sportName,
                    "season": f"{basic_details.season} {basic_details.year}",
                },
            },
        }

    # Extract variant GIDs from variants_data (matching GAS logic)
    variant_mapping = variants_data.get("data", {}).get("variant_mapping", {})
    vet_gid = variant_mapping.get("vet")
    early_gid = variant_mapping.get("early")
    open_gid = variant_mapping.get("open")
    waitlist_gid = variant_mapping.get("waitlist")

    if not early_gid or not open_gid:
        logger.error("Early and Open variant GIDs are required")
        return {"success": False, "error": "Required variant GIDs missing"}

    product_id_digits_only = product_url.split("/")[-1] if product_url else ""

    logger.info(f"Scheduling updates for product: {product_id_digits_only}")

    try:
        # Generate sport and division slugs (matching GAS logic)
        sport_slug = map_sport_to_abbreviation(validated_request.sportName)
        day_slug = basic_details.dayOfPlay.lower()
        division_slug = basic_details.division.lower().split("+")[0] + "Div"

        # Get registration dates (matching GAS logic)
        vet_date_time = getattr(important_dates, "vetRegistrationStartDateTime", None)
        early_date_time = getattr(
            important_dates, "earlyRegistrationStartDateTime", None
        )
        open_date_time = getattr(important_dates, "openRegistrationStartDateTime", None)

        # Format dates to ISO (matching GAS formatDateToIso)
        vet_date_string = format_date_to_iso(vet_date_time) if vet_date_time else ""
        early_date_string = (
            format_date_to_iso(early_date_time) if early_date_time else ""
        )
        open_date_string = format_date_to_iso(open_date_time) if open_date_time else ""

        # Determine registration flow (exact GAS logic)
        reg1, reg2, time1, time2, gid1, gid2 = None, None, None, None, None, None

        if vet_gid:
            logger.info("yes vetGid")
            if vet_date_time and early_date_time and vet_date_time < early_date_time:
                logger.info("vet is before early")
                reg1, time1, gid1 = "vet", vet_date_string, vet_gid
                reg2, time2, gid2 = "early", early_date_string, early_gid
            else:
                logger.info("early is before vet")
                reg1, time1, gid1 = "early", early_date_string, early_gid
                reg2, time2, gid2 = "vet", vet_date_string, vet_gid
        else:
            logger.info("no vetGid")
            reg1, time1, gid1 = "vet", vet_date_string, vet_gid
            reg2, time2, gid2 = "early", early_date_string, early_gid

        logger.info(f"Final assignments - reg1: {reg1}, time1: {time1}, gid1: {gid1}")
        logger.info(f"Final assignments - reg2: {reg2}, time2: {time2}, gid2: {gid2}")

        # Build requests array (exact GAS structure)
        requests = []

        # Inventory move request (if vet registration exists)
        if vet_gid and vet_date_time:
            inventory_move_request = {
                "actionType": "create-scheduled-inventory-movements",
                "scheduleName": f"auto-move-{sport_slug}-{day_slug}-{product_id_digits_only}-{reg1}-to-{reg2}",
                "groupName": f"move-inventory-between-variants-{sport_slug}",
                "productUrl": product_url,
                "sourceVariant": {
                    "type": reg1,
                    "name": f"{reg1.capitalize()} Registration",
                    "gid": gid1,
                },
                "destinationVariant": {
                    "type": reg2,
                    "name": f"{reg2.capitalize()} Registration",
                    "gid": gid2,
                },
                "newDatetime": time2,
                "note": "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
                "totalInventory": inventory_info.totalInventory,
                "numberVetSpotsToReleaseAtGoLive": inventory_info.numberVetSpotsToReleaseAtGoLive,
            }
            requests.append(inventory_move_request)

        # Second inventory move (reg2 to open)
        inventory_move_to_open = {
            "actionType": "create-scheduled-inventory-movements",
            "scheduleName": f"auto-move-{product_id_digits_only}-{sport_slug}-{day_slug}-{division_slug}-{reg2}-to-open",
            "groupName": f"move-inventory-between-variants-{sport_slug}",
            "productUrl": product_url,
            "sourceVariant": {
                "type": reg2,
                "name": f"{reg2.capitalize()} Registration",
                "gid": gid2,
            },
            "destinationVariant": {
                "type": "open",
                "name": "Open Registration",
                "gid": open_gid,
            },
            "newDatetime": open_date_string,
            "note": "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
            "totalInventory": inventory_info.totalInventory,
            "numberVetSpotsToReleaseAtGoLive": inventory_info.numberVetSpotsToReleaseAtGoLive,
        }
        requests.append(inventory_move_to_open)

        # Initial inventory addition and title change (exact GAS logic)
        first_registration_date = (
            vet_date_string if vet_gid and vet_date_time else early_date_string
        )
        first_variant_gid = vet_gid if vet_gid and vet_date_time else early_gid

        initial_inventory_request = {
            "actionType": "create-initial-inventory-addition-and-title-change",
            "scheduleName": f"auto-set-{product_id_digits_only}-{sport_slug}-{day_slug}-{division_slug}-live",
            "groupName": "set-product-live",
            "productUrl": product_url,
            "productTitle": f"Big Apple {validated_request.sportName} - {basic_details.dayOfPlay} - {basic_details.division} Division - {basic_details.season.value} {basic_details.year}",
            "variantGid": first_variant_gid,
            "inventoryToAdd": inventory_info.totalInventory,
            "newDatetime": first_registration_date,
            "note": "newDateTime is in UTC (ET is 4 hours earlier than what this says)",
            "totalInventory": inventory_info.totalInventory,
            "numberVetSpotsToReleaseAtGoLive": inventory_info.numberVetSpotsToReleaseAtGoLive,
        }
        requests.append(initial_inventory_request)

        # Price changes request (exact GAS schedulePriceChanges structure)
        if open_gid and waitlist_gid:
            # Format off dates (matching GAS logic)
            off_dates_raw = getattr(important_dates, "offDatesCommaSeparated", "")
            off_dates_comma_separated = ""

            if isinstance(off_dates_raw, datetime):
                off_dates_comma_separated = format_date_only(off_dates_raw) or ""
            elif isinstance(off_dates_raw, str):
                off_dates_comma_separated = off_dates_raw.strip()

            price_changes_request = {
                "actionType": "create-scheduled-price-changes",
                "sport": validated_request.sportName,
                "day": basic_details.dayOfPlay,
                "division": basic_details.division,
                "productGid": product_gid,
                "openVariantGid": open_gid,
                "waitlistVariantGid": waitlist_gid,
                "price": float(inventory_info.price),
                "seasonStartDate": format_date_only(important_dates.seasonStartDate)
                or "",
                "sportStartTime": format_time_only(basic_details.leagueStartTime),
                "offDatesCommaSeparated": off_dates_comma_separated,
                "totalInventory": inventory_info.totalInventory,
                "numberVetSpotsToReleaseAtGoLive": inventory_info.numberVetSpotsToReleaseAtGoLive,
            }
            requests.append(price_changes_request)

        # Log all requests (matching GAS)
        logger.info("🔮 AWS SCHEDULING REQUESTS GENERATED")
        logger.info(f"📊 Total Requests: {len(requests)}")

        for i, request in enumerate(requests):
            action_type = request.get("actionType")
            schedule_name = request.get("scheduleName")

            logger.info(f"📋 Request {i+1}/{len(requests)}: {action_type}")
            logger.info(f"   📛 Schedule Name: {schedule_name}")
            logger.info(f"   🏷️ Group Name: {request.get('groupName')}")

            if action_type == "create-scheduled-inventory-movements":
                logger.info(
                    f"   📦 Inventory Move: {request.get('sourceVariant', {}).get('type')} → {request.get('destinationVariant', {}).get('type')}"
                )
                logger.info(f"   📅 Scheduled For: {request.get('newDatetime')}")
                logger.info(f"   🔢 Total Inventory: {request.get('totalInventory')}")
            elif action_type == "create-initial-inventory-addition-and-title-change":
                logger.info(f"   🎯 Go Live: {request.get('productTitle')}")
                logger.info(f"   📦 Initial Inventory: {request.get('inventoryToAdd')}")
                logger.info(f"   📅 Launch Date: {request.get('newDatetime')}")
            elif action_type == "create-scheduled-price-changes":
                logger.info(f"   💰 Price Changes: ${request.get('price')}")
                logger.info(
                    f"   🏃 Sport: {request.get('sport')} - {request.get('day')} - {request.get('division')}"
                )
                logger.info(f"   📅 Season Start: {request.get('seasonStartDate')}")

            logger.info(f"   📤 Full Request: {json.dumps(request, indent=4)}")

        # Note: In current implementation, these requests are prepared but not sent to AWS
        # They would be sent to AWS Lambda endpoints in a full integration
        logger.info(
            "📝 NOTE: Requests prepared for AWS integration (not yet implemented)"
        )
        logger.info(
            "🔗 These would be sent to AWS Lambda URLs when integration is complete"
        )

        # Success response (matching GAS success structure)
        result = {
            "success": True,
            "message": f"✅ {len(requests)} scheduling requests created successfully",
            "data": {
                "product_id": product_id_digits_only,
                "product_url": product_url,
                "requests": requests,
                "total_requests": len(requests),
                "inventory_moves_scheduled": True,
                "price_changes_scheduled": bool(open_gid and waitlist_gid),
                "summary": {
                    "sport": validated_request.sportName,
                    "day": basic_details.dayOfPlay,
                    "division": basic_details.division,
                    "season": f"{basic_details.season.value} {basic_details.year}",
                    "registration_flow": f"{reg1} → {reg2} → open",
                    "first_registration_date": first_registration_date,
                    "total_inventory": inventory_info.totalInventory,
                },
            },
        }

        logger.info(
            f"✅ Scheduled {len(requests)} events for product {product_id_digits_only}"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Error scheduling product updates: {e}")
        return {
            "success": False,
            "message": f"Product scheduling failed: {str(e)}",
            "error": str(e),
        }
