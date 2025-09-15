"""
Product creation service - matching Create Product From Row.gs structure
"""

import logging
from typing import Dict, Any, Union
from datetime import datetime
from models.products.product_creation_request import ProductCreationRequest
from services.shopify.shopify_service import ShopifyService
from utils.date_utils import (
    format_date_only,
    format_date_and_time,
    format_league_play_times,
)
from .enable_inventory_tracking import enable_inventory_tracking

logger = logging.getLogger(__name__)


def format_date_for_display(date_value: Union[str, datetime, None]) -> str:
    """Format a date value for display in Eastern time, handling both string and datetime types"""
    if not date_value:
        return "TBD"

    # If it's already a string that looks like a placeholder, return it as-is
    if isinstance(date_value, str):
        # Common placeholder strings that should be preserved
        placeholder_strings = ["TBD", "tbd", "unknown", "n/a", "na", "pending", ""]
        if date_value.lower().strip() in placeholder_strings:
            return "TBD"

        # If it looks like a user-friendly date string (not ISO), preserve it
        # Only try to format if it looks like a proper ISO datetime
        if not ("T" in date_value or "Z" in date_value or "+" in date_value[-6:]):
            logger.warning(f"Preserving user-provided date string: {date_value}")
            return date_value

    # Use the date_utils function which handles timezone conversion to ET
    try:
        formatted_result = format_date_and_time(date_value)
        # Check if the formatting failed and returned the error message
        if formatted_result == "Unknown Date/Time":
            logger.warning(
                f"Date formatting failed for: {date_value}, preserving original"
            )
            return str(date_value) if date_value else "TBD"
        return formatted_result.replace(" at ", " at ")
    except Exception as e:
        logger.warning(
            f"Exception formatting date {date_value}: {e}, preserving original"
        )
        # Fallback to string representation if formatting fails
        return str(date_value) if date_value else "TBD"


def validate_important_dates(important_dates) -> Dict[str, Any]:
    """Validate important dates for proper formatting and detect problematic values"""
    issues = []
    warnings = []

    date_fields = [
        ("seasonStartDate", important_dates.seasonStartDate),
        ("seasonEndDate", important_dates.seasonEndDate),
        ("vetRegistrationStartDateTime", important_dates.vetRegistrationStartDateTime),
        (
            "earlyRegistrationStartDateTime",
            important_dates.earlyRegistrationStartDateTime,
        ),
        (
            "openRegistrationStartDateTime",
            important_dates.openRegistrationStartDateTime,
        ),
        (
            "newPlayerOrientationDateTime",
            getattr(important_dates, "newPlayerOrientationDateTime", None),
        ),
        ("scoutNightDateTime", getattr(important_dates, "scoutNightDateTime", None)),
        ("openingPartyDate", getattr(important_dates, "openingPartyDate", None)),
        ("rainDate", getattr(important_dates, "rainDate", None)),
        ("closingPartyDate", getattr(important_dates, "closingPartyDate", None)),
    ]

    for field_name, field_value in date_fields:
        if field_value is not None:
            if isinstance(field_value, str):
                # Check for problematic string values
                if field_value.lower().strip() in [
                    "tbd",
                    "unknown",
                    "n/a",
                    "na",
                    "pending",
                ]:
                    warnings.append(
                        f"{field_name}: '{field_value}' will be displayed as 'TBD'"
                    )
                elif not (
                    "T" in field_value or "Z" in field_value or "+" in field_value[-6:]
                ):
                    # It's a non-ISO string - might be a user-friendly format or error
                    warnings.append(
                        f"{field_name}: '{field_value}' is not in ISO format and will be preserved as-is"
                    )
                else:
                    # Try to validate it can be parsed
                    try:
                        from utils.date_utils import parse_shopify_datetime

                        parsed = parse_shopify_datetime(field_value)
                        if parsed is None:
                            issues.append(
                                f"{field_name}: '{field_value}' cannot be parsed as a valid date"
                            )
                    except Exception as e:
                        issues.append(
                            f"{field_name}: '{field_value}' parsing failed: {str(e)}"
                        )

    return {"has_issues": len(issues) > 0, "issues": issues, "warnings": warnings}


def create_product(validated_request: ProductCreationRequest) -> Dict[str, Any]:
    """
    Create a Shopify product matching the structure from Create Product From Row.gs

    Returns the same format as the GAS version for compatibility with sendProductInfoToBackendForCreation
    """
    from config import settings

    basic_details = validated_request.regularSeasonBasicDetails
    important_dates = validated_request.importantDates
    optional_league_info = getattr(validated_request, "optionalLeagueInfo", None)

    # Validate important dates before creating the product
    date_validation = validate_important_dates(important_dates)
    if date_validation["has_issues"]:
        logger.error(f"Date validation failed: {date_validation['issues']}")
        return {
            "success": False,
            "error": "Invalid date format(s) detected",
            "message": f"Date validation failed: {'; '.join(date_validation['issues'])}",
            "details": {
                "issues": date_validation["issues"],
                "warnings": date_validation["warnings"],
            },
        }

    # Log warnings but continue if only warnings exist
    if date_validation["warnings"]:
        for warning in date_validation["warnings"]:
            logger.warning(f"Date validation warning: {warning}")

    # For development/testing mode when Shopify credentials aren't available
    if not settings.shopify_token:
        logger.warning("No Shopify token available - returning mock data for testing")
        mock_product_id = "8123456789012345678"
        mock_variant_id = "gid://shopify/ProductVariant/45123456789012345678"

        return {
            "success": True,
            "data": {
                "product_gid": f"gid://shopify/Product/{mock_product_id}",
                "product_id": mock_product_id,
                "productUrl": f"https://admin.shopify.com/store/09fe59-3/products/{mock_product_id}",
                "product_title": f"{validated_request.sportName} {basic_details.division} {basic_details.dayOfPlay} League - {basic_details.season} {basic_details.year}",
                "first_variant_gid": mock_variant_id,
            },
        }

    # Create Shopify service instance
    shopify_service = ShopifyService()

    # Get sport-specific image URL (matching GAS function exactly)
    def get_image_url(sport: str) -> str:
        image_mapping = {
            "Bowling": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/BARS_BowlingCrest_2025.png?v=1744213239",
            "Dodgeball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/AF92B4C5-5AA4-4B40-8774-F42937B7C631.png?v=1743883324",
            "Kickball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Kickball_Open.png?v=1744224266",
            "Pickleball": "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/BARS_PickleballCrest_2025.png?v=1744213148",
        }
        return image_mapping.get(sport, "")

    def get_sport_email_address(sport: str) -> str:
        return f"<a href='mailto:{sport.lower()}@bigapplerecsports.com' style='color:blue'>{sport.lower()}@bigapplerecsports.com</a>"

    # Extract enum values first for reuse
    sport_name_value = (
        validated_request.sportName.value
        if hasattr(validated_request.sportName, "value")
        else str(validated_request.sportName)
    )
    day_of_play_value = (
        basic_details.dayOfPlay.value
        if hasattr(basic_details.dayOfPlay, "value")
        else str(basic_details.dayOfPlay)
    )
    season_value = (
        basic_details.season.value
        if hasattr(basic_details.season, "value")
        else str(basic_details.season)
    )
    division_value = (
        basic_details.division.value
        if hasattr(basic_details.division, "value")
        else str(basic_details.division)
    )

    # Build product handle (exact match to GAS)
    division_value_for_handle = (
        division_value.lower().split("+")[0] if division_value else "open"
    )
    handle = f"{basic_details.year}-{season_value.lower()}-{sport_name_value.lower()}-{day_of_play_value.lower()}-{division_value_for_handle}div"

    # Build product title (exact match to GAS)
    title = f"Big Apple {sport_name_value} - {day_of_play_value} - {division_value} Division - {season_value} {basic_details.year} (*Registration Not Yet Open - Please scroll down to description for dates*)"

    # Build description HTML (matching GAS structure exactly)
    # Convert enum values to their string representations
    day_all_caps = day_of_play_value.upper()
    sport_all_caps = sport_name_value.upper()

    sport_sub_category = (
        getattr(optional_league_info, "sportSubCategory", "")
        if optional_league_info
        else ""
    )
    sport_sub_category_value = getattr(
        sport_sub_category,
        "value",
        str(sport_sub_category) if sport_sub_category else "",
    )
    sport_sub_category_all_caps = (
        sport_sub_category_value.upper()
        if sport_sub_category_value and sport_sub_category_value != "N/A"
        else ""
    )

    social_or_advanced = (
        getattr(optional_league_info, "socialOrAdvanced", "")
        if optional_league_info
        else ""
    )
    social_or_advanced_value = getattr(
        social_or_advanced,
        "value",
        str(social_or_advanced) if social_or_advanced else "",
    )

    types_list = (
        getattr(optional_league_info, "types", []) if optional_league_info else []
    )
    # Convert enum values in types list to their string representations
    types_values = []
    for t in types_list:
        if hasattr(t, "value"):
            types_values.append(t.value)
        else:
            types_values.append(str(t))
    types_comma_separated = ", ".join(types_values) if types_values else ""

    # Build optional sections (matching GAS conditionals)
    new_player_orientation = getattr(
        important_dates, "newPlayerOrientationDateTime", None
    )
    scout_night = getattr(important_dates, "scoutNightDateTime", None)
    opening_party = getattr(important_dates, "openingPartyDate", None)
    rain_date = getattr(important_dates, "rainDate", None)
    closing_party = getattr(important_dates, "closingPartyDate", None)
    vet_registration = getattr(important_dates, "vetRegistrationStartDateTime", None)

    # Format optional date sections (exact GAS match)
    new_player_section = (
        f"<li><p><strong><span>New Player Orientation Date</span></strong><span>: {format_date_for_display(new_player_orientation)}</span></p></li>"
        if new_player_orientation
        else ""
    )
    scout_night_section = (
        f"<li><p><strong><span>Scout Night Date</span></strong><span>: {format_date_for_display(scout_night)}</span></p></li>"
        if scout_night
        else ""
    )
    opening_party_section = (
        f"<li><p><strong><span>Opening Party Date</span></strong><span>: {format_date_for_display(opening_party)}</span></p></li>"
        if opening_party
        else ""
    )
    rain_date_section = (
        f"<li><p><strong><span>Rain Date (played if a regular season date gets rained out)</span></strong><span>: {format_date_for_display(rain_date)}</span></p></li>"
        if rain_date
        else ""
    )
    closing_party_section = (
        f'<li><p><strong><span>Closing Party Date{"(tentative, depending on rain date)" if validated_request.sportName.lower() == "kickball" else ""}</span></strong><span>: {format_date_for_display(closing_party)}</span></p></li>'
        if closing_party
        else ""
    )

    # Get off dates and weeks
    off_dates_str = getattr(important_dates, "offDatesCommaSeparated", "")
    num_weeks = getattr(basic_details, "numOfWeeks", "")

    # WTNB+ and Social intro section (matching GAS logic)
    intro_section = ""
    if division_value == "WTNB+" or social_or_advanced_value == "Social":
        intro_parts = []
        if division_value == "WTNB+":
            intro_parts.append(
                "Open to <u>women, trans, and non-binary identifying players</u> of all skill levels."
            )
        if social_or_advanced_value == "Social":
            intro_parts.append(
                "While matches will be scored and season standings recorded, this league will stress the social aspect of the sport over competitiveness."
            )

        if intro_parts:
            intro_section = f'<p>{" ".join(intro_parts)}</p>'

    # Vet registration section (exact GAS match)
    vet_section = ""
    if vet_registration:
        vet_section = f"""<li>
                    <p>
                      <span><b>Vet Registration:</b> {format_date_for_display(vet_registration)}
                        <br/><small>(Vet status is earned by missing <i>no more</i> than the <b>greater of 25% or 2 weeks</b> of the <i>most recent season</i> of that sport/day/division. Vet status cannot be transferred between players or between different sports/days. All players who are eligible to register during the Veteran Registration period will be notified in advance by email.)</small>
                      </span>
                    </p>
                  </li>"""

    # Alternative time section
    alternative_start = getattr(basic_details, "alternativeStartTime", None)
    alternative_end = getattr(basic_details, "alternativeEndTime", None)
    alt_time_text = ""
    if alternative_start and alternative_end:
        alt_time_formatted = format_league_play_times(
            str(alternative_start), str(alternative_end)
        )
        alt_time_text = f" (and sometimes {alt_time_formatted}, varies each week)"

    # Build complete description HTML (exact GAS structure)
    description_html = f"""<p></p>
              <h1>{day_all_caps} {sport_sub_category_all_caps} {sport_all_caps}</h1>
              <p></p>
              <h1>{division_value} Division {f'({social_or_advanced_value})' if social_or_advanced_value else ''}</h1>
              <p><br/></p>

              {intro_section}

              <p><h2><span>LEAGUE DETAILS:</span></h2></p>
              <ul>
                <li>
                  <p><span><strong>Type</strong>: {'Created for our Women/Trans/Non-Binary (WTNB+) Community, ' if division_value == 'WTNB+' else ''}{social_or_advanced_value}{', ' + types_comma_separated if types_comma_separated else ''}</span></p>
                </li>
                {new_player_section}
                {scout_night_section}
                {opening_party_section}
                <li>
                  <p><strong><span>Season Dates</span></strong><span>: {format_date_only(important_dates.seasonStartDate) or 'TBD'} – {format_date_only(important_dates.seasonEndDate) or 'TBD'} ({num_weeks} weeks{f', off {off_dates_str}' if off_dates_str else ''})</span></p>
                  <ul><li>
                    <p><span><strong>League Day/Time:</strong> {day_of_play_value.capitalize()} {format_league_play_times(basic_details.leagueStartTime, basic_details.leagueEndTime)}{alt_time_text}</span></p>
                  </li></ul>
                </li>{rain_date_section}
                {closing_party_section}
                <li>
                  <p><span><strong>Location:</strong> {basic_details.location}</span></p>
                </li>
                <li>
                  <p><span><strong>Price</strong>: ${validated_request.inventoryInfo.price}</span></p>
                </li>

              </ul>
              <br/>

              <p><h2><span>REGISTRATION DATES/TIMES:</span></h2></p>
              <ul>
                {vet_section}
                <li>
                  <p>
                    <span><b>{'W' if basic_details.division == 'Open' else ''}TNB+ &amp; BIPOC Early Registration</b>: {format_date_for_display(getattr(important_dates, 'earlyRegistrationStartDateTime', None))}</span>
                  </p>
                </li>
                <li>
                  <p>
                    <span><b>Open Registration:</b> {format_date_for_display(getattr(important_dates, 'openRegistrationStartDateTime', None))}</span>
                  </p>
                </li>
                <li><b>**Notes**:</b>
                  <ul>
                    <li>You will only be able to add the product to your cart on the corresponding dates and times above</li>
                    <li>Registration takes place entirely online - please don't show up to the location in person when trying to register (you don't need to!)</li>
                  </ul>
                </li>
              </ul>
              <hr/>

              <p>By participating in any sport or event operated by BARS, players agree to the following:</p>
              <ul>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Waiver.pdf?v=1704060897' target='_blank' style='color:blue'>Waiver</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Terms_of_Participation.pdf?v=1704060897' target='_blank' style='color:blue'>Terms of Participation</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Player_Participation_Policies.pdf?v=1704060897' target='_blank' style='color:blue'>Player Participation Policies</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/ADA_Policy_With_No_Signature.docx.pdf?v=1704060738' target='_blank' style='color:blue'>Americans with Disabilities Act (ADA) Policy</a></u>
                </li>
                <li>
                  <u><a href='https://cdn.shopify.com/s/files/1/0554/7553/5966/files/Harassment_Discrimination_and_Bullying_Policy.pdf?v=1702339211' target='_blank' style='color:blue'>Harassment, Bullying, and Discrimination Policy</a></u>
                </li>
              </ul>

              <p>Have questions? Email {get_sport_email_address(validated_request.sportName)}</p>"""

    # Build GraphQL query (exact match to GAS structure)
    query = {
        "query": f"""mutation {{
          productCreate(
            media: [
              {{
                mediaContentType: IMAGE,
                originalSource: "{get_image_url(validated_request.sportName)}"
              }}
            ],
            product: {{
              handle: "{handle}",
              title: "{title}",
              status: ACTIVE,
              category: "gid://shopify/TaxonomyCategory/sg-4",
              tags: ["{validated_request.sportName}", "{'WTNB' if basic_details.division == 'WTNB+' else basic_details.division} Division"],
              descriptionHtml: "{description_html.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')}"
            }}) {{
            product {{
              id
              title
            }}
            userErrors {{
              field
              message
            }}
          }}
        }}"""
    }

    try:
        logger.info("🚀 Sending product creation request to Shopify")
        response = shopify_service._make_shopify_request(query)

        if response is None:
            logger.error("❌ No response received from Shopify")
            return {
                "success": False,
                "error": "Failed to create product",
                "step_failed": "shopify_request",
                "details": "No response received from Shopify API",
            }

        # Check if response contains engineering error information
        if isinstance(response, dict) and "error" in response:
            error_type = response.get("error_type", "unknown")
            engineering_note = response.get("engineering_note", "")

            logger.error(
                f"❌ Shopify request failed: {response.get('message', 'Unknown error')}"
            )
            if engineering_note:
                logger.error(f"🔧 Engineering note: {engineering_note}")

            return {
                "success": False,
                "error": f"Shopify API error: {response.get('message', 'Unknown error')}",
                "step_failed": "shopify_request",
                "details": f"Error type: {error_type}. {engineering_note}",
                "error_type": error_type,
            }

        # Log the actual response for debugging
        logger.info(
            f"📥 Shopify response received: {type(response)} with keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}"
        )

        # Check for GraphQL errors first
        if response.get("errors"):
            logger.error(f"Shopify GraphQL errors: {response['errors']}")
            return {
                "success": False,
                "error": f"Shopify GraphQL errors: {response['errors']}",
            }

        product_create_data = response.get("data", {}).get("productCreate", {})
        user_errors = product_create_data.get("userErrors", [])

        if user_errors:
            logger.error(f"Shopify user errors: {user_errors}")
            return {"success": False, "error": f"Shopify errors: {user_errors}"}

        product = product_create_data.get("product", {})
        if not product:
            logger.error(
                f"❌ No product data returned from Shopify. ProductCreate response: {product_create_data}"
            )
            return {
                "success": False,
                "error": "Product creation failed: No product data returned",
            }

        product_gid = product.get("id")
        product_id_digits_only = product_gid.split("/")[-1] if product_gid else ""
        product_url = (
            f"https://admin.shopify.com/store/09fe59-3/products/{product_id_digits_only}"
            if product_id_digits_only
            else ""
        )

        logger.info(f"✅ Product created: {product_gid}")
        if product.get("title"):
            logger.info(f"📝 Title: {product.get('title')}")

        # Get first variant GID (auto-created with product)
        variant_query = {
            "query": f"""
                query {{
                    product(id: "{product_gid}") {{
                        variants(first: 1) {{
                            nodes {{ id }}
                        }}
                    }}
                }}"""
        }

        variant_response = shopify_service._make_shopify_request(variant_query)

        first_variant_gid = None
        if variant_response and variant_response.get("data", {}).get("product", {}).get(
            "variants", {}
        ).get("nodes"):
            first_variant_gid = variant_response["data"]["product"]["variants"][
                "nodes"
            ][0]["id"]

        # Update variant settings (tax, shipping) - matching GAS updateVariantSettings
        if first_variant_gid:
            logger.info(f"🔧 Updating variant settings: {first_variant_gid}")
            variant_update_data = {"taxable": False, "requires_shipping": False}
            update_result = shopify_service.update_variant_rest(
                first_variant_gid, variant_update_data
            )

            if update_result.get("success"):
                logger.info("✅ Variant settings updated")
            else:
                logger.warning(f"⚠️ Variant update failed: {update_result.get('error')}")

            # Enable inventory tracking - matching GAS enableInventoryTracking
            logger.info("📦 Enabling inventory tracking")
            inventory_result = enable_inventory_tracking(
                first_variant_gid, shopify_service
            )

            if inventory_result.get("success"):
                logger.info("✅ Inventory tracking enabled")
            else:
                logger.warning(
                    f"⚠️ Inventory tracking failed: {inventory_result.get('error')}"
                )

            if not inventory_result.get("success"):
                logger.warning(
                    f"⚠️ Failed to enable inventory tracking: {inventory_result.get('error')}"
                )
        else:
            logger.warning("⚠️ No variant GID found - skipping variant updates")

        logger.info(f"Successfully created product with GID: {product_gid}")

        return {
            "success": True,
            "data": {
                "product_gid": product_gid,
                "product_id": product_id_digits_only,
                "productUrl": product_url,  # Match GAS key name
                "product_title": product.get("title"),
                "first_variant_gid": first_variant_gid,
            },
        }

    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        return {"success": False, "error": str(e)}
