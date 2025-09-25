"""
Refunds Router

Handles incoming refund requests
"""

from fastapi import APIRouter, Request, HTTPException
import logging
import json
from datetime import datetime, timezone
from new_structure_target.services.refunds.refunds_service import process_initial_refund_request
from utils.validators import validate_email_format, validate_shopify_order_number_format

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/refunds", tags=["refunds"])

@router.post("/submit-request")
async def handle_refund_request(request: Request):
    payload = await request.json()
    logger.info(f"Received refund request: {payload}")
    email = payload.get("email")
    order_number = payload.get("orderNumber")

    validation_results = [
        validate_email_format(email),
        validate_shopify_order_number_format(order_number),
    ]
    errors = [str(r["message"]) for r in validation_results if not r["success"] and r.get("message")]
    if errors:
        raise HTTPException(status_code=422, detail='; '.join(errors))

    now = datetime.now(timezone.utc)
    return process_initial_refund_request(email=email, order_number=order_number, request_submitted_at=now)