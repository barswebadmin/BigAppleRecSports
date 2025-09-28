import datetime
import logging
from backend.models.shopify.requests import FetchOrderRequest
from backend.new_structure_target.clients.shopify.builders.shopify_normalizers import normalize_order_number
from new_structure_target.services.orders.orders_service import OrdersService

logger = logging.getLogger("REFUNDS LOGGER")

orders_service = OrdersService()

def process_initial_refund_request(email: str, order_number: str, request_submitted_at: datetime.datetime):
    """
    Process the initial refund request
    """
    request_args = FetchOrderRequest.create({"order_number": order_number})
    order_details = orders_service.fetch_order_from_shopify(identifier=request_args)
    
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