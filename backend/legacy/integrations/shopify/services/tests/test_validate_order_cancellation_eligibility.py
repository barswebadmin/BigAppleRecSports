"""
Tests for ShopifyService.validate_order_cancellation_eligibility()

Tests verify that the method:
1. Calls get_order_by_identifier() internally
2. Returns error response if order fetch fails
3. Checks cancelledAt field to determine eligibility
4. Returns warning status (409) if already canceled
5. Returns success status (200) with full order data if eligible
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from modules.integrations.shopify.services.shopify_service import ShopifyService


class TestValidateOrderCancellationEligibility:
    """Test suite for validate_order_cancellation_eligibility method."""
    
    @pytest.fixture
    def shopify_service(self):
        """Create ShopifyService instance for testing."""
        return ShopifyService(environment="production")
    
    @pytest.fixture
    def mock_order_eligible(self):
        """Mock order that is eligible for cancellation (cancelledAt is None)."""
        order = Mock()
        order.id = "gid://shopify/Order/1234567890"
        order.name = "#12345"
        order.cancelledAt = None
        order.cancelReason = None
        order.totalPriceSet = Mock()
        order.totalPriceSet.presentmentMoney = Mock()
        order.totalPriceSet.presentmentMoney.amount = "115.0"
        order.lineItems = Mock()
        order.lineItems.nodes = []
        order.refunds = []
        return order
    
    @pytest.fixture
    def mock_order_already_canceled(self):
        """Mock order that is already canceled (cancelledAt is not None)."""
        order = Mock()
        order.id = "gid://shopify/Order/1234567890"
        order.name = "#12345"
        order.cancelledAt = "2026-01-09T23:15:37Z"
        order.cancelReason = "CUSTOMER"
        order.totalPriceSet = Mock()
        order.totalPriceSet.presentmentMoney = Mock()
        order.totalPriceSet.presentmentMoney.amount = "115.0"
        order.lineItems = Mock()
        order.lineItems.nodes = []
        order.refunds = []
        return order
    
    def test_order_eligible_for_cancellation(self, shopify_service, mock_order_eligible):
        """Test that eligible order returns 200 status with full order data."""
        identifier = {"identifier": "12345", "query": "name:#12345"}
        
        with patch.object(shopify_service, 'get_order_by_identifier', return_value=[mock_order_eligible]):
            result = shopify_service.validate_order_cancellation_eligibility(identifier)
        
        assert result["status_code"] == 200
        assert result["success"] is True
        assert "order" in result
        assert result["order"] == mock_order_eligible
        assert "message" in result
        assert "eligible" in result["message"].lower()
    
    def test_order_already_canceled(self, shopify_service, mock_order_already_canceled):
        """Test that already canceled order returns 409 status with warning."""
        identifier = {"identifier": "12345", "query": "name:#12345"}
        
        with patch.object(shopify_service, 'get_order_by_identifier', return_value=[mock_order_already_canceled]):
            result = shopify_service.validate_order_cancellation_eligibility(identifier)
        
        assert result["status_code"] == 409
        assert result["success"] is False
        assert "message" in result
        assert "already canceled" in result["message"].lower()
        assert "order" in result
        assert result["order"] == mock_order_already_canceled
    
    def test_order_not_found(self, shopify_service):
        """Test that order not found returns 404 status."""
        identifier = {"identifier": "99999", "query": "name:#99999"}
        
        with patch.object(shopify_service, 'get_order_by_identifier', side_effect=ValueError("No orders found")):
            result = shopify_service.validate_order_cancellation_eligibility(identifier)
        
        assert result["status_code"] == 404
        assert result["success"] is False
        assert "message" in result
        assert ("not found" in result["message"].lower() or "no orders found" in result["message"].lower())
    
    def test_order_fetch_error(self, shopify_service):
        """Test that order fetch error returns 500 status."""
        identifier = {"identifier": "12345", "query": "name:#12345"}
        
        with patch.object(shopify_service, 'get_order_by_identifier', side_effect=RuntimeError("GraphQL error")):
            result = shopify_service.validate_order_cancellation_eligibility(identifier)
        
        assert result["status_code"] == 500
        assert result["success"] is False
        assert "message" in result
        assert "error" in result["message"].lower()
    
    def test_empty_orders_list(self, shopify_service):
        """Test that empty orders list returns 404 status."""
        identifier = {"identifier": "12345", "query": "name:#12345"}
        
        with patch.object(shopify_service, 'get_order_by_identifier', return_value=[]):
            result = shopify_service.validate_order_cancellation_eligibility(identifier)
        
        assert result["status_code"] == 404
        assert result["success"] is False
        assert "message" in result
        assert "not found" in result["message"].lower()
