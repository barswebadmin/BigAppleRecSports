"""Order analysis and refund calculation utilities."""

from typing import Any, Dict, List, Optional

import click

from backend.shared.date_utils import calculate_refund_amount, extract_season_dates
from bars_cli.utils.csv_utils import read_csv_file, write_results_csv
from bars_cli.utils.data_parsing import (
    extract_price_from_html,
    parse_order_date,
    parse_total_paid,
    parse_total_refunded,
)


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
    
    # Extract season dates using shared utility
    season_start_date_str, off_dates_str = extract_season_dates(description_html)
    if season_start_date_str is None:
        result['error'] = 'Could not extract season start date from descriptionHtml'
        return result
    result['season_start_date'] = season_start_date_str
    
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
    net_paid = total_paid - (total_refunded or 0.0)
    result['net_paid'] = net_paid
    
    # Calculate discounted price using shared utility
    try:
        # Calculate what refund would be due if requested now (based on order date)
        # This tells us what discount tier the order falls into
        # The refund amount represents how much they overpaid
        refund_amount_due, refund_message = calculate_refund_amount(
            season_start_date_str=season_start_date_str,
            off_dates_str=off_dates_str,
            total_amount_paid=original_price,
            refund_type="refund",  # Use "refund" type for analysis
            request_submitted_at=order_date,
        )
        
        # The discounted price is what they should have paid
        # If they paid original_price and are due refund_amount_due,
        # then they should have paid: original_price - refund_amount_due
        discounted_price = original_price - refund_amount_due if refund_amount_due else original_price
        discount_amount = refund_amount_due if refund_amount_due else 0.0
        
        result['discounted_price'] = discounted_price
        result['discount_amount'] = discount_amount
        
        # Determine if refund is due
        # Compare net paid (totalPaid - totalRefunded) vs discounted_price
        # If they paid more than the discounted price, they're due a refund
        if net_paid > discounted_price:
            result['refund_due'] = True
            result['refund_amount'] = net_paid - discounted_price
        else:
            result['refund_due'] = False
            result['refund_amount'] = 0.0
            
    except Exception as e:
        result['error'] = f'Error calculating discount: {str(e)}'
    
    return result


def analyze_order_refunds(input_csv: str, output_csv: Optional[str] = None, verbose: bool = False) -> int:
    """
    Analyze CSV orders to determine refund eligibility.
    
    Args:
        input_csv: Path to input CSV file
        output_csv: Optional path to output CSV file (defaults to input_filename_refunds.csv)
        verbose: If True, print detailed analysis for each order
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Read input CSV
    try:
        headers, rows = read_csv_file(input_csv)
        click.echo(f"Read {len(rows)} orders from {input_csv}")
    except Exception as e:
        click.echo(f"Error reading CSV file: {e}", err=True)
        return 1
    
    # Analyze each order
    results = []
    errors = 0
    
    for i, row in enumerate(rows, 1):
        result = analyze_order(row, headers)
        results.append(result)
        
        if result.get('error'):
            errors += 1
            if verbose:
                click.echo(f"Order {i} ({result.get('order_number', 'unknown')}): {result['error']}", err=True)
        elif verbose:
            order_num = result.get('order_number', 'unknown')
            if result.get('refund_due'):
                click.echo(f"Order {i} ({order_num}): Refund due: ${result['refund_amount']:.2f}")
            else:
                click.echo(f"Order {i} ({order_num}): No refund due")
    
    # Summary
    refunds_due = sum(1 for r in results if r.get('refund_due'))
    total_refund_amount = sum(r.get('refund_amount', 0) for r in results if r.get('refund_due'))
    
    click.echo("\nSummary:")
    click.echo(f"  Total orders analyzed: {len(results)}")
    click.echo(f"  Orders with errors: {errors}")
    click.echo(f"  Orders eligible for refund: {refunds_due}")
    click.echo(f"  Total refund amount: ${total_refund_amount:.2f}")
    
    # Write output CSV
    output_path = output_csv or input_csv.replace('.csv', '_refunds.csv')
    try:
        write_results_csv(results, output_path)
        click.echo(f"\nResults written to: {output_path}")
    except Exception as e:
        click.echo(f"Error writing output CSV: {e}", err=True)
        return 1
    
    return 0
