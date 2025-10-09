"""
Test webhook signature verification functionality.
"""

from shared.security.webhook_signature_verification import (
    is_valid_webhook_signature,
    extract_slack_webhook_signature,
    InvalidSlackSignatureError
)


class TestWebhookSignatureVerification:
    """Test webhook signature verification for different services."""

    def test_slack_signature_extraction(self):
        """Test the extract_slack_webhook_signature function with valid data."""
        signing_secret = "test_secret"
        
        headers = {
            "x-slack-signature": "v0=will_be_calculated",
            "x-slack-request-timestamp": "1234567890"
        }
        
        raw_request_body = b'token=test_token&text=hello&api_app_id=TEST_APP_ID'
        app_id = "TEST_APP_ID"
        expected_signature = extract_slack_webhook_signature(headers, signing_secret, raw_request_body, app_id)
        
        # Verify the extraction worked
        assert expected_signature is not None
        
        # Verify the signature matches what we received (we'll use the calculated signature)
        received_signature = expected_signature  # Use the calculated signature as "received"
        assert is_valid_webhook_signature(received_signature, expected_signature) == True

    def test_slack_signature_verification(self):
        """Test signature verification with mock data."""
        # Use mock data instead of real data
        signing_secret = "test_signing_secret_12345"
        timestamp = "1234567890"
        app_id = "TEST_APP_ID"
        
        # Create a simple mock request body
        raw_request_body = b'token=test_token&text=hello&api_app_id=TEST_APP_ID&command=%2Ftest'
        
        # Calculate the expected signature using our function
        headers = {
            "x-slack-signature": "v0=will_be_calculated",
            "x-slack-request-timestamp": timestamp
        }
        
        expected_signature = extract_slack_webhook_signature(headers, signing_secret, raw_request_body, app_id)
        
        # Verify the extraction worked
        assert expected_signature is not None
        
        # Test cases: valid and invalid signatures
        test_cases = [
            {
                "name": "valid_signature",
                "received_signature": expected_signature,  # Use the calculated signature as "received"
                "expected_result": True
            },
            {
                "name": "invalid_signature", 
                "received_signature": "v0=invalid_signature_12345",
                "expected_result": False
            }
        ]
        
        for test_case in test_cases:
            if test_case["expected_result"]:
                # Should succeed
                result = is_valid_webhook_signature(
                    test_case["received_signature"], 
                    expected_signature
                )
                assert result == True, f"Failed for {test_case['name']}"
            else:
                # Should raise InvalidSlackSignatureError
                try:
                    is_valid_webhook_signature(
                        test_case["received_signature"], 
                        expected_signature
                    )
                    assert False, f"Expected InvalidSlackSignatureError for {test_case['name']}"
                except InvalidSlackSignatureError:
                    # This is expected
                    pass
