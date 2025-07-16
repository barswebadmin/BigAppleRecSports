"""
Unit tests for MoveInventoryLambda function.

Tests individual components and the main lambda handler with mocked
dependencies.
"""

import pytest
import sys
import os
from unittest.mock import patch

# Add the specific lambda function to path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), '../../MoveInventoryLambda')
)

from lambda_function import lambda_handler  # type: ignore


class TestMoveInventoryLambda:
    """Test suite for MoveInventoryLambda"""

    def test_veteran_to_early_move(self, mock_shopify_utils,
                                   sample_move_inventory_event,
                                   sample_lambda_context):
        """Test moving inventory from veteran to early variant"""
        # Setup mocks
        mock_shopify_utils['get_inventory_item_and_quantity'].side_effect = [
            {'inventoryItemId': 'item_11111', 'inventoryQuantity': 5},
            {'inventoryItemId': 'item_22222', 'inventoryQuantity': 0}
        ]

        # Mock wait_until_next_minute to avoid delays in tests
        with patch('bars_common_utils.request_utils.wait_until_next_minute') \
                as mock_wait:
            result = lambda_handler(sample_move_inventory_event,
                                    sample_lambda_context)

        # Assertions
        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Moved all 5 units' in response_body['message']

        # Verify inventory adjustments were called
        assert mock_shopify_utils['adjust_inventory'].call_count == 2
        mock_shopify_utils['adjust_inventory'].assert_any_call(
            'item_11111', -5)  # remove from source
        mock_shopify_utils['adjust_inventory'].assert_any_call(
            'item_22222', 5)   # add to destination

        # Verify wait was called
        mock_wait.assert_called_once()

    def test_early_vet_to_open_consolidation(self, mock_shopify_utils,
                                             sample_lambda_context):
        """Test consolidating early/veteran inventory to open variant"""
        # Create event for early/vet -> open move
        event = {
            'scheduleName': 'test-schedule',
            'productUrl': 'https://admin.shopify.com/store/test/products/12345',
            'sourceVariant': {
                'name': 'Early/Vet Consolidation',
                # This will trigger get_product_variants
                'gid': 'gid://shopify/ProductVariant/12345',
                'type': 'consolidation'
            },
            'destinationVariant': {
                'name': 'Open',
                'gid': 'gid://shopify/ProductVariant/33333',
                'type': 'open'
            }
        }

        # Setup destination variant mock
        mock_shopify_utils['get_inventory_item_and_quantity'].return_value = {
            'inventoryItemId': 'item_33333',
            'inventoryQuantity': 0
        }

        with patch('bars_common_utils.request_utils.wait_until_next_minute'):
            result = lambda_handler(event, sample_lambda_context)

        # Should consolidate early (5) + veteran (3) = 8 units to open
        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Moved 8 units into Open' in response_body['message']

        # Verify consolidation calls
        assert mock_shopify_utils['get_product_variants'].called
        # 2 removals + 1 addition
        assert mock_shopify_utils['adjust_inventory'].call_count == 3

    def test_custom_to_custom_move(self, mock_shopify_utils,
                                   sample_lambda_context):
        """Test custom variant to custom variant move"""
        event = {
            'scheduleName': 'test-schedule',
            'productUrl': 'https://admin.shopify.com/store/test/products/12345',
            'sourceVariant': {
                'name': 'Custom Source',
                'gid': 'gid://shopify/ProductVariant/44444',
                'type': 'custom'
            },
            'destinationVariant': {
                'name': 'Custom Destination',
                'gid': 'gid://shopify/ProductVariant/55555',
                'type': 'custom'
            }
        }

        # Setup mocks for custom move
        mock_shopify_utils['get_inventory_item_and_quantity'].side_effect = [
            {'inventoryItemId': 'item_44444', 'inventoryQuantity': 12},
            {'inventoryItemId': 'item_55555', 'inventoryQuantity': 0}
        ]

        with patch('bars_common_utils.request_utils.wait_until_next_minute'):
            result = lambda_handler(event, sample_lambda_context)

        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Moved all 12 units' in response_body['message']

    def test_no_inventory_to_move_error(self, mock_shopify_utils,
                                        sample_move_inventory_event,
                                        sample_lambda_context):
        """Test error when source variant has no inventory"""
        # Mock source with 0 inventory
        mock_shopify_utils['get_inventory_item_and_quantity'].side_effect = [
            {'inventoryItemId': 'item_11111', 'inventoryQuantity': 0},
            {'inventoryItemId': 'item_22222', 'inventoryQuantity': 0}
        ]

        result = lambda_handler(sample_move_inventory_event,
                                sample_lambda_context)

        assert result['statusCode'] == 500
        response_body = result['body']
        assert 'No inventory to move' in response_body['error']

    def test_missing_required_fields_error(self, sample_lambda_context):
        """Test error when required fields are missing"""
        incomplete_event = {
            'scheduleName': 'test-schedule',
            # Missing productUrl, sourceVariant, destinationVariant
        }

        result = lambda_handler(incomplete_event, sample_lambda_context)

        assert result['statusCode'] == 500
        response_body = result['body']
        assert 'error' in response_body

    def test_unsupported_move_type_error(self, mock_shopify_utils,
                                         sample_lambda_context):
        """Test error for unsupported source->destination move types"""
        event = {
            'scheduleName': 'test-schedule',
            'productUrl': 'https://admin.shopify.com/store/test/products/12345',
            'sourceVariant': {
                'name': 'Unknown Type',
                'gid': 'gid://shopify/ProductVariant/99999',
                'type': 'unknown'
            },
            'destinationVariant': {
                'name': 'Another Unknown',
                'gid': 'gid://shopify/ProductVariant/88888',
                'type': 'unknown'
            }
        }

        result = lambda_handler(event, sample_lambda_context)

        assert result['statusCode'] == 500
        response_body = result['body']
        assert 'Unsupported source→destination move' in response_body['error']

    def test_shopify_api_error_handling(self, mock_shopify_utils,
                                        sample_move_inventory_event,
                                        sample_lambda_context):
        """Test error handling when Shopify API fails"""
        # Mock Shopify API to raise an exception
        mock_shopify_utils['get_inventory_item_and_quantity'].side_effect = \
            Exception("Shopify API Error")

        result = lambda_handler(sample_move_inventory_event,
                                sample_lambda_context)

        assert result['statusCode'] == 500
        response_body = result['body']
        assert 'error' in response_body

    def test_type_annotations_and_imports(self):
        """Test that the function has proper type annotations and imports"""
        from lambda_function import lambda_handler  # type: ignore
        import inspect

        # Check function signature
        sig = inspect.signature(lambda_handler)
        assert len(sig.parameters) == 2

        # Check that all imports are working (no ImportError)
        assert lambda_handler is not None

    @pytest.mark.parametrize("source_type,dest_type,expected_success", [
        ("veteran", "early", True),
        ("consolidation", "open", True),
        ("custom", "custom", True),
        ("invalid", "invalid", False),
    ])
    def test_move_type_matrix(self, mock_shopify_utils, sample_lambda_context,
                              source_type, dest_type, expected_success):
        """Test different combinations of source and destination types"""
        event = {
            'scheduleName': 'test-schedule',
            'productUrl': 'https://admin.shopify.com/store/test/products/12345',
            'sourceVariant': {
                'name': f'Source {source_type}',
                'gid': 'gid://shopify/ProductVariant/11111',
                'type': source_type
            },
            'destinationVariant': {
                'name': f'Dest {dest_type}',
                'gid': 'gid://shopify/ProductVariant/22222',
                'type': dest_type
            }
        }

        with patch('bars_common_utils.request_utils.wait_until_next_minute'):
            result = lambda_handler(event, sample_lambda_context)

        if expected_success:
            assert result['statusCode'] == 200
        else:
            assert result['statusCode'] == 500 