#!/usr/bin/env python3
"""
Simple test script for the orders API
"""

import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.orders.services import OrdersService

def test_orders_service():
    """Test the OrdersService functionality"""
    print("Testing OrdersService...")
    
    try:
        orders_service = OrdersService()
        print("✅ OrdersService initialized successfully")
        
        # Test fetching order details (this will likely fail without a real order)
        test_order = "#1001"  # Replace with a real order number
        print(f"Testing order lookup for: {test_order}")
        
        result = orders_service.fetch_order_details_by_email_or_order_number(order_number=test_order)
        print(f"Order lookup result: {result}")
        
        if result["success"]:
            print("✅ Order found successfully")
            
            # Test refund calculation
            refund_calc = orders_service.calculate_refund_due(result["data"], "refund")
            print(f"Refund calculation: {refund_calc}")
            
            # Test inventory summary
            # inventory = orders_service.get_inventory_summary(result["data"])
            # print(f"Inventory summary: {inventory}")
            
        else:
            print(f"⚠️ Order not found (expected for test): {result['message']}")
        
        print("✅ All OrdersService tests completed")
        
    except Exception as e:
        print(f"❌ OrdersService test failed: {str(e)}")
        print(f"Error details: {e.__class__.__name__}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"OrdersService test failed: {str(e)}")

def test_date_utils():
    """Test the date utility functions"""
    print("\nTesting date utilities...")
    
    try:
        from lib.domain.registrations.refunds import (
            SeasonDates,
            EstimateTierKind,
            calculate_estimated_refund_due,
        )
        
        sample_html = """
        <p>Season Dates: 1/15/25 - 3/15/25 (8 weeks, off 2/15/25)</p>
        """
        
        season_dates = SeasonDates.from_html(sample_html)
        if season_dates:
            print(f"Extracted dates - Start: {season_dates.start_date_str}, Off: {season_dates.off_dates_str}")
            
            refund_amount, refund_text = calculate_estimated_refund_due(
                season_dates=season_dates,
                total_paid=100.0,
                tier_kind=EstimateTierKind.REFUND,
            )
            print(f"Refund calculation - Amount: {refund_amount}, Text: {refund_text}")
        else:
            print("Could not extract season dates from HTML")
        
        print("✅ Date utilities test completed")
        
    except Exception as e:
        print(f"❌ Date utilities test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Date utilities test failed: {str(e)}")

if __name__ == "__main__":
    print("=== BARS Orders API Test ===")
    
    # Test date utilities first (no external dependencies)
    date_test_passed = test_date_utils()
    
    # Test orders service (requires Shopify connection)
    orders_test_passed = test_orders_service()
    
    print("\n=== Test Summary ===")
    print(f"Date utilities: {'✅ PASSED' if date_test_passed else '❌ FAILED'}")
    print(f"Orders service: {'✅ PASSED' if orders_test_passed else '❌ FAILED'}")
    
    if date_test_passed and orders_test_passed:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed")
        sys.exit(1) 