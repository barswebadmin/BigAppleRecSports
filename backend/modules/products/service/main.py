"""
Products Service for validating and processing product creation requests
"""

import logging
from typing import Dict, Any
from .fetch_product_from_shopify import fetch_product_from_shopify
from .inventory.update_product_inventory import update_product_inventory
from ..models import FetchProductRequest, ProductCreationRequest, ProductCreationRequestValidationError

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
    def create_product(cls, validated_request):
        """
        Create a product from a validated ProductCreationRequest instance
        """
        return create_product_complete_process(validated_request)

    def get_product_details(self,request_details):
        """
        Fetch product details from Shopify
        """
        return fetch_product_from_shopify(request_details)

    def update_inventory(self, validated_request):
        """
        Update inventory for a product from a validated FetchProductRequest instance
        """
        return update_product_inventory(validated_request)
