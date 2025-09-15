import json
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from services.products.products_service import ProductsService
from services.products.create_product import create_product as create_product_service

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

    # Validate the product request data
    validation_result = ProductsService.is_valid_product_request_data(
        create_product_request_data
    )

    if not validation_result["valid"]:
        logger.warning(f"Product validation failed: {validation_result['errors']}")
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Product validation failed",
                "errors": validation_result["errors"],
            },
        )

    logger.info("Product validation passed")

    # Create the product
    try:
        result = create_product_service(create_product_request_data)

        if result["success"]:
            logger.info(f"Product created successfully: {result.get('product_id')}")
            return result
        else:
            logger.error(f"Product creation failed: {result.get('message')}")
            raise HTTPException(
                status_code=500,
                detail={
                    "message": result.get("message", "Product creation failed"),
                    "error": result.get("error"),
                },
            )

    except Exception as e:
        logger.error(f"Unexpected error during product creation: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal server error during product creation",
                "error": str(e),
            },
        )
