# """
# Refund calculation utilities.
# Handles business logic for calculating refund amounts based on season dates.
# """

from typing import Dict, Any, Optional
import logging
from datetime import datetime
from shared.date_utils import extract_season_dates, calculate_refund_amount

# logger = logging.getLogger(__name__)


def calculate_refund_due(
    order_data: Dict[str, Any],
    refund_type: str,
    request_submitted_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    return {}
#     """
#     Calculate refund amount based on order data and season information.

#     Args:
#         order_data: Shopify order data
#         refund_type: Type of refund ('refund' or 'credit')

#     Returns:
#         Dict containing refund calculation results
#     """
#     try:
#         logger.info(f"Calculating refund for {refund_type}")

#         # Get line items from order
#         line_items = order_data.get("line_items", [])
#         if not line_items:
#             return {
#                 "success": False,
#                 "message": "No line items found in order",
#                 "refund_amount": 0,
#             }

#         # For simplicity, use the first line item's product
#         first_item = line_items[0]
#         product_title = first_item.get("title", "")
#         product_description = first_item.get("product", {}).get(
#             "descriptionHtml", ""
#         )

#         logger.info(f"Calculating refund for product: {product_title}")

#         # Extract season dates from product description
#         try:
#             # extract_season_dates returns Tuple[Optional[str], Optional[str]]
#             season_dates_tuple = extract_season_dates(product_description)
#             season_start_date_str, off_dates_str = season_dates_tuple

#             logger.info(
#                 f"Extracted season dates: start={season_start_date_str}, off={off_dates_str}"
#             )

#             if not season_start_date_str:
#                 # Calculate refund based on total amount paid with percentage
#                 total_paid = float(order_data.get("total_price", 0))

#                 # Apply percentage based on refund type
#                 if refund_type == "credit":
#                     refund_percentage = 0.95  # 95% for store credit
#                 else:  # refund_type == "refund"
#                     refund_percentage = 0.90  # 90% for refund

#                 refund_amount = total_paid * refund_percentage

#                 return {
#                     "success": True,
#                     "message": f"Could not parse season dates. Calculated {refund_percentage*100:.0f}% of total paid (${total_paid:.2f})",
#                     "refund_amount": refund_amount,
#                     "product_title": product_title,
#                     "missing_season_info": True,  # Flag to indicate season info is missing
#                 }

#             # Get original cost (early bird variant price or total paid)
#             original_cost = self._get_original_cost(order_data)

#             # Calculate refund amount using original cost instead of total price
#             refund_amount, calculation_message = calculate_refund_amount(
#                 season_start_date_str=season_start_date_str,
#                 off_dates_str=off_dates_str,
#                 total_amount_paid=original_cost,  # Use original cost here
#                 refund_type=refund_type,
#                 request_submitted_at=request_submitted_at,  # Use actual submission timestamp
#             )

#             logger.info(
#                 f"Calculated refund amount: ${refund_amount:.2f} based on original cost: ${original_cost:.2f}"
#             )

#             return {
#                 "success": True,
#                 "refund_amount": refund_amount,
#                 "original_cost": original_cost,
#                 "order_total": float(order_data.get("total_price", 0)),
#                 "season_start_date": season_start_date_str,
#                 "off_dates": off_dates_str,
#                 "refund_type": refund_type,
#                 "product_title": product_title,
#                 "message": calculation_message,
#             }

#         except Exception as e:
#             logger.error(f"Error extracting season dates: {str(e)}")
#             return {
#                 "success": False,
#                 "message": f"Could not extract season dates from product description: {str(e)}",
#                 "refund_amount": 0,
#                 "product_title": product_title,
#             }

#     except Exception as e:
#         logger.error(f"Error calculating refund: {str(e)}")
#         return {
#             "success": False,
#             "message": f"Error calculating refund: {str(e)}",
#             "refund_amount": 0,
#         }
