"""
Products Service for validating and processing product creation requests
"""

import logging
from typing import Dict, Any
from models.products.create_product_request import CreateProductRequest
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ProductsService:
    """Service for handling product creation and validation"""

    @classmethod
    def is_valid_product_request_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate product request data structure and types using Pydantic model

        Args:
            data: Raw product data dictionary from request

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        try:
            # Try to create Pydantic model - this handles all validation including sport-specific rules
            CreateProductRequest(**data)
            return {"valid": True, "errors": []}

        except ValidationError as e:
            # Extract detailed error messages from Pydantic
            errors = []
            for error in e.errors():
                # Build field path
                field_path = ".".join(str(loc) for loc in error["loc"])

                # Get error message
                msg = error["msg"]

                # Format the error message
                if field_path:
                    errors.append(f"{field_path}: {msg}")
                else:
                    errors.append(msg)

            return {"valid": False, "errors": errors}

        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return {"valid": False, "errors": [f"Validation error: {str(e)}"]}
