"""
Unit tests for ScheduleChangesForShopifyProductsLambda
"""

import json
from unittest.mock import patch, MagicMock
from lambda_function import lambda_handler

class TestScheduleChangesForShopifyProductsLambda:
    """Test cases for the main lambda handler"""
    
    def test_missing_action_type(self):
        """Test that missing actionType returns 400 error"""
        event = {
            "body": json.dumps({
                "scheduleName": "test-schedule",
                "groupName": "test-group"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Missing required field: actionType" in response_body["message"]
    
    def test_unsupported_action_type(self):
        """Test that unsupported actionType returns 422 error"""
        event = {
            "body": json.dumps({
                "actionType": "unsupported-action",
                "scheduleName": "test-schedule"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 422
        response_body = json.loads(result["body"])
        assert "Unsupported actionType" in response_body["message"]
        assert "supported_action_types" in response_body["details"]
        assert len(response_body["details"]["supported_action_types"]) == 3
    
    @patch('inventory_movement_scheduler.create_scheduled_inventory_movements')
    def test_inventory_movement_success(self, mock_create_inventory):
        """Test successful inventory movement scheduling"""
        # Mock the inventory scheduler response
        mock_create_inventory.return_value = {
            "message": "✅ Schedule 'test-inventory-move' created successfully!",
            "new_expression": "at(2024-01-01T10:00:00)",
            "aws_response": {"ScheduleArn": "arn:aws:scheduler:us-east-1:123456789012:schedule/test-group/test-inventory-move"}
        }
        
        event = {
            "body": json.dumps({
                "actionType": "create-scheduled-inventory-movements",
                "scheduleName": "test-inventory-move",
                "groupName": "move-inventory-between-variants-kb",
                "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
                "sourceVariant": {
                    "type": "early",
                    "name": "Early Registration",
                    "gid": "gid://shopify/ProductVariant/111111111"
                },
                "destinationVariant": {
                    "type": "open",
                    "name": "Open Registration", 
                    "gid": "gid://shopify/ProductVariant/222222222"
                },
                "newDatetime": "2024-01-01T10:00:00",
                "note": "Test inventory move"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 201
        response_body = json.loads(result["body"])
        assert response_body["success"] is True
        assert "Schedule 'test-inventory-move' created successfully!" in response_body["data"]["message"]
        
        # Verify the inventory scheduler was called with correct parameters
        mock_create_inventory.assert_called_once()
        call_args = mock_create_inventory.call_args[0][0]
        assert call_args["actionType"] == "create-scheduled-inventory-movements"
        assert call_args["scheduleName"] == "test-inventory-move"
    
    @patch('price_change_scheduler.create_scheduled_price_changes')
    def test_price_change_success(self, mock_create_price):
        """Test successful price change scheduling"""
        # Mock the price scheduler response
        mock_create_price.return_value = {
            "message": "✅ All price change schedules updated successfully!",
            "price_schedule": [
                {"timestamp": "2024-01-01T10:00:00", "updated_price": 115},
                {"timestamp": "2024-01-08T10:00:00", "updated_price": 103.5},
                {"timestamp": "2024-01-15T10:00:00", "updated_price": 92},
                {"timestamp": "2024-01-22T10:00:00", "updated_price": 80.5}
            ]
        }
        
        event = {
            "body": json.dumps({
                "actionType": "create-scheduled-price-changes",
                "sport": "Kickball",
                "day": "Monday",
                "division": "Social",
                "productGid": "gid://shopify/Product/123456789",
                "openVariantGid": "gid://shopify/ProductVariant/111111111",
                "waitlistVariantGid": "gid://shopify/ProductVariant/222222222",
                "price": 115,
                "seasonStartDate": "2024-01-01",
                "sportStartTime": "21:00:00",
                "offDatesCommaSeparated": "2024-01-15"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 200
        response_body = json.loads(result["body"])
        assert response_body["success"] is True
        assert "All price change schedules updated successfully!" in response_body["data"]["message"]
        
        # Verify the price scheduler was called with correct parameters
        mock_create_price.assert_called_once()
        call_args = mock_create_price.call_args[0][0]
        assert call_args["actionType"] == "create-scheduled-price-changes"
        assert call_args["sport"] == "Kickball"
        assert call_args["price"] == 115
    
    @patch('inventory_addition_scheduler.create_initial_inventory_addition_and_title_change')
    def test_inventory_addition_and_title_change_success(self, mock_create_addition):
        """Test successful inventory addition and title change scheduling"""
        # Mock the inventory addition scheduler response
        mock_create_addition.return_value = {
            "message": "✅ Schedule 'auto-set-123456789-kb-monday-socialdiv-live' created successfully!",
            "new_expression": "at(2024-01-01T10:00:00)",
            "lambda_input": {
                "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
                "productTitle": "Big Apple Kickball - Monday - Social Division - Fall 2024",
                "variantGid": "gid://shopify/ProductVariant/111111111",
                "inventoryToAdd": 180
            },
            "aws_response": {"ScheduleArn": "arn:aws:scheduler:us-east-1:123456789012:schedule/set-product-live/auto-set-123456789-kb-monday-socialdiv-live"}
        }
        
        event = {
            "body": json.dumps({
                "actionType": "create-initial-inventory-addition-and-title-change",
                "scheduleName": "auto-set-123456789-kb-monday-socialdiv-live",
                "groupName": "set-product-live",
                "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
                "productTitle": "Big Apple Kickball - Monday - Social Division - Fall 2024",
                "variantGid": "gid://shopify/ProductVariant/111111111",
                "inventoryToAdd": 180,
                "newDatetime": "2024-01-01T10:00:00",
                "note": "Test inventory addition and title change"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 201
        response_body = json.loads(result["body"])
        assert response_body["success"] is True
        assert "Schedule 'auto-set-123456789-kb-monday-socialdiv-live' created successfully!" in response_body["data"]["message"]
        
        # Verify the inventory addition scheduler was called with correct parameters
        mock_create_addition.assert_called_once()
        call_args = mock_create_addition.call_args[0][0]
        assert call_args["actionType"] == "create-initial-inventory-addition-and-title-change"
        assert call_args["scheduleName"] == "auto-set-123456789-kb-monday-socialdiv-live"
        assert call_args["productTitle"] == "Big Apple Kickball - Monday - Social Division - Fall 2024"
        assert call_args["inventoryToAdd"] == 180
    
    @patch('inventory_movement_scheduler.create_scheduled_inventory_movements')
    def test_inventory_movement_validation_error(self, mock_create_inventory):
        """Test validation error in inventory movement"""
        # Mock the inventory scheduler to raise ValueError
        mock_create_inventory.side_effect = ValueError("Missing required field: newDatetime")
        
        event = {
            "body": json.dumps({
                "actionType": "create-scheduled-inventory-movements",
                "scheduleName": "test-schedule",
                "groupName": "test-group"
                # Missing newDatetime
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Missing required field: newDatetime" in response_body["message"]
    
    @patch('price_change_scheduler.create_scheduled_price_changes')
    def test_price_change_validation_error(self, mock_create_price):
        """Test validation error in price change"""
        # Mock the price scheduler to raise ValueError
        mock_create_price.side_effect = ValueError("Missing required field: sport")
        
        event = {
            "body": json.dumps({
                "actionType": "create-scheduled-price-changes",
                "day": "Monday",
                "division": "Social"
                # Missing sport and other required fields
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Missing required field: sport" in response_body["message"]
    
    @patch('inventory_addition_scheduler.create_initial_inventory_addition_and_title_change')
    def test_inventory_addition_validation_error(self, mock_create_addition):
        """Test validation error in inventory addition and title change"""
        # Mock the inventory addition scheduler to raise ValueError
        mock_create_addition.side_effect = ValueError("Missing required parameters: productTitle, inventoryToAdd")
        
        event = {
            "body": json.dumps({
                "actionType": "create-initial-inventory-addition-and-title-change",
                "scheduleName": "test-schedule",
                "groupName": "set-product-live",
                "productUrl": "https://09fe59-3.myshopify.com/admin/products/123456789",
                "variantGid": "gid://shopify/ProductVariant/111111111",
                "newDatetime": "2024-01-01T10:00:00"
                # Missing productTitle and inventoryToAdd
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 400
        response_body = json.loads(result["body"])
        assert "Missing required parameters: productTitle, inventoryToAdd" in response_body["message"]
    
    def test_direct_event_body(self):
        """Test handling of direct event body (not wrapped in 'body' field)"""
        event = {
            "actionType": "unsupported-action",
            "scheduleName": "test-schedule"
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 422
        response_body = json.loads(result["body"])
        assert "Unsupported actionType" in response_body["message"]
    
    @patch('inventory_movement_scheduler.create_scheduled_inventory_movements')
    def test_unexpected_error(self, mock_create_inventory):
        """Test handling of unexpected exceptions"""
        # Mock the inventory scheduler to raise an unexpected exception
        mock_create_inventory.side_effect = Exception("Unexpected AWS error")
        
        event = {
            "body": json.dumps({
                "actionType": "create-scheduled-inventory-movements",
                "scheduleName": "test-schedule",
                "groupName": "test-group",
                "newDatetime": "2024-01-01T10:00:00"
            })
        }
        
        result = lambda_handler(event, {})
        
        assert result["statusCode"] == 500
        response_body = json.loads(result["body"])
        assert "Internal server error" in response_body["message"]
        assert "Unexpected AWS error" in response_body["details"]["error"]

if __name__ == "__main__":
    # Run the tests
    import sys
    import os
    
    # Add current directory to path for imports
    sys.path.insert(0, os.path.dirname(__file__))
    
    test_instance = TestScheduleChangesForShopifyProductsLambda()
    
    print("🧪 Running tests for ScheduleChangesForShopifyProductsLambda...")
    
    try:
        test_instance.test_missing_action_type()
        print("✅ test_missing_action_type passed")
        
        test_instance.test_unsupported_action_type()
        print("✅ test_unsupported_action_type passed")
        
        test_instance.test_inventory_movement_success()
        print("✅ test_inventory_movement_success passed")
        
        test_instance.test_price_change_success()
        print("✅ test_price_change_success passed")
        
        test_instance.test_inventory_addition_and_title_change_success()
        print("✅ test_inventory_addition_and_title_change_success passed")
        
        test_instance.test_inventory_movement_validation_error()
        print("✅ test_inventory_movement_validation_error passed")
        
        test_instance.test_price_change_validation_error()
        print("✅ test_price_change_validation_error passed")
        
        test_instance.test_inventory_addition_validation_error()
        print("✅ test_inventory_addition_validation_error passed")
        
        test_instance.test_direct_event_body()
        print("✅ test_direct_event_body passed")
        
        test_instance.test_unexpected_error()
        print("✅ test_unexpected_error passed")
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
