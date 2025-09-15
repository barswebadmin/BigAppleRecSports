"""
Products Service for validating and processing product creation requests
"""

import logging
from typing import Dict, Any
from models.products.product_creation_request import ProductCreationRequest
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)

logger = logging.getLogger(__name__)


class ProductsService:
    """Service for handling product creation and validation"""

    @classmethod
    def is_valid_product_creation_request(
        cls, data: Dict[str, Any]
    ) -> ProductCreationRequest:
        """
        Validate product creation request data using Pydantic model

        Args:
            data: Raw product data dictionary from request

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
            raise ProductCreationRequestValidationError([f"Validation error: {str(e)}"])
