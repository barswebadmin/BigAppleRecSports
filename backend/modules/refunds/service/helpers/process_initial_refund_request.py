import logging
from modules.orders.models import FetchOrderRequest
from shared.fetch_shopify_orders import fetch_order_from_shopify

def process_initial_refund_request(request: FetchOrderRequest):
    """
    Public entry point for initial refund request processing.

    Args:
        request: Validated refund request payload

    Returns:
        The result of the initial refund request processing. Exits early if there is an error and returns an HTTPException.
    """

    request_args = FetchOrderRequest.create({"order_number": request.order_number})
    try:
        order_details = fetch_order_from_shopify(request_args)
        if not order_details.get("success"):
            error_msg = order_details.get("message", "Unknown error fetching order")
            logging.getLogger("REFUNDS LOGGER").error(f"Error fetching order: {error_msg}")
            raise ValueError(f"Error fetching order: {error_msg}")
        return order_details
    except Exception as e:
        logging.getLogger("REFUNDS LOGGER").error(f"Error fetching order: {str(e)}")
        raise ValueError(f"Error fetching order: {str(e)}")


    # later:
    # validate order exists
    # validate provided email matches order email
    # validate order not already cancelled
    # validate order not already refunded
    # validate any money was paid for the order

    # validate order not already in refund queue
    # validate order not already in refund history
    
    # calculate refund amounts and ensure > 0
    # return refund options to FE with 