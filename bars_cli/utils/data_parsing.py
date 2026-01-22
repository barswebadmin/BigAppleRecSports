"""Data parsing utilities for dates, prices, amounts, and HTML."""

import re
from datetime import datetime, timezone
from typing import Optional


def extract_price_from_html(description_html: str) -> Optional[float]:
    """
    Extract price from descriptionHtml.
    Looks for "Price" followed by text until ':', then finds first number (possibly after '$').
    Follows the numerical string until there's something that's not a decimal or digit.
    
    Args:
        description_html: HTML description text
        
    Returns:
        Price as float, or None if not found
    """
    if not description_html:
        return None
    
    # Find "Price" followed by any text until ':'
    # Then find first number (possibly after '$'), following digits and decimals
    price_pattern = r'Price[^:]*:\s*[^0-9\$]*\$?\s*(\d+\.?\d*)'
    match = re.search(price_pattern, description_html, re.IGNORECASE)
    
    if match:
        try:
            price_str = match.group(1)
            # Extract only digits and decimal point (stop at first non-digit/non-decimal)
            price_clean = re.match(r'(\d+\.?\d*)', price_str)
            if price_clean:
                return float(price_clean.group(1))
        except (ValueError, IndexError):
            pass
    
    # Fallback: More flexible pattern
    price_pattern_fallback = r'Price[^:]*:\s*[^0-9]*(\d+(?:\.\d+)?)'
    match = re.search(price_pattern_fallback, description_html, re.IGNORECASE)
    
    if match:
        try:
            price_str = match.group(1)
            return float(price_str)
        except (ValueError, IndexError):
            pass
    
    return None


def parse_order_date(created_at: str) -> Optional[datetime]:
    """
    Parse order date from createdAt column.
    
    Args:
        created_at: Date string (various formats supported)
        
    Returns:
        datetime object, or None if parsing fails
    """
    if not created_at:
        return None
    
    # Try common date formats
    date_formats = [
        '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
        '%Y-%m-%dT%H:%M:%S.%f%z',  # ISO format with microseconds
        '%Y-%m-%dT%H:%M:%S',  # ISO format without timezone
        '%Y-%m-%d %H:%M:%S',  # Standard format
        '%Y-%m-%d',  # Date only
        '%m/%d/%Y',  # US format
        '%m/%d/%y',  # US format with 2-digit year
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(created_at.strip(), fmt)
            # Make timezone-aware if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    return None


def parse_total_paid(total_paid: str) -> Optional[float]:
    """
    Parse total paid amount from string.
    
    Args:
        total_paid: Amount string (may include $, commas, etc.)
        
    Returns:
        Float value, or None if parsing fails
    """
    if not total_paid:
        return None
    
    # Remove $, commas, and whitespace
    cleaned = re.sub(r'[\$,\s]', '', str(total_paid))
    
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_total_refunded(total_refunded: str) -> Optional[float]:
    """
    Parse total refunded amount from string.
    
    Args:
        total_refunded: Amount string (may include $, commas, etc.)
        
    Returns:
        Float value, or None if parsing fails (defaults to 0.0 if empty)
    """
    if not total_refunded:
        return 0.0
    
    # Remove $, commas, and whitespace
    cleaned = re.sub(r'[\$,\s]', '', str(total_refunded))
    
    # Handle empty string after cleaning
    if not cleaned or cleaned == '':
        return 0.0
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
