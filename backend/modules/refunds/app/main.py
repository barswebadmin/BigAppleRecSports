import logging
from ..models import RefundRequest
from .helpers.process_initial_refund_request import process_initial_refund_request

logger = logging.getLogger("REFUNDS LOGGER")

class RefundsService:
    
    def process_initial_refund_request(self, email: str, order_number: str):
        """
        Public entry point for initial refund request processing.

        Args:
            email: Customer email address
            order_number: Shopify order number

        Returns:
            The result of the initial refund request processing. Exits early if there is an error and returns an HTTPException.
        """
        request = RefundRequest.create({"email": email, "order_number": order_number})
        return process_initial_refund_request(request)


