from datetime import datetime


def process_initial_refund_request(email: str, order_number: str, request_submitted_at: datetime):
    """
    Public entry point for initial refund request processing.

    Delegates to the implementation in process_initial_refund_request.py.
    """
    # Lazy import to avoid heavy dependencies at import time (simplifies unit testing)
    from .process_initial_refund_request import process_initial_refund_request as _impl
    return _impl(email, order_number, request_submitted_at)


