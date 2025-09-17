"""
Product Data Parser

Handles parsing of product data from webhooks, including title processing
and inventory checking for waitlist form integration.
"""

import re
from datetime import datetime
from typing import Dict, Any
from .text_cleaner import TextCleaner
from config import config


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
    
    product_url = f"{config.shopify_admin_url}/products/{product_id}"
    
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
