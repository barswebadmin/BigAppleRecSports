import datetime
import logging
from new_structure_target.clients.shopify.shopify_service import ShopifyService

logger = logging.getLogger("REFUNDS LOGGER")

shopify_service = ShopifyService()

def process_initial_refund_request(email: str, order_number: str, request_submitted_at: datetime.datetime):
    """
    Process the initial refund request
    """
    # call shopify to get order details
    order_details = shopify_service.get_order_details(order_number)
    logger.info(f"Order details: {order_details}")

    return order_details


    # later:
    # validate order exists
    # validate provided email matches order email
    # validate order not already cancelled
    # validate order not already refunded
    # validate order not already in refund queue
    # validate order not already in refund history
    # validate any money was paid for the order
    # calculate refund amounts and ensure > 0
    # return refund options to FE with 