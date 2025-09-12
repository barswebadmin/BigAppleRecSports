#!/usr/bin/env python3
"""
Validation service for deny refund action payloads.
Used for testing to ensure the correct structure is sent to GAS.
"""

from typing import Dict, Any


class DenyActionValidator:
    """Validates the structure and content of deny action payloads"""

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the structure of a deny action payload

        Args:
            payload: The payload to validate

        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []

        # Required fields
        required_fields = [
            "action",
            "order_number",
            "requestor_email",
            "first_name",
            "last_name",
            "custom_message",
            "cc_bcc_option",
            "slack_user_name",
            "slack_user_id",
        ]

        # Check for required fields
        for field in required_fields:
            if field not in payload:
                errors.append(f"Missing required field: {field}")
            elif payload[field] is None:
                errors.append(f"Field '{field}' cannot be None")
            elif isinstance(payload[field], str) and not payload[field].strip():
                errors.append(f"Field '{field}' cannot be empty")

        # Validate specific field values
        if "action" in payload:
            if payload["action"] != "send_denial_email":
                errors.append(
                    f"Invalid action value: {payload['action']}. Expected: 'send_denial_email'"
                )

        if "cc_bcc_option" in payload:
            valid_options = ["no", "cc", "bcc"]
            if payload["cc_bcc_option"] not in valid_options:
                errors.append(
                    f"Invalid cc_bcc_option: {payload['cc_bcc_option']}. Must be one of: {valid_options}"
                )

        if "order_number" in payload:
            order_num = payload["order_number"]
            if not isinstance(order_num, str) or not order_num.startswith("#"):
                errors.append(
                    f"Invalid order_number format: {order_num}. Must start with '#'"
                )

        if "requestor_email" in payload:
            email = payload["requestor_email"]
            if not isinstance(email, str) or "@" not in email:
                errors.append(f"Invalid email format: {email}")

        # Check for deprecated fields that should not be present
        deprecated_fields = ["include_staff_info", "staff_email", "staff_name"]
        for field in deprecated_fields:
            if field in payload:
                warnings.append(f"Deprecated field present: {field}")

        # Validate custom message content
        if "custom_message" in payload:
            message = payload["custom_message"]
            if len(message) < 10:
                warnings.append(
                    "Custom message is very short (less than 10 characters)"
                )
            if "Order #" not in message and "#" not in message:
                warnings.append(
                    "Custom message does not contain order number reference"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "field_count": len(payload),
            "required_fields_present": len(
                [f for f in required_fields if f in payload]
            ),
            "payload_summary": {
                "action": payload.get("action"),
                "order_number": payload.get("order_number"),
                "requestor_email": payload.get("requestor_email"),
                "cc_bcc_option": payload.get("cc_bcc_option"),
                "custom_message_length": len(payload.get("custom_message", ""))
                if payload.get("custom_message")
                else 0,
            },
        }

    @staticmethod
    def get_expected_structure() -> Dict[str, str]:
        """
        Return the expected structure for a deny action payload

        Returns:
            Dict describing expected fields and their types
        """
        return {
            "action": "string (must be 'send_denial_email')",
            "order_number": "string (must start with #)",
            "requestor_email": "string (valid email format)",
            "first_name": "string (non-empty)",
            "last_name": "string (non-empty)",
            "custom_message": "string (email body content)",
            "cc_bcc_option": "string (one of: no, cc, bcc)",
            "slack_user_name": "string (slack username)",
            "slack_user_id": "string (slack user ID)",
        }
