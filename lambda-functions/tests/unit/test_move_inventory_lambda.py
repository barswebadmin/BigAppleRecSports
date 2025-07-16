"""
Unit tests for MoveInventoryLambda function.

Tests individual components and the main lambda handler with mocked
dependencies.
"""

import pytest
import sys
import os
import importlib
from unittest.mock import patch

# Clear any cached lambda_function modules
modules_to_clear = [mod for mod in sys.modules.keys() if 'lambda_function' in mod]
for mod in modules_to_clear:
    del sys.modules[mod]

# More aggressive path cleaning to avoid conflicts
paths_to_remove = []
for path in sys.path:
    if 'lambda-functions' in path:
        if 'shopifyProductUpdateHandler' in path or 'createScheduledPriceChanges' in path or 'CreateScheduleLambda' in path:
            paths_to_remove.append(path)

for path in paths_to_remove:
    sys.path.remove(path)

# Add the specific lambda function to path
move_inventory_path = os.path.join(os.path.dirname(__file__), '../../MoveInventoryLambda')
sys.path.insert(0, move_inventory_path)

# Dynamically import the correct lambda_function to avoid cached imports
import importlib.util
spec = importlib.util.spec_from_file_location("lambda_function", 
                                               os.path.join(move_inventory_path, "lambda_function.py"))
if spec is None or spec.loader is None:
    raise ImportError("Could not load lambda_function.py from MoveInventoryLambda")
lambda_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_module)
lambda_handler = lambda_module.lambda_handler

# Safety check: verify we imported the correct lambda handler
try:
    # Check for unique functions that only exist in MoveInventoryLambda
    from bars_common_utils.shopify_utils import get_inventory_item_and_quantity  # type: ignore
    print("✅ Correctly imported MoveInventoryLambda lambda_function")
except ImportError:
    raise ImportError("❌ Wrong lambda_function imported - should be MoveInventoryLambda")


class TestMoveInventoryLambda:
    """Test suite for MoveInventoryLambda"""

    def test_veteran_to_early_move(self, mock_shopify_utils,
                                   sample_move_inventory_event,
                                   sample_lambda_context):
        """Test moving inventory from veteran to early variant"""
        # Patch the functions at the lambda_module level using the imported module
        with patch.object(lambda_module, 'get_inventory_item_and_quantity') as mock_get_inv, \
             patch.object(lambda_module, 'adjust_inventory') as mock_adjust, \
             patch.object(lambda_module, 'wait_until_next_minute') as mock_wait:
            
            # Setup mock responses
            mock_get_inv.side_effect = [
                {'inventoryItemId': 'item_11111', 'inventoryQuantity': 5},
                {'inventoryItemId': 'item_22222', 'inventoryQuantity': 0}
            ]

            result = lambda_handler(sample_move_inventory_event,
                                    sample_lambda_context)

            # Assertions
            assert result['statusCode'] == 200
            response_body = result['body']
            assert response_body['success'] is True
            assert 'Moved all 5 units' in response_body['message']

            # Verify inventory adjustments were called
            assert mock_adjust.call_count == 2
            mock_adjust.assert_any_call('item_11111', -5)  # remove from source
            mock_adjust.assert_any_call('item_22222', 5)   # add to destination

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

        # Patch the functions at the lambda_module level
        with patch.object(lambda_module, 'get_product_variants') as mock_get_variants, \
             patch.object(lambda_module, 'get_inventory_item_and_quantity') as mock_get_inv, \
             patch.object(lambda_module, 'adjust_inventory') as mock_adjust, \
             patch.object(lambda_module, 'wait_until_next_minute') as mock_wait:
            
            # Setup mock responses for consolidation flow
            mock_get_variants.return_value = {
                'product': {
                    'variants': {
                        'nodes': [
                            {
                                'title': 'Early Bird',
                                'inventoryQuantity': 5,
                                'inventoryItem': {'id': 'item_early'}
                            },
                            {
                                'title': 'Veteran',
                                'inventoryQuantity': 3,
                                'inventoryItem': {'id': 'item_veteran'}
                            },
                            {
                                'title': 'Open',
                                'inventoryQuantity': 0,
                                'inventoryItem': {'id': 'item_open'}
                            }
                        ]
                    }
                }
            }
            
            mock_get_inv.return_value = {
                'inventoryItemId': 'item_33333',
                'inventoryQuantity': 0
            }

            result = lambda_handler(event, sample_lambda_context)

        # Should consolidate early (5) + veteran (3) = 8 units to open
        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Moved 8 units into Open' in response_body['message']

        # Verify consolidation calls
        assert mock_get_variants.called
        # 2 removals + 1 addition
        assert mock_adjust.call_count == 3

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

        # Patch the functions at the lambda_module level
        with patch.object(lambda_module, 'get_inventory_item_and_quantity') as mock_get_inv, \
             patch.object(lambda_module, 'adjust_inventory') as mock_adjust, \
             patch.object(lambda_module, 'wait_until_next_minute') as mock_wait:
            
            # Setup mocks for custom move
            mock_get_inv.side_effect = [
                {'inventoryItemId': 'item_44444', 'inventoryQuantity': 12},
                {'inventoryItemId': 'item_55555', 'inventoryQuantity': 0}
            ]

            result = lambda_handler(event, sample_lambda_context)

        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Moved all 12 units' in response_body['message']

    def test_no_inventory_to_move_error(self, mock_shopify_utils,
                                        sample_move_inventory_event,
                                        sample_lambda_context):
        """Test error when source variant has no inventory"""
        # Patch the functions at the lambda_module level
        with patch.object(lambda_module, 'get_inventory_item_and_quantity') as mock_get_inv:
            # Mock source with 0 inventory
            mock_get_inv.side_effect = [
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

        # Patch all functions using the lambda_module object
        with patch.object(lambda_module, 'get_inventory_item_and_quantity') as mock_get_inv, \
             patch.object(lambda_module, 'adjust_inventory') as mock_adjust, \
             patch.object(lambda_module, 'get_product_variants') as mock_get_variants, \
             patch.object(lambda_module, 'wait_until_next_minute') as mock_wait:
            
            # Setup mocks based on source_type
            if source_type == 'veteran':
                mock_get_inv.side_effect = [
                    {'inventoryItemId': 'item_11111', 'inventoryQuantity': 5},
                    {'inventoryItemId': 'item_22222', 'inventoryQuantity': 0}
                ]
            elif source_type == 'consolidation':
                # Setup for consolidation flow
                mock_get_variants.return_value = {
                    'product': {
                        'variants': {
                            'nodes': [
                                {
                                    'title': 'Early Bird',
                                    'inventoryQuantity': 5,
                                    'inventoryItem': {'id': 'item_early'}
                                },
                                {
                                    'title': 'Veteran',
                                    'inventoryQuantity': 3,
                                    'inventoryItem': {'id': 'item_veteran'}
                                }
                            ]
                        }
                    }
                }
                mock_get_inv.return_value = {
                    'inventoryItemId': 'item_22222',
                    'inventoryQuantity': 0
                }
            elif source_type == 'custom':
                mock_get_inv.side_effect = [
                    {'inventoryItemId': 'item_11111', 'inventoryQuantity': 10},
                    {'inventoryItemId': 'item_22222', 'inventoryQuantity': 0}
                ]

            result = lambda_handler(event, sample_lambda_context)

        if expected_success:
            assert result['statusCode'] == 200
        else:
            assert result['statusCode'] == 500 