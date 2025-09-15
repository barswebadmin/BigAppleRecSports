import json
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from services.products.products_service import ProductsService
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


@router.post("/create")
async def create_product(
    create_product_request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a product - accepts direct product data from GAS

    Validates the product data structure and types, then creates the product
    """
    logger.info("Product creation request received")
    logger.debug(f"Product data: {json.dumps(create_product_request_data, indent=2)}")

    # Validate and create ProductCreationRequest instance
    try:
        validated_request = ProductsService.to_product_creation_request(
            create_product_request_data
        )
        logger.info("Product validation passed")
    except ProductCreationRequestValidationError as e:
        logger.warning(f"Product validation failed: {e.get_errors()}")
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Product validation failed",
                "errors": e.get_errors(),
            },
        )

    # Create the product using the validated request object
    try:
        logger.info("🚀 Starting product creation process in router...")
        logger.info(
            f"📝 Request summary: {validated_request.sportName} - {validated_request.regularSeasonBasicDetails.dayOfPlay} - {validated_request.regularSeasonBasicDetails.division}"
        )

        result = ProductsService.create_product(validated_request)

        logger.info(f"📥 Product creation result: {result.get('success', False)}")
        if result.get("success"):
            logger.info("🎉 Product creation completed successfully!")
        else:
            logger.warning(f"⚠️ Product creation failed: {result.get('error')}")

        if result["success"]:
            logger.info(
                f"Product created successfully: {result.get('data', {}).get('product', {}).get('id')}"
            )
            return result
        else:
            logger.error(f"Product creation failed: {result.get('message')}")

            # Determine appropriate HTTP status code based on the error type
            status_code = (
                422
                if "validation" in result.get("error", "").lower()
                or "invalid" in result.get("error", "").lower()
                else 500
            )

            # Build detailed error response
            error_detail = {
                "message": result.get("message", "Product creation failed"),
                "error": result.get("error"),
                "step_failed": result.get("step_failed"),
            }

            # Include additional details if available
            if "details" in result:
                error_detail["details"] = result["details"]

            raise HTTPException(
                status_code=status_code,
                detail=error_detail,
            )

    except HTTPException:
        # Re-raise HTTPExceptions (including our validation errors above)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during product creation: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during product creation",
                "error": str(e),
                "step_failed": "unexpected_exception",
            },
        )
