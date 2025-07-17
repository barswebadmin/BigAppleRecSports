#!/usr/bin/env python3
"""
Simple test script for the orders API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.orders import OrdersService

def test_orders_service():
    """Test the OrdersService functionality"""
    print("Testing OrdersService...")
    
    try:
        orders_service = OrdersService()
        print("✅ OrdersService initialized successfully")
        
        # Test fetching order details (this will likely fail without a real order)
        test_order = "#1001"  # Replace with a real order number
        print(f"Testing order lookup for: {test_order}")
        
        result = orders_service.fetch_order_details_by_email_or_order_name(order_name=test_order)
        print(f"Order lookup result: {result}")
        
        if result["success"]:
            print("✅ Order found successfully")
            
            # Test refund calculation
            refund_calc = orders_service.calculate_refund_due(result["data"], "refund")
            print(f"Refund calculation: {refund_calc}")
            
            # Test inventory summary
            inventory = orders_service.get_inventory_summary(result["data"])
            print(f"Inventory summary: {inventory}")
            
        else:
            print(f"⚠️ Order not found (expected for test): {result['message']}")
        
        print("✅ All OrdersService tests completed")
        return True
        
    except Exception as e:
        print(f"❌ OrdersService test failed: {str(e)}")
        print(f"Error details: {e.__class__.__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_date_utils():
    """Test the date utility functions"""
    print("\nTesting date utilities...")
    
    try:
        from utils.date_utils import extract_season_dates, calculate_refund_amount
        
        # Test season date extraction
        sample_html = """
        <p>Season Dates: 1/15/25 - 3/15/25 (8 weeks, off 2/15/25)</p>
        """
        
        start_date, off_dates = extract_season_dates(sample_html)
        print(f"Extracted dates - Start: {start_date}, Off: {off_dates}")
        
        if start_date:
            # Test refund calculation
            refund_amount, refund_text = calculate_refund_amount(
                start_date, off_dates, 100.0, "refund"
            )
            print(f"Refund calculation - Amount: {refund_amount}, Text: {refund_text}")
        
        print("✅ Date utilities test completed")
        return True
        
    except Exception as e:
        print(f"❌ Date utilities test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

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