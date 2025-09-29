import logging
from backend.modules.refunds.models import RefundRequest
from .helpers.process_initial_refund_request import process_initial_refund_request

logger = logging.getLogger("REFUNDS LOGGER")

class RefundsService:
    
    def process_initial_refund_request(self, request: RefundRequest):
        """
        Public entry point for initial refund request processing.

        Args:
            request: Validated refund request payload

        Returns:
            The result of the initial refund request processing. Exits early if there is an error and returns an HTTPException.
        """
        return process_initial_refund_request(request)


