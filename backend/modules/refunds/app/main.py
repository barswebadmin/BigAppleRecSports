import logging
from .helpers.process_initial_refund_request import process_initial_refund_request

logger = logging.getLogger("REFUNDS LOGGER")

class RefundsService:
    
    def process_initial_refund_request(self, request):
        return process_initial_refund_request(request)


