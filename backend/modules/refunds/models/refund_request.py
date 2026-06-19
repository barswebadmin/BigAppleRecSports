from pydantic import BaseModel, model_validator, Field
from typing import Optional
from datetime import datetime, timezone

from validator_collection import is_email

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT
from backend.modules.integrations.shopify.services.shopify_normalizers import (
    validate_shopify_order_number_format,
)


class RefundRequest(BaseModel):
    """Request model for initiating a refund."""
    model_config = DEFAULT_CONFIG_DICT

    email: str
    order_number: str
    request_submitted_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode='before')
    @classmethod
    def validate_all_fields(cls, values):
        """Validate email and order_number, reporting all errors together."""
        if not isinstance(values, dict):
            return values
        
        errors = []
        email = values.get("email")
        order_number = values.get("order_number")
        
        if not is_email(email):
            errors.append("Invalid email format")
        if not validate_shopify_order_number_format(order_number):
            errors.append("Invalid order number format")
        
        if errors:
            raise ValueError("; ".join(errors))
            
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


