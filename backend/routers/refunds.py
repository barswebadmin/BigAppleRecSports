"""
Refunds Router

Handles incoming refund requests
"""

from fastapi import APIRouter, HTTPException, Request
from modules.refunds import RefundsService
from modules.refunds.models import RefundRequest
from pydantic import ValidationError

router = APIRouter(prefix="/refunds", tags=["refunds"])

refunds_service = RefundsService()

@router.post("/submit-request")
async def handle_refund_request(request: Request):
    try:
        payload = await request.json()
        body = RefundRequest.create(payload)
        return refunds_service.process_initial_refund_request(
            email=body.email,
            order_number=body.order_number
        )
    except (ValidationError, ValueError) as e:
        # Map validation issues to HTTP 400 instead of FastAPI's default 422
        detail = str(e)
        raise HTTPException(status_code=400, detail=detail)