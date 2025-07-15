"""
Refund calculation utilities.
Handles business logic for calculating refund amounts based on season dates.
"""

from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timezone
from utils.date_utils import extract_season_dates, calculate_refund_amount

logger = logging.getLogger(__name__)


class RefundCalculator:
    """Helper class for calculating refund amounts based on season information."""
    
    def _get_original_cost(self, order_data: Dict[str, Any]) -> float:
        """
        Get the original cost by finding early bird variant price or fall back to total paid.
        Based on Google Apps Script logic:
        const earlyVariant = product.variants.find(variant => variant.variantName.toLowerCase().includes("trans"))
        const originalCost = earlyVariant?.price || totalAmountPaid
        """
        try:
            # Get total amount paid as fallback
            total_paid = float(order_data.get("total_price", 0))
            
            # Try to find early bird variant from product variants
            product = order_data.get("product", {})
            variants = product.get("variants", [])
            
            logger.info(f"Searching for early bird variant in {len(variants)} variants")
            
            for variant in variants:
                variant_name = variant.get("variantName", variant.get("title", "")).lower()
                logger.info(f"Checking variant: {variant_name}")
                
                # Look for transfer variants, early registration, or veteran registration (original pricing)
                if any(keyword in variant_name for keyword in ["trans", "early", "veteran", "vet", "wtnb", "bipoc"]):
                    # Found early bird/transfer/veteran variant (original pricing)
                    variant_price = variant.get("price")
                    if variant_price:
                        try:
                            original_cost = float(variant_price)
                            logger.info(f"Found original pricing variant '{variant_name}' with price ${original_cost}")
                            return original_cost
                        except (ValueError, TypeError):
                            continue
            
            # No early bird variant found, use total paid
            logger.info(f"No early bird variant found, using total paid: ${total_paid}")
            return total_paid
            
        except Exception as e:
            logger.error(f"Error getting original cost: {str(e)}")
            return float(order_data.get("total_price", 0))
    
    def calculate_refund_due(self, order_data: Dict[str, Any], refund_type: str) -> Dict[str, Any]:
        """
        Calculate refund amount based on order data and season information.
        
        Args:
            order_data: Shopify order data
            refund_type: Type of refund ('refund' or 'credit')
            
        Returns:
            Dict containing refund calculation results
        """
        try:
            logger.info(f"Calculating refund for {refund_type}")
            
            # Get line items from order
            line_items = order_data.get("line_items", [])
            if not line_items:
                return {
                    "success": False,
                    "message": "No line items found in order",
                    "refund_amount": 0
                }
            
            # For simplicity, use the first line item's product
            first_item = line_items[0]
            product_title = first_item.get("title", "")
            product_description = first_item.get("product", {}).get("descriptionHtml", "")
            
            logger.info(f"Calculating refund for product: {product_title}")
            
            # Extract season dates from product description
            try:
                # extract_season_dates returns Tuple[Optional[str], Optional[str]]
                season_dates_tuple = extract_season_dates(product_description)
                season_start_date_str, off_dates_str = season_dates_tuple
                
                logger.info(f"Extracted season dates: start={season_start_date_str}, off={off_dates_str}")
                
                if not season_start_date_str:
                    # Calculate refund based on total amount paid with percentage
                    total_paid = float(order_data.get("total_price", 0))
                    
                    # Apply percentage based on refund type
                    if refund_type == "credit":
                        refund_percentage = 0.95  # 95% for store credit
                    else:  # refund_type == "refund"
                        refund_percentage = 0.90  # 90% for refund
                    
                    refund_amount = total_paid * refund_percentage
                    
                    return {
                        "success": True,
                        "message": f"Could not parse season dates. Calculated {refund_percentage*100:.0f}% of total paid (${total_paid:.2f})",
                        "refund_amount": refund_amount,
                        "product_title": product_title,
                        "missing_season_info": True  # Flag to indicate season info is missing
                    }
                
                # Get original cost (early bird variant price or total paid)
                original_cost = self._get_original_cost(order_data)
                
                # Calculate refund amount using original cost instead of total price
                refund_amount, calculation_message = calculate_refund_amount(
                    season_start_date_str=season_start_date_str,
                    off_dates_str=off_dates_str,
                    total_amount_paid=original_cost,  # Use original cost here
                    refund_or_credit=refund_type,
                    request_submitted_at=datetime.now(timezone.utc)
                )
                
                logger.info(f"Calculated refund amount: ${refund_amount:.2f} based on original cost: ${original_cost:.2f}")
                
                return {
                    "success": True,
                    "refund_amount": refund_amount,
                    "original_cost": original_cost,
                    "order_total": float(order_data.get("total_price", 0)),
                    "season_start_date": season_start_date_str,
                    "off_dates": off_dates_str,
                    "refund_type": refund_type,
                    "product_title": product_title,
                    "message": calculation_message
                }
                
            except Exception as e:
                logger.error(f"Error extracting season dates: {str(e)}")
                return {
                    "success": False,
                    "message": f"Could not extract season dates from product description: {str(e)}",
                    "refund_amount": 0,
                    "product_title": product_title
                }
                
        except Exception as e:
            logger.error(f"Error calculating refund: {str(e)}")
            return {
                "success": False,
                "message": f"Error calculating refund: {str(e)}",
                "refund_amount": 0
            } 