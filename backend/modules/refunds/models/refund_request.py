from pydantic import model_validator, Field
from typing import Optional
from datetime import datetime, timezone

from validator_collection import is_email

from shared.model_config import ApiModel
from backend.modules.integrations.shopify.services.shopify_normalizers import (
    validate_shopify_order_number_format,
)
from shared.validators import (
    validate_multiple_fields,
)

class RefundRequest(ApiModel):
    """
    Request model for initiating a refund.

    Accepts both snake_case (order_number) and camelCase (orderNumber) input thanks
    to ApiModel's alias_generator.
    """

    email: str
    order_number: str
    request_submitted_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode='before')
    @classmethod
    def validate_all_fields(cls, values):
        """
        Validate all fields using centralized multi-field validator.
        This ensures both email and order_number errors are reported together,
        even when inputs are not strings.
        """
        if not isinstance(values, dict):
            return values
        
        # Define field validators for this model
        field_validators = {
            "email": is_email,
            "order_number": validate_shopify_order_number_format,
        }
        
        # Use centralized validation
        result = validate_multiple_fields(values, field_validators)
        
        # If validation failed, raise ValueError with all errors
        if not result["success"]:
            raise ValueError("; ".join(result["errors"]))
            
        return values

    @classmethod
    def create(cls, data):
        """
        Validate input data and create RefundRequest instance.
        
        This method provides a clean interface that:
        1. Runs our custom validation logic (validate_all_fields hook)
        2. Handles field aliasing (orderNumber → order_number)
        3. Performs type conversion and creates the instance
        
        Args:
            data: Dictionary containing email and order_number fields
            
        Returns:
            RefundRequest: Validated instance
            
        Raises:
            ValueError: If validation fails (contains all field errors)
        """
        return cls.model_validate(data)


