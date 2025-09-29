"""
Products Service for validating and processing product creation requests
"""

import logging
from typing import Dict, Any
from models.products.product_creation_request import ProductCreationRequest
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)
from .create_product_complete_process.create_product_complete_process import (
    create_product_complete_process,
)

logger = logging.getLogger(__name__)


class ProductsService:
    """Service for handling product creation and validation"""

    @classmethod
    def to_product_creation_request(
        cls, data: Dict[str, Any]
    ) -> ProductCreationRequest:
        """
        Create and validate a ProductCreationRequest instance from raw data

        Args:
            data: Raw product data dictionary from request (should already be properly structured by GAS)
        Returns:
            ProductCreationRequest instance if valid
        Raises:
            ProductCreationRequestValidationError: If validation fails with all error details
        """
        try:
            return ProductCreationRequest.validate_request_data(data)
        except ProductCreationRequestValidationError:
            # Re-raise the custom validation error to be handled by the router
            raise
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            raise ProductCreationRequestValidationError(
                [{"msg": f"Validation error: {str(e)}", "loc": ["unknown"]}]
            )

    @classmethod
    def create_product(
        cls, validated_request: ProductCreationRequest
    ) -> Dict[str, Any]:
        """
        Create a product from a validated ProductCreationRequest instance
        """
        return create_product_complete_process(validated_request)
