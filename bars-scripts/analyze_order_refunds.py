#!/usr/bin/env python3
"""
Analyze CSV orders to determine refund eligibility based on discount calculator logic.

This script:
1. Reads a CSV file with order data
2. Extracts Price and Season Dates from descriptionHtml
3. Calculates discounted price based on order date vs season start date
4. Determines if a refund is due (if totalPaid > discountedPrice)

Usage:
    python bars-scripts/analyze_order_refunds.py input.csv
    python bars-scripts/analyze_order_refunds.py input.csv --output output.csv
"""

import sys
import argparse
import csv
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from html import unescape

# Add shared-utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared-utilities" / "src"))

try:
    from utils.discount_calculator import calculate_discounted_price
except ImportError:
    # Fallback: Embed the discount calculator logic directly
    import logging
    logger = logging.getLogger(__name__)
    
    def create_discount_amount(
        season_start_date_str: str,
        off_dates_str: Optional[str],
        total_amount_paid: float,
        request_submitted_at: Optional[datetime] = None,
    ) -> Tuple[float, str]:
        """Calculate discount amount based on timing and season dates (embedded version)."""
        try:
            if not season_start_date_str or not total_amount_paid:
                return (0, "Error calculating discount - please check season dates and amount")
            
            if total_amount_paid == 0:
                return 0, "Discount Amount: $0 (No payment was made for this order)"
            
            # Ensure request_submitted_at is timezone-aware
            if request_submitted_at is None:
                request_submitted_at = datetime.now(timezone.utc)
            elif request_submitted_at.tzinfo is None:
                request_submitted_at = request_submitted_at.replace(tzinfo=timezone.utc)
            
            # Parse season start date and make it timezone-aware (UTC)
            month, day, year = map(int, season_start_date_str.split("/"))
            normalized_year = year if year >= 100 else 2000 + year
            season_start_date = datetime(
                normalized_year, month, day, 7, 0, 0, tzinfo=timezone.utc
            )
            
            # Create week dates (5 weeks starting from season start)
            week_dates = [season_start_date]
            for i in range(1, 5):
                next_week_timestamp = week_dates[i - 1].timestamp() + (7 * 24 * 60 * 60)
                next_week = datetime.fromtimestamp(next_week_timestamp, tz=timezone.utc)
                week_dates.append(next_week)
            
            # Parse off dates and adjust week dates
            if off_dates_str:
                off_dates = []
                for date_str in off_dates_str.split(","):
                    date_str = date_str.strip()
                    if date_str and "/" in date_str:
                        try:
                            m, d, y = map(int, date_str.split("/"))
                            normalized_year = y if y >= 100 else 2000 + y
                            off_date = datetime(
                                normalized_year, m, d, 7, 0, 0, tzinfo=timezone.utc
                            )
                            off_dates.append(off_date)
                        except ValueError:
                            continue
                
                # Adjust week dates by shifting subsequent weeks for each off date
                for off_date in sorted(off_dates):
                    for i in range(len(week_dates)):
                        if week_dates[i] == off_date:
                            for j in range(i, len(week_dates)):
                                shift_timestamp = week_dates[j].timestamp() + (7 * 24 * 60 * 60)
                                week_dates[j] = datetime.fromtimestamp(shift_timestamp, tz=timezone.utc)
                            break
            
            # Define discount tiers
            discount_percentages = [0, 15, 25, 35, 45, 55]
            discount_percentage = 0
            week_index = 0
            
            # Find appropriate discount tier
            if request_submitted_at < week_dates[0]:
                discount_percentage = discount_percentages[0]
                week_index = 0
            else:
                for i in range(len(week_dates)):
                    week_date = week_dates[i]
                    if i == len(week_dates) - 1 or request_submitted_at < week_dates[i + 1]:
                        if request_submitted_at >= week_date:
                            week_index = i + 1
                            if week_index < len(discount_percentages):
                                discount_percentage = discount_percentages[week_index]
                            else:
                                discount_percentage = discount_percentages[-1]
                        break
            
            discount_amount = (discount_percentage / 100) * total_amount_paid
            return discount_amount, f"Discount: {discount_percentage}%"
        
        except Exception as e:
            return 0, f"Error calculating discount amount: {str(e)}"
    
    def calculate_discounted_price(
        original_price: float,
        season_start_date_str: str,
        off_dates_str: Optional[str] = None,
        request_submitted_at: Optional[datetime] = None,
    ) -> Tuple[float, float, str]:
        """Calculate discounted price (embedded version)."""
        discount_amount, discount_text = create_discount_amount(
            season_start_date_str, off_dates_str, original_price, request_submitted_at
        )
        final_price = original_price - discount_amount
        return final_price, discount_amount, discount_text


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


def extract_season_start_date_from_html(description_html: str) -> Optional[str]:
    """
    Extract season start date from descriptionHtml.
    Looks for "Season Dates" followed by any text until ':', then parses the first date.
    Strips HTML tags to handle cases where tags are inserted in the middle of dates.
    
    Args:
        description_html: HTML description text
        
    Returns:
        Date string in MM/DD/YY format, or None if not found
    """
    if not description_html:
        return None
    
    # Strip HTML tags to handle cases where tags are inserted in dates
    # This handles cases like "1<meta...>0/14/25" becoming "10/14/25"
    text_without_tags = re.sub(r'<[^>]+>', '', description_html)
    # Also decode HTML entities
    text_clean = unescape(text_without_tags)
    
    # Find "Season Dates" followed by any text until ':'
    # Then find the next set of numbers and slashes (date pattern)
    # Allow for whitespace and non-digit characters between digits (handles HTML remnants)
    season_pattern = r'Season\s+Dates[^:]*:\s*(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{2,4})'
    match = re.search(season_pattern, text_clean, re.IGNORECASE)
    
    if match:
        date_str = match.group(1)
        # Clean up whitespace and normalize
        date_str = re.sub(r'\s+', '', date_str)  # Remove all whitespace
        # Normalize to MM/DD/YY format
        parts = date_str.split('/')
        if len(parts) == 3:
            month, day, year = parts
            # Convert YYYY to YY if needed
            if len(year) == 4:
                year = year[-2:]
            return f"{month}/{day}/{year}"
    
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


def analyze_order(row: Dict[str, str], headers: List[str]) -> Dict[str, Any]:
    """
    Analyze a single order row to determine refund eligibility.
    
    Args:
        row: Dictionary of row data
        headers: List of column headers
        
    Returns:
        Dictionary with analysis results
    """
    result = {
        'order_number': row.get('Order Number', row.get('orderName', '')),
        'original_price': None,
        'season_start_date': None,
        'order_date': None,
        'total_paid': None,
        'total_refunded': None,
        'net_paid': None,
        'discounted_price': None,
        'discount_amount': None,
        'refund_due': None,
        'refund_amount': None,
        'error': None,
    }
    
    # Get descriptionHtml
    description_html = row.get('descriptionHtml', row.get('Description HTML', ''))
    if not description_html:
        result['error'] = 'Missing descriptionHtml'
        return result
    
    # Extract price
    original_price = extract_price_from_html(description_html)
    if original_price is None:
        result['error'] = 'Could not extract price from descriptionHtml'
        return result
    result['original_price'] = original_price
    
    # Extract season start date
    season_start_date = extract_season_start_date_from_html(description_html)
    if season_start_date is None:
        result['error'] = 'Could not extract season start date from descriptionHtml'
        return result
    result['season_start_date'] = season_start_date
    
    # Parse order date
    created_at = row.get('createdAt', row.get('Created At', row.get('Order Date', '')))
    order_date = parse_order_date(created_at)
    if order_date is None:
        result['error'] = f'Could not parse order date: {created_at}'
        return result
    result['order_date'] = order_date.isoformat()
    
    # Parse total paid
    total_paid_str = row.get('Total Paid', row.get('totalPaid', row.get('Total price', '')))
    total_paid = parse_total_paid(total_paid_str)
    if total_paid is None:
        result['error'] = f'Could not parse total paid: {total_paid_str}'
        return result
    result['total_paid'] = total_paid
    
    # Parse total refunded (defaults to 0.0 if not found or empty)
    total_refunded_str = row.get('totalRefunded', row.get('Total Refunded', ''))
    total_refunded = parse_total_refunded(total_refunded_str)
    result['total_refunded'] = total_refunded
    
    # Calculate net paid (total paid minus refunds already issued)
    net_paid = total_paid - total_refunded
    result['net_paid'] = net_paid
    
    # Always calculate discounted price (discount calculator handles timing logic)
    try:
        # Calculate discounted price based on order date
        # The discount calculator will determine the appropriate discount tier
        # based on when the order was placed relative to the season start date
        discounted_price, discount_amount, discount_text = calculate_discounted_price(
            original_price=original_price,
            season_start_date_str=season_start_date,
            off_dates_str=None,  # Could extract from HTML if needed
            request_submitted_at=order_date,
        )
        
        result['discounted_price'] = discounted_price
        result['discount_amount'] = discount_amount
        
        # Determine if refund is due
        # Compare net paid (totalPaid - totalRefunded) vs discounted_price
        if net_paid > discounted_price:
            result['refund_due'] = True
            result['refund_amount'] = net_paid - discounted_price
        else:
            result['refund_due'] = False
            result['refund_amount'] = 0.0
            
    except Exception as e:
        result['error'] = f'Error calculating discount: {str(e)}'
    
    return result


def read_csv_file(file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Read CSV file and return headers and rows.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Tuple of (headers, rows)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    
    return headers, rows


def write_results_csv(results: List[Dict[str, Any]], output_path: str):
    """
    Write analysis results to CSV file.
    
    Args:
        results: List of analysis result dictionaries
        output_path: Path to output CSV file
    """
    if not results:
        print("No results to write", file=sys.stderr)
        return
    
    # Get all unique keys from results
    fieldnames = set()
    for result in results:
        fieldnames.update(result.keys())
    
    fieldnames = sorted(fieldnames)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze CSV orders to determine refund eligibility'
    )
    parser.add_argument(
        'input_csv',
        help='Input CSV file path'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output CSV file path (default: input_filename_refunds.csv)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Print detailed analysis for each order'
    )
    
    args = parser.parse_args()
    
    # Read input CSV
    try:
        headers, rows = read_csv_file(args.input_csv)
        print(f"Read {len(rows)} orders from {args.input_csv}")
    except Exception as e:
        print(f"Error reading CSV file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Analyze each order
    results = []
    errors = 0
    
    for i, row in enumerate(rows, 1):
        result = analyze_order(row, headers)
        results.append(result)
        
        if result.get('error'):
            errors += 1
            if args.verbose:
                print(f"Order {i} ({result.get('order_number', 'unknown')}): {result['error']}", file=sys.stderr)
        elif args.verbose:
            order_num = result.get('order_number', 'unknown')
            if result.get('refund_due'):
                print(f"Order {i} ({order_num}): Refund due: ${result['refund_amount']:.2f}")
            else:
                print(f"Order {i} ({order_num}): No refund due")
    
    # Summary
    refunds_due = sum(1 for r in results if r.get('refund_due'))
    total_refund_amount = sum(r.get('refund_amount', 0) for r in results if r.get('refund_due'))
    
    print(f"\nSummary:")
    print(f"  Total orders analyzed: {len(results)}")
    print(f"  Orders with errors: {errors}")
    print(f"  Orders eligible for refund: {refunds_due}")
    print(f"  Total refund amount: ${total_refund_amount:.2f}")
    
    # Write output CSV
    output_path = args.output or args.input_csv.replace('.csv', '_refunds.csv')
    try:
        write_results_csv(results, output_path)
        print(f"\nResults written to: {output_path}")
    except Exception as e:
        print(f"Error writing output CSV: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

