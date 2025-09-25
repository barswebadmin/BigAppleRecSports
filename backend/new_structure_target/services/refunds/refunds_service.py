from datetime import datetime
from .process_initial_refund_request import process_initial_refund_request as _process_initial_refund_request


def process_initial_refund_request(email: str, order_number: str, request_submitted_at: datetime):
    """
    Public entry point for initial refund request processing.

    Delegates to the implementation in process_initial_refund_request.py.
    """
    return _process_initial_refund_request(email, order_number, request_submitted_at)


