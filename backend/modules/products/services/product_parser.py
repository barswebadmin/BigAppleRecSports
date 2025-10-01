"""
Product Data Parser

Handles parsing of product data from webhooks, including title processing
and inventory checking for waitlist form integration.
"""

import re
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .text_cleaner import TextCleaner
from ../../../../config import config

logger = logging.getLogger(__name__)

def no_inventory_check_needed_reason(product_data: Dict[str, Any]) -> Optional[str]:
    """
    Check if product update should skip inventory processing.
    
    Returns:
        String reason for early exit if any condition is met, None otherwise
    """
    # Check if product is already marked as waitlist-only via tags
    tags_value = product_data.get("tags")
    tags_list: List[str] = []
    if isinstance(tags_value, list):
        tags_list = [str(t).strip().lower() for t in tags_value]
    elif isinstance(tags_value, str):
        # Shopify often sends tags as a comma-separated string
        tags_list = [t.strip().lower() for t in tags_value.split(",") if t.strip()]
    if "waitlist-only" in tags_list:
        try:
            # Log the raw webhook payload to validate waitlist-only state
            logger.info(f"🧾 Raw product webhook payload (waitlist-only detected): {json.dumps(product_data)[:4000]}")
        except Exception:
            logger.info("🧾 Raw product payload available but could not be serialized for logging")
        return "already_waitlisted"

    # Check if status is draft
    status = product_data.get("status", "").lower()
    if status == "draft":
        return "product status is draft"
    
    # Check if published_at is null
    published_at = product_data.get("published_at")
    if published_at is None:
        return "product is not published (published_at is null)"
    
    # Check if published_at is less than 24 hours ago
    try:
        if published_at:
            # Parse the published_at timestamp (Shopify format: "2025-09-16T23:59:29-04:00")
            # Handle both Z suffix and timezone offsets
            if published_at.endswith('Z'):
                published_datetime = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            else:
                published_datetime = datetime.fromisoformat(published_at)
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Convert published_datetime to UTC for comparison
            if published_datetime.tzinfo is None:
                # Assume UTC if no timezone info
                published_datetime = published_datetime.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                published_datetime = published_datetime.astimezone(timezone.utc)
            
            time_since_published = now - published_datetime
            hours_since_published = time_since_published.total_seconds() / 3600
            
            if hours_since_published < 24:
                return f"product was published recently ({hours_since_published:.1f} hours ago)"
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not parse published_at '{published_at}': {e}")
        # Don't early exit if we can't parse the date - let inventory check proceed
    
    return None

def has_zero_inventory(product_data: Dict[str, Any]) -> bool:
    """Check if all variants have zero inventory"""
    variants = product_data.get("variants", [])
    if not variants:
        return False
        
    for variant in variants:
        inventory_quantity = variant.get("inventory_quantity", 0)
        if inventory_quantity > 0:
            return False
    
    return True


def parse_for_waitlist_form(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Shopify webhook product data for waitlist form"""
    title = product_data.get("title", "")
    product_id = product_data.get("id", "")
    
    product_url = f"{config.Shopify.admin_url}/products/{product_id}"
    
    working_title = title.strip()
    working_title = re.sub(r'\bbig apple\b', '', working_title, flags=re.IGNORECASE).strip()
    
    current_year = datetime.now().year
    working_title = re.sub(r'\b(fall|spring|summer|winter)\b', '', working_title, flags=re.IGNORECASE)
    
    year_patterns = [
        str(current_year), str(current_year + 1), str(current_year - 1),
        str(current_year % 100), str((current_year + 1) % 100), str((current_year - 1) % 100)
    ]
    for year in year_patterns:
        working_title = re.sub(r'\b' + re.escape(year) + r'\b', '', working_title, flags=re.IGNORECASE)
    
    working_title = TextCleaner.clean_title_formatting(working_title)
    
    # Check if we have all required components (sport, day, division) in the title
    # If not, return as other_identifier immediately
    sports = ["dodgeball", "kickball", "pickleball", "bowling"]
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    divisions = ["wtnb+", "wtnb", "open"]
    
    has_sport = any(re.search(r'\b' + re.escape(sport) + r'\b', working_title, re.IGNORECASE) for sport in sports)
    has_multi_sport = re.search(r'\b(kickball|dodgeball|pickleball|bowling)\s+and\s+(kickball|dodgeball|pickleball|bowling)\b', working_title, re.IGNORECASE)
    has_day = any(re.search(r'\b' + re.escape(day) + r'\b', working_title, re.IGNORECASE) for day in days)
    has_division = any(
        re.search(r'\bwtnb\+', working_title, re.IGNORECASE) if division == "wtnb+" else
        re.search(r'\b' + re.escape(division) + r'\b', working_title, re.IGNORECASE)
        for division in divisions
    )
    
    if not ((has_sport or has_multi_sport) and has_day and has_division):
        return {
            "product_url": product_url,
            "sport": None,
            "day": None,
            "division": None,
            "other_identifier": working_title if working_title else None
        }
    
    result = {
        "product_url": product_url,
        "sport": None,
        "day": None, 
        "division": None,
        "other_identifier": None
    }
    
    # Multi-sport pattern: "Kickball and Dodgeball"
    multi_sport_pattern = r'\b(kickball|dodgeball|pickleball|bowling)\s+and\s+(kickball|dodgeball|pickleball|bowling)\b'
    multi_sport_match = re.search(multi_sport_pattern, working_title, re.IGNORECASE)
    
    if multi_sport_match:
        sport1, sport2 = multi_sport_match.groups()
        result["sport"] = f"{sport1.title()} and {sport2.title()}"
        working_title = working_title[:multi_sport_match.start()] + working_title[multi_sport_match.end():]
        working_title = TextCleaner.clean_title_formatting(working_title)
    else:
        sports = ["dodgeball", "kickball", "pickleball", "bowling"]
        sport_matches = []
        
        for sport in sports:
            matches = list(re.finditer(r'\b' + re.escape(sport) + r'\b', working_title, re.IGNORECASE))
            sport_matches.extend([(match, sport) for match in matches])
        
        if sport_matches:
            sport_matches.sort(key=lambda x: x[0].start())
            
            if len(sport_matches) == 1:
                match, sport = sport_matches[0]
                result["sport"] = sport.title()
                working_title = working_title[:match.start()] + working_title[match.end():]
            else:
                first_match = sport_matches[0][0]
                last_match = sport_matches[-1][0]
                result["sport"] = sport_matches[0][1].title()
                working_title = working_title[:first_match.start()] + working_title[last_match.end():]
            
            working_title = TextCleaner.clean_title_formatting(working_title)
        else:
            result["other_identifier"] = working_title if working_title else None
            return result
    
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_matches = []
    
    for day in days:
        matches = list(re.finditer(r'\b' + re.escape(day) + r'\b', working_title, re.IGNORECASE))
        day_matches.extend([(match, day) for match in matches])
    
    if day_matches:
        day_matches.sort(key=lambda x: x[0].start())
        
        if len(day_matches) == 1:
            match, day = day_matches[0]
            result["day"] = day.title()
            working_title = working_title[:match.start()] + working_title[match.end():]
        else:
            first_match = day_matches[0][0]
            last_match = day_matches[-1][0]
            result["day"] = day_matches[0][1].title()
            working_title = working_title[:first_match.start()] + working_title[last_match.end():]
        
        working_title = TextCleaner.clean_title_formatting(working_title)
    else:
        result["other_identifier"] = working_title if working_title else None
        return result
    
    # Check wtnb+ before wtnb to avoid partial matches
    divisions = ["wtnb+", "wtnb", "open"]
    
    for division in divisions:
        if division == "wtnb+":
            # Special regex for wtnb+ since + is not a word character
            pattern = r'\bwtnb\+'
        else:
            pattern = r'\b' + re.escape(division) + r'\b'
        match = re.search(pattern, working_title, re.IGNORECASE)
        if match:
            if division == "open":
                result["division"] = "Open"
            elif division == "wtnb+":
                result["division"] = "WTNB+"
            else:
                result["division"] = division.lower()
            
            working_title = working_title[:match.start()] + working_title[match.end():]
            working_title = re.sub(r'\bdivision\b', '', working_title, flags=re.IGNORECASE)
            working_title = TextCleaner.clean_title_formatting(working_title)
            break
    
    if working_title and re.search(r'[a-zA-Z0-9]', working_title):
        result["other_identifier"] = working_title
    
    return result

def get_slack_group_mention(product_tags: Optional[str]) -> Optional[str]:
    """Get Slack group mention for product tags.
    Accepts either a comma-separated string or a list of strings.
    """
    if not product_tags:
        return None
    for tag in product_tags.split(","):
        try:
            if isinstance(tag, str) and tag.strip().startswith("slackGroup"):
                parts = tag.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip()
        except Exception:
            continue
    return None