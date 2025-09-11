#!/usr/bin/env python3
"""
Unit tests for error codes that test router functions directly with mocked services
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from models.requests import RefundSlackNotificationRequest

@pytest.fixture
def mock_orders_service():
    """Mock the OrdersService for unit tests"""
    with patch('routers.refunds.orders_service') as mock_service:
        yield mock_service

@pytest.fixture
def mock_slack_service():
    """Mock the SlackService for unit tests"""
    with patch('routers.refunds.slack_service') as mock_service:
        yield mock_service

@pytest.mark.asyncio
class TestRefundRouterErrorCodes:
    """Unit tests for refund router error codes"""
    
    async def test_order_not_found_406(self, mock_orders_service, mock_slack_service):
        """Test that order not found returns 406 status code"""
        from routers.refunds import send_refund_to_slack
        
        # Mock orders service to return failure (no order found)
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": False,
            "message": "Order not found"
        }
        
        request = RefundSlackNotificationRequest(
            order_number="#99999999",
            requestor_name={"first": "John", "last": "Doe"},
            requestor_email="john.doe@example.com",
            refund_type="refund",
            notes="Test order not found",
            sheet_link="https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A5"
        )
        
        # Should raise HTTPException with 406 status code
        with pytest.raises(HTTPException) as exc_info:
            await send_refund_to_slack(request)
        
        assert exc_info.value.status_code == 406
        assert "not found" in str(exc_info.value.detail).lower()
        
        # Verify orders service was called but slack service was called for error notification
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(order_name="#99999999")
        mock_slack_service.send_refund_request_notification.assert_called_once()
        
        print("✅ Order not found unit test passed - raised 406!")

    async def test_email_mismatch_409(self, mock_orders_service, mock_slack_service):
        """Test that email mismatch returns 409 status code"""
        from routers.refunds import send_refund_to_slack
        
        # Mock orders service to return an order with different email
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": 12345,
                "name": "#12345",
                "customer": {"email": "real.customer@example.com"},
                "line_items": [{"title": "Test Product"}],
                "total_price": "25.00"
            }
        }
        
        request = RefundSlackNotificationRequest(
            order_number="#12345",
            requestor_name={"first": "Jane", "last": "Smith"},
            requestor_email="wrong.email@example.com",  # Mismatched email
            refund_type="credit",
            notes="Test email mismatch",
            sheet_link="https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A6"
        )
        
        # Should raise HTTPException with 409 status code
        with pytest.raises(HTTPException) as exc_info:
            await send_refund_to_slack(request)
        
        assert exc_info.value.status_code == 409
        assert ("email mismatch" in str(exc_info.value.detail).lower() or 
                "does not match" in str(exc_info.value.detail).lower())
        
        # Verify services were called correctly
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(order_name="#12345")
        mock_slack_service.send_refund_request_notification.assert_called_once()
        
        print("✅ Email mismatch unit test passed - raised 409!")

    async def test_successful_request_200(self, mock_orders_service, mock_slack_service):
        """Test a successful request returns 200 and calls Slack"""
        from routers.refunds import send_refund_to_slack
        
        # Mock orders service to return a matching order
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": 12345,
                "name": "#12345",
                "customer": {"email": "valid.user@example.com"},
                "line_items": [{"title": "Test Product"}],
                "total_price": "25.00"
            }
        }
        
        # Mock check_existing_refunds to return no existing refunds
        mock_orders_service.check_existing_refunds.return_value = {
            "success": True,
            "has_refunds": False,
            "total_refunds": 0,
            "refunds": []
        }
        
        # Mock calculate_refund_due method
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 25.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock Slack service to return success
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": True,
            "message": "Slack message sent successfully"
        }
        
        request = RefundSlackNotificationRequest(
            order_number="#12345",
            requestor_name={"first": "Valid", "last": "User"},
            requestor_email="valid.user@example.com",  # Matching email
            refund_type="refund",
            notes="Test successful request",
            sheet_link="https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A7"
        )
        
        # Should succeed and return success response
        result = await send_refund_to_slack(request)
        
        assert result["success"] == True
        assert "message" in result
        assert result["data"]["order_number"] == "#12345"
        assert result["data"]["refund_amount"] == 25.00
        
        # Verify both services were called
        mock_orders_service.fetch_order_details_by_email_or_order_name.assert_called_once_with(order_name="#12345")
        mock_orders_service.calculate_refund_due.assert_called_once()
        mock_slack_service.send_refund_request_notification.assert_called_once()
        
        print("✅ Successful request unit test passed - returned 200!")

    async def test_slack_service_failure(self, mock_orders_service, mock_slack_service):
        """Test that Slack service failure is handled correctly"""
        from routers.refunds import send_refund_to_slack
        
        # Mock orders service to return a valid order
        mock_orders_service.fetch_order_details_by_email_or_order_name.return_value = {
            "success": True,
            "data": {
                "id": 12345,
                "name": "#12345",
                "customer": {"email": "valid.user@example.com"},
                "line_items": [{"title": "Test Product"}],
                "total_price": "25.00"
            }
        }
        
        # Mock calculate_refund_due method
        mock_orders_service.calculate_refund_due.return_value = {
            "success": True,
            "refund_amount": 25.00,
            "message": "Refund calculated successfully"
        }
        
        # Mock Slack service to return failure
        mock_slack_service.send_refund_request_notification.return_value = {
            "success": False,
            "error": "Slack API error"
        }
        
        request = RefundSlackNotificationRequest(
            order_number="#12345",
            requestor_name={"first": "Valid", "last": "User"},
            requestor_email="valid.user@example.com",
            refund_type="refund",
            notes="Test Slack failure",
            sheet_link="https://docs.google.com/spreadsheets/d/test/edit#gid=1&range=A8"
        )
        
        # Should raise HTTPException with 500 status code
        with pytest.raises(HTTPException) as exc_info:
            await send_refund_to_slack(request)
        
        assert exc_info.value.status_code == 500
        detail = exc_info.value.detail
        if isinstance(detail, dict):
            assert "slack" in str(detail.get("message", "")).lower()
        else:
            assert "slack" in str(detail).lower()
        
        print("✅ Slack service failure unit test passed - raised 500!")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 