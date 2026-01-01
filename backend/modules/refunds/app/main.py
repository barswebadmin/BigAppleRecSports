import logging
from ..models import RefundRequest
from .helpers.process_initial_refund_request import process_initial_refund_request

logger = logging.getLogger("REFUNDS LOGGER")

class RefundsService:
    
    def process_initial_refund_request(self, email: str, order_number: str, request_submitted_at: str = None):
        """
        Public entry point for initial refund request processing.

        Args:
            email: Customer email address
            order_number: Shopify order number
            request_submitted_at: ISO timestamp when request was submitted (auto-generated if not provided)

        Returns:
            The result of the initial refund request processing. Exits early if there is an error and returns an HTTPException.
        """
        payload = {"email": email, "order_number": order_number}
        if request_submitted_at:
            payload["request_submitted_at"] = request_submitted_at
        request = RefundRequest.create(payload)
        return process_initial_refund_request(request)


