"""
Refunds Router

Handles incoming refund requests
"""

from fastapi import APIRouter, HTTPException, Request
from modules.refunds.service import RefundsService
from modules.orders.models import FetchOrderRequest

router = APIRouter(prefix="/refunds", tags=["refunds"])

refunds_service = RefundsService()

@router.post("/submit-request")
async def handle_refund_request(request: Request):
    payload = await request.json()
    body = FetchOrderRequest.create(payload)
    return refunds_service.process_initial_refund_request(body)
    