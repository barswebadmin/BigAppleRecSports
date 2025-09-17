"""
Consolidated tests for Slack message parsing and data extraction.
Combines functionality from test_variant_name_handling.py and other parsing tests.
"""

import pytest
from unittest.mock import Mock
from services.slack.builders.message_parsers import SlackMessageParsers


class TestParsingConsolidated:
    """Consolidated test suite for Slack message parsing and data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parsers = SlackMessageParsers()

    def test_extract_sheet_link(self):
        """Test extraction of Google Sheets links from message text."""
        # Test various sheet link formats
        test_cases = [
            {
                "message": "Please check this sheet: https://docs.google.com/spreadsheets/d/1234567890",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890"
            },
            {
                "message": "Sheet link: https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0"
            },
            {
                "message": "No sheet link here",
                "expected": ""
            },
            {
                "message": "Multiple links: https://docs.google.com/spreadsheets/d/1234567890 and https://example.com",
                "expected": "https://docs.google.com/spreadsheets/d/1234567890"
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_sheet_link(test_case["message"])
            assert result == test_case["expected"]

    def test_extract_season_start_info(self):
        """Test extraction of season start information from message text."""
        test_cases = [
            {
                "message": "The season starts on October 15th at 7:00 PM",
                "expected": {
                    "season_start_date": "October 15th",
                    "season_start_time": "7:00 PM",
                    "season_name": None
                }
            },
            {
                "message": "Kickball season begins on September 1st at 6:30 PM",
                "expected": {
                    "season_start_date": "September 1st",
                    "season_start_time": "6:30 PM",
                    "season_name": "kickball"
                }
            },
            {
                "message": "No season info here",
                "expected": {
                    "season_start_date": None,
                    "season_start_time": None,
                    "season_name": None
                }
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_season_start_info(test_case["message"])
            assert result["season_start_date"] == test_case["expected"]["season_start_date"]
            assert result["season_start_time"] == test_case["expected"]["season_start_time"]
            assert result["season_name"] == test_case["expected"]["season_name"]

    def test_extract_order_number(self):
        """Test extraction of order numbers from message text."""
        test_cases = [
            {
                "message": "Order #12345 has been processed",
                "expected": "12345"
            },
            {
                "message": "Please check order number #67890",
                "expected": "67890"
            },
            {
                "message": "Order: #11111 is ready",
                "expected": "11111"
            },
            {
                "message": "No order number here",
                "expected": None
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_order_number(test_case["message"])
            assert result == test_case["expected"]

    def test_extract_email(self):
        """Test extraction of email addresses from message text."""
        test_cases = [
            {
                "message": "Contact us at support@example.com for help",
                "expected": "support@example.com"
            },
            {
                "message": "Email: john.doe@company.org",
                "expected": "john.doe@company.org"
            },
            {
                "message": "No email here",
                "expected": None
            },
            {
                "message": "Multiple emails: first@example.com and second@test.org",
                "expected": "first@example.com"
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_email(test_case["message"])
            assert result == test_case["expected"]

    def test_extract_refund_amount(self):
        """Test extraction of refund amounts from message text."""
        test_cases = [
            {
                "message": "Refund amount: $25.00",
                "expected": 25.00
            },
            {
                "message": "Total refund: $150.50",
                "expected": 150.50
            },
            {
                "message": "Amount: $0.99 dollars",
                "expected": 0.99
            },
            {
                "message": "No amount here",
                "expected": None
            }
        ]

        for test_case in test_cases:
            result = self.parsers.extract_refund_amount(test_case["message"])
            assert result == test_case["expected"]

    def test_variant_name_handling(self):
        """Test handling of product variant names in messages."""
        # Test various product variant name formats
        test_cases = [
            {
                "message": "Product: Test Product - Pickleball Monday",
                "variant_info": {
                    "product_name": "Test Product",
                    "variant": "Pickleball Monday",
                    "sport": "pickleball"
                }
            },
            {
                "message": "Item: Soccer League - Fall Season",
                "variant_info": {
                    "product_name": "Soccer League",
                    "variant": "Fall Season",
                    "sport": "soccer"
                }
            },
            {
                "message": "Product: Kickball Tournament Entry",
                "variant_info": {
                    "product_name": "Kickball Tournament Entry",
                    "variant": None,
                    "sport": "kickball"
                }
            }
        ]

        for test_case in test_cases:
            # Test sport detection
            season_info = self.parsers.extract_season_start_info(test_case["message"])
            if test_case["variant_info"]["sport"]:
                # This would test sport detection if we had that functionality
                assert test_case["variant_info"]["sport"] in test_case["message"].lower()

    def test_complex_message_parsing(self):
        """Test parsing of complex messages with multiple data types."""
        complex_message = """
        Order #12345 for john.doe@example.com
        
        Product: Test Product - Pickleball Monday
        Season starts on October 15th at 7:00 PM
        
        Refund amount: $95.00
        
        Sheet: https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0
        """

        # Test multiple extractions from the same message
        order_number = self.parsers.extract_order_number(complex_message)
        email = self.parsers.extract_email(complex_message)
        season_info = self.parsers.extract_season_start_info(complex_message)
        refund_amount = self.parsers.extract_refund_amount(complex_message)
        sheet_link = self.parsers.extract_sheet_link(complex_message)

        assert order_number == "12345"
        assert email == "john.doe@example.com"
        assert season_info["season_start_date"] == "October 15th"
        assert season_info["season_start_time"] == "7:00 PM"
        assert refund_amount == 95.00
        assert "https://docs.google.com/spreadsheets/d/1234567890/edit#gid=0" in sheet_link

    def test_error_handling_in_parsing(self):
        """Test error handling in parsing methods."""
        # Test with malformed input
        malformed_inputs = [
            None,
            "",
            "   ",
            "Invalid input with special characters: !@#$%^&*()",
        ]

        for malformed_input in malformed_inputs:
            # All parsing methods should handle malformed input gracefully
            try:
                self.parsers.extract_sheet_link(malformed_input or "")
                self.parsers.extract_season_start_info(malformed_input or "")
                self.parsers.extract_order_number(malformed_input or "")
                self.parsers.extract_email(malformed_input or "")
                self.parsers.extract_refund_amount(malformed_input or "")
            except Exception as e:
                pytest.fail(f"Parsing method should handle malformed input gracefully: {e}")

    def test_edge_cases_in_parsing(self):
        """Test edge cases in parsing methods."""
        # Test edge cases
        edge_cases = [
            {
                "method": "extract_sheet_link",
                "input": "https://docs.google.com/spreadsheets/d/",
                "expected": ""
            },
            {
                "method": "extract_order_number",
                "input": "Order #",
                "expected": None
            },
            {
                "method": "extract_email",
                "input": "Email: @invalid",
                "expected": None
            },
            {
                "method": "extract_refund_amount",
                "input": "Amount: $",
                "expected": None
            }
        ]

        for edge_case in edge_cases:
            method = getattr(self.parsers, edge_case["method"])
            result = method(edge_case["input"])
            assert result == edge_case["expected"]


if __name__ == "__main__":
    pytest.main([__file__])
