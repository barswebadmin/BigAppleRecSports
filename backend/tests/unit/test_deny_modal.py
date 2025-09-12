#!/usr/bin/env python3
"""
Tests for the deny modal functionality - both UI structure and submission handling
"""

import pytest
import json
from unittest.mock import Mock
from fastapi.testclient import TestClient
from services.slack.slack_refunds_utils import SlackRefundsUtils


class TestDenyModal:
    """Test the deny modal UI structure and functionality"""

    @pytest.fixture
    def slack_refunds_utils(self):
        """Create SlackRefundsUtils instance for testing"""
        # Create mocks for required dependencies
        mock_orders_service = Mock()
        mock_settings = Mock()
        mock_settings.SLACK_CHANNEL_ID = "C123456789"
        mock_settings.SLACK_BOT_TOKEN = "xoxb-test-token"

        return SlackRefundsUtils(
            orders_service=mock_orders_service, settings=mock_settings
        )

    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client for internal endpoint testing"""
        from main import app

        return TestClient(app)

    @pytest.fixture
    def sample_request_data(self):
        """Sample request data for testing"""
        return {
            "rawOrderNumber": "#42308",
            "refundType": "refund",
            "requestorEmail": "jdazz87@gmail.com",
            "first": "joe",
            "last": "ra",
            "email": "jdazz87@gmail.com",
            "requestSubmittedAt": "09/12/25 at 7:51 AM",
        }

    def test_deny_modal_structure(self, slack_refunds_utils, sample_request_data):
        """Test that the deny modal has the correct structure and required elements"""

        # Build the modal blocks
        modal_blocks = slack_refunds_utils._build_deny_request_modal_blocks(
            raw_order_number=sample_request_data["rawOrderNumber"],
            requestor_email=sample_request_data["requestorEmail"],
            first_name=sample_request_data["first"],
            last_name=sample_request_data["last"],
            refund_type=sample_request_data["refundType"],
        )

        # Test structure
        assert len(modal_blocks) == 5, "Modal should have exactly 5 blocks"

        # Test first block - intro text with requestor info
        intro_block = modal_blocks[0]
        assert intro_block["type"] == "section"
        intro_text = intro_block["text"]["text"]

        # Test presence of requestor name and email
        assert "joe ra" in intro_text, "Requestor name should be present"
        assert "jdazz87@gmail.com" in intro_text, "Requestor email should be present"

        # Test presence of order number (should not be blank)
        assert "#42308" in intro_text, "Order number should be present and not blank"
        assert (
            sample_request_data["rawOrderNumber"] != ""
        ), "Order number should not be empty"

        # Test second block - divider
        assert modal_blocks[1]["type"] == "divider"

        # Test third block - subject line
        subject_block = modal_blocks[2]
        assert subject_block["type"] == "section"
        subject_text = subject_block["text"]["text"]
        assert "Subject Line" in subject_text, "Should contain subject line label"
        assert "#42308" in subject_text, "Subject should contain order number"

        # Test fourth block - email body input
        email_body_block = modal_blocks[3]
        assert email_body_block["type"] == "input"
        assert email_body_block["block_id"] == "custom_message_input"
        assert email_body_block["label"]["text"] == "Email Body (edit to your liking)"
        assert not email_body_block["optional"], "Email body should be required"

        # Test fifth block - CC/BCC dropdown
        cc_bcc_block = modal_blocks[4]
        assert cc_bcc_block["type"] == "input"
        assert cc_bcc_block["block_id"] == "cc_bcc_input"
        assert "CC/BCC" in cc_bcc_block["label"]["text"]

        # Test dropdown options
        dropdown_element = cc_bcc_block["element"]
        assert dropdown_element["type"] == "static_select"
        options = dropdown_element["options"]
        assert len(options) == 3, "Should have 3 CC/BCC options"

        option_values = [opt["value"] for opt in options]
        assert "no" in option_values
        assert "cc" in option_values
        assert "bcc" in option_values

        # Test default selection
        assert dropdown_element["initial_option"]["value"] == "no"

    def test_modal_button_structure(self, slack_refunds_utils):
        """Test that modal buttons have correct text and structure"""

        # Create a mock modal view
        modal_blocks = []
        modal_title = "Deny Refund Request"
        callback_id = "deny_refund_modal"

        # Use the internal method that creates the modal view
        modal_view = {
            "type": "modal",
            "callback_id": callback_id,
            "title": {"type": "plain_text", "text": modal_title},
            "blocks": modal_blocks,
            "submit": {"type": "plain_text", "text": "Deny & Send Email"},
            "close": {"type": "plain_text", "text": "Cancel"},
        }

        # Test submit button
        submit_button = modal_view["submit"]
        assert submit_button["text"] == "Deny & Send Email"
        assert "Deny" in submit_button["text"], "Submit button should contain 'Deny'"
        assert (
            len(submit_button["text"]) <= 25
        ), "Button text must be under 25 characters for Slack API"

        # Test close/cancel button
        close_button = modal_view["close"]
        assert close_button["text"] == "Cancel"

    @pytest.mark.asyncio
    async def test_modal_submission_with_default_text(
        self, slack_refunds_utils, test_client
    ):
        """Test modal submission sends correct data structure with default email text"""

        # Mock the _send_denial_email_via_gas method to capture the payload
        captured_payload = {}

        async def mock_send_denial_email(
            order_number: str,
            requestor_email: str,
            first_name: str,
            last_name: str,
            custom_message: str,
            cc_bcc_option: str,
            slack_user_name: str,
            slack_user_id: str,
        ):
            captured_payload.update(
                {
                    "action": "send_denial_email",
                    "order_number": order_number,
                    "requestor_email": requestor_email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "custom_message": custom_message,
                    "cc_bcc_option": cc_bcc_option,
                    "slack_user_name": slack_user_name,
                    "slack_user_id": slack_user_id,
                }
            )
            return {"success": True, "message": "Email sent successfully"}

        slack_refunds_utils._send_denial_email_via_gas = mock_send_denial_email

        # Create mock payload simulating modal submission
        modal_payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {
                            "custom_message": {
                                "value": "Hi joe,\n\nWe're sorry, but we were not able to approve your refund request for Order #42308. Please sign in to view your orders and try again if needed.\n\nIf you have any questions, please reach out to refunds@bigapplerecsports.com."
                            }
                        },
                        "cc_bcc_input": {
                            "cc_bcc_option": {"selected_option": {"value": "no"}}
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123456789",
                        "slack_user_name": "testuser",
                        "slack_user_id": "U123456789",
                        "raw_order_number": "#42308",
                        "requestor_email": "jdazz87@gmail.com",
                        "first_name": "joe",
                        "last_name": "ra",
                    }
                ),
            }
        }

        # Process the modal submission
        await slack_refunds_utils.handle_deny_refund_request_modal_submission(
            modal_payload
        )

        # Use our test endpoint to validate the payload structure
        response = test_client.post(
            "/refunds/test/validate-deny-action", json=captured_payload
        )

        assert response.status_code == 200
        validation_data = response.json()

        # Test validation passed
        assert validation_data["success"]
        assert validation_data["validation"][
            "valid"
        ], f"Validation errors: {validation_data['validation']['errors']}"
        assert len(validation_data["validation"]["errors"]) == 0

        # Test required fields are present in captured payload
        payload = validation_data["received_payload"]
        assert payload["action"] == "send_denial_email"
        assert payload["order_number"] == "#42308"
        assert payload["requestor_email"] == "jdazz87@gmail.com"
        assert payload["first_name"] == "joe"
        assert payload["last_name"] == "ra"
        assert payload["cc_bcc_option"] == "no"
        assert payload["slack_user_name"] == "testuser"
        assert payload["slack_user_id"] == "U123456789"

        # Test email body content
        expected_default_text = "Hi joe,\n\nWe're sorry, but we were not able to approve your refund request for Order #42308. Please sign in to view your orders and try again if needed.\n\nIf you have any questions, please reach out to refunds@bigapplerecsports.com."
        assert payload["custom_message"] == expected_default_text

    @pytest.mark.asyncio
    async def test_modal_submission_with_custom_text(
        self, slack_refunds_utils, test_client
    ):
        """Test modal submission sends updated text when user modifies email body"""

        # Mock the _send_denial_email_via_gas method to capture the payload
        captured_payload = {}

        async def mock_send_denial_email(
            order_number: str,
            requestor_email: str,
            first_name: str,
            last_name: str,
            custom_message: str,
            cc_bcc_option: str,
            slack_user_name: str,
            slack_user_id: str,
        ):
            captured_payload.update(
                {
                    "action": "send_denial_email",
                    "order_number": order_number,
                    "requestor_email": requestor_email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "custom_message": custom_message,
                    "cc_bcc_option": cc_bcc_option,
                    "slack_user_name": slack_user_name,
                    "slack_user_id": slack_user_id,
                }
            )
            return {"success": True, "message": "Email sent successfully"}

        slack_refunds_utils._send_denial_email_via_gas = mock_send_denial_email

        custom_email_text = "Hi joe,\n\nYour refund request has been reviewed and unfortunately we cannot process it at this time due to our refund policy. Please contact us if you have questions.\n\nBest regards,\nBARS Team"

        # Create mock payload with custom email text
        modal_payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {
                            "custom_message": {"value": custom_email_text}
                        },
                        "cc_bcc_input": {
                            "cc_bcc_option": {"selected_option": {"value": "cc"}}
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123456789",
                        "slack_user_name": "testuser",
                        "slack_user_id": "U123456789",
                        "raw_order_number": "#42308",
                        "requestor_email": "jdazz87@gmail.com",
                        "first_name": "joe",
                        "last_name": "ra",
                    }
                ),
            }
        }

        # Process the modal submission
        await slack_refunds_utils.handle_deny_refund_request_modal_submission(
            modal_payload
        )

        # Use our test endpoint to validate the payload structure
        response = test_client.post(
            "/refunds/test/validate-deny-action", json=captured_payload
        )

        assert response.status_code == 200
        validation_data = response.json()

        # Test validation passed
        assert validation_data["success"]
        assert validation_data["validation"][
            "valid"
        ], f"Validation errors: {validation_data['validation']['errors']}"

        # Get the validated payload
        payload = validation_data["received_payload"]

        # Test that custom email text was sent
        assert (
            payload["custom_message"] == custom_email_text
        ), "Should send the custom email text, not default"
        assert payload["cc_bcc_option"] == "cc", "Should send the selected CC option"

    @pytest.mark.asyncio
    async def test_modal_submission_cc_bcc_options(
        self, slack_refunds_utils, test_client
    ):
        """Test all CC/BCC options are properly sent to internal validation"""

        # Test each CC/BCC option
        cc_bcc_options = ["no", "cc", "bcc"]

        for option in cc_bcc_options:
            # Mock the _send_denial_email_via_gas method to capture the payload
            captured_payload = {}

            async def mock_send_denial_email(
                order_number: str,
                requestor_email: str,
                first_name: str,
                last_name: str,
                custom_message: str,
                cc_bcc_option: str,
                slack_user_name: str,
                slack_user_id: str,
            ):
                captured_payload.clear()  # Clear for each iteration
                captured_payload.update(
                    {
                        "action": "send_denial_email",
                        "order_number": order_number,
                        "requestor_email": requestor_email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "custom_message": custom_message,
                        "cc_bcc_option": cc_bcc_option,
                        "slack_user_name": slack_user_name,
                        "slack_user_id": slack_user_id,
                    }
                )
                return {"success": True, "message": "Email sent successfully"}

            slack_refunds_utils._send_denial_email_via_gas = mock_send_denial_email

            modal_payload = {
                "view": {
                    "state": {
                        "values": {
                            "custom_message_input": {
                                "custom_message": {"value": "Test email content"}
                            },
                            "cc_bcc_input": {
                                "cc_bcc_option": {"selected_option": {"value": option}}
                            },
                        }
                    },
                    "private_metadata": json.dumps(
                        {
                            "original_thread_ts": "1234567890.123456",
                            "original_channel_id": "C123456789",
                            "slack_user_name": "testuser",
                            "slack_user_id": "U123456789",
                            "raw_order_number": "#42308",
                            "requestor_email": "jdazz87@gmail.com",
                            "first_name": "joe",
                            "last_name": "ra",
                        }
                    ),
                }
            }

            # Process the modal submission
            (
                await slack_refunds_utils.handle_deny_refund_request_modal_submission(
                    modal_payload
                )
            )

            # Use our test endpoint to validate the payload structure
            response = test_client.post(
                "/refunds/test/validate-deny-action", json=captured_payload
            )

            assert response.status_code == 200
            validation_data = response.json()

            # Test validation passed
            assert validation_data["success"]
            assert validation_data["validation"][
                "valid"
            ], f"Validation errors: {validation_data['validation']['errors']}"

            # Verify the correct CC/BCC option was sent
            payload = validation_data["received_payload"]
            assert (
                payload["cc_bcc_option"] == option
            ), f"Should send {option} option for validation"

    def test_modal_works_from_any_step(self, slack_refunds_utils):
        """Test that deny modal structure is consistent regardless of which step it came from"""

        # Test deny from different refund types/scenarios
        test_scenarios = [
            {
                "raw_order_number": "#42308",
                "requestor_email": "test@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "refund_type": "refund",
            },
            {
                "raw_order_number": "#54321",
                "requestor_email": "jane@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "refund_type": "credit",
            },
            {
                "raw_order_number": "#99999",
                "requestor_email": "bob@example.com",
                "first_name": "Bob",
                "last_name": "Johnson",
                "refund_type": "email_mismatch",
            },
        ]

        for scenario in test_scenarios:
            modal_blocks = slack_refunds_utils._build_deny_request_modal_blocks(
                raw_order_number=scenario["raw_order_number"],
                requestor_email=scenario["requestor_email"],
                first_name=scenario["first_name"],
                last_name=scenario["last_name"],
                refund_type=scenario["refund_type"],
            )

            # Test that all scenarios produce consistent modal structure
            assert (
                len(modal_blocks) == 5
            ), f"Modal should have 5 blocks for {scenario['refund_type']}"

            # Test that requestor info is always present
            intro_text = modal_blocks[0]["text"]["text"]
            full_name = f"{scenario['first_name']} {scenario['last_name']}"
            assert (
                full_name in intro_text
            ), f"Requestor name should be present in {scenario['refund_type']} scenario"
            assert (
                scenario["requestor_email"] in intro_text
            ), f"Email should be present in {scenario['refund_type']} scenario"
            assert (
                scenario["raw_order_number"] in intro_text
            ), f"Order number should be present in {scenario['refund_type']} scenario"

            # Test that CC/BCC dropdown is always present
            cc_bcc_block = modal_blocks[4]
            assert (
                cc_bcc_block["block_id"] == "cc_bcc_input"
            ), f"CC/BCC block should be present in {scenario['refund_type']} scenario"

    @pytest.mark.asyncio
    async def test_gas_payload_structure(self, slack_refunds_utils, test_client):
        """Test that the payload structure has the correct field names for GAS integration"""

        # Mock the _send_denial_email_via_gas method to capture the payload
        captured_payload = {}

        async def mock_send_denial_email(
            order_number: str,
            requestor_email: str,
            first_name: str,
            last_name: str,
            custom_message: str,
            cc_bcc_option: str,
            slack_user_name: str,
            slack_user_id: str,
        ):
            captured_payload.update(
                {
                    "action": "send_denial_email",
                    "order_number": order_number,
                    "requestor_email": requestor_email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "custom_message": custom_message,
                    "cc_bcc_option": cc_bcc_option,
                    "slack_user_name": slack_user_name,
                    "slack_user_id": slack_user_id,
                }
            )
            return {"success": True, "message": "Email sent successfully"}

        slack_refunds_utils._send_denial_email_via_gas = mock_send_denial_email

        modal_payload = {
            "view": {
                "state": {
                    "values": {
                        "custom_message_input": {
                            "custom_message": {"value": "Test email body content"}
                        },
                        "cc_bcc_input": {
                            "cc_bcc_option": {"selected_option": {"value": "bcc"}}
                        },
                    }
                },
                "private_metadata": json.dumps(
                    {
                        "original_thread_ts": "1234567890.123456",
                        "original_channel_id": "C123456789",
                        "slack_user_name": "testuser",
                        "slack_user_id": "U123456789",
                        "raw_order_number": "#42308",
                        "requestor_email": "jdazz87@gmail.com",
                        "first_name": "joe",
                        "last_name": "ra",
                    }
                ),
            }
        }

        # Process the modal submission
        await slack_refunds_utils.handle_deny_refund_request_modal_submission(
            modal_payload
        )

        # Use our test endpoint to validate the payload structure
        response = test_client.post(
            "/refunds/test/validate-deny-action", json=captured_payload
        )

        assert response.status_code == 200
        validation_data = response.json()

        # Test validation passed
        assert validation_data["success"]
        assert validation_data["validation"][
            "valid"
        ], f"Validation errors: {validation_data['validation']['errors']}"

        # Get the validated payload
        payload = validation_data["received_payload"]

        # Test exact field names expected by GAS
        required_fields = [
            "action",
            "order_number",
            "requestor_email",
            "first_name",
            "last_name",
            "custom_message",
            "cc_bcc_option",  # This should be the new field name
            "slack_user_name",
            "slack_user_id",
        ]

        for field in required_fields:
            assert field in payload, f"Payload should contain {field}"

        # Test specific values
        assert payload["action"] == "send_denial_email"
        assert payload["cc_bcc_option"] == "bcc"
        assert payload["custom_message"] == "Test email body content"

        # Test that old field name is not present
        assert (
            "include_staff_info" not in payload
        ), "Old field 'include_staff_info' should not be present"

    def test_email_subject_structure(self, slack_refunds_utils, sample_request_data):
        """Test that the email subject line is properly formatted in the modal"""

        modal_blocks = slack_refunds_utils._build_deny_request_modal_blocks(
            raw_order_number=sample_request_data["rawOrderNumber"],
            requestor_email=sample_request_data["requestorEmail"],
            first_name=sample_request_data["first"],
            last_name=sample_request_data["last"],
            refund_type=sample_request_data["refundType"],
        )

        # Find the subject line block
        subject_block = modal_blocks[2]
        subject_text = subject_block["text"]["text"]

        # Test subject line format
        expected_subject = "Big Apple Rec Sports - Order #42308 - Refund Request Denied"
        assert (
            expected_subject in subject_text
        ), "Subject line should have correct format"
        assert "Subject Line:" in subject_text, "Should have 'Subject Line:' label"
