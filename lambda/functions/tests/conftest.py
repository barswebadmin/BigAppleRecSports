"""
Pytest configuration and shared fixtures for lambda function tests.
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add lambda-functions to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for testing"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    yield
    # Cleanup
    for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 
                'AWS_SECURITY_TOKEN', 'AWS_SESSION_TOKEN']:
        os.environ.pop(key, None)

@pytest.fixture(autouse=True)
def mock_shopify_env_and_token():
    """Provide location ID and patch token resolver to avoid boto3/SSM in unit tests."""
    os.environ['SHOPIFY_LOCATION_ID'] = 'test_location_id'
    # Patch both shared layer and any local copy
    patches = [
        patch('bars_common_utils.shopify_utils._get_shopify_access_token', return_value='test_token'),
        patch('MoveInventoryLambda.bars_common_utils.shopify_utils._get_shopify_access_token', return_value='test_token'),
        patch('shopify_image_updater._get_ssm_param', return_value='test_token'),
    ]
    actives = []
    for p in patches:
        try:
            actives.append(p.start())
        except Exception:
            pass
    yield
    for p in patches:
        try:
            p.stop()
        except Exception:
            pass
    os.environ.pop('SHOPIFY_LOCATION_ID', None)

@pytest.fixture
def mock_shopify_env():
    """Backwards-compatible alias for tests expecting mock_shopify_env."""
    # No-op: token is patched by mock_shopify_env_and_token; just ensure fixture exists
    yield

@pytest.fixture
def mock_boto3_client(aws_credentials):
    """Mock boto3 clients for AWS services"""
    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 not installed - skipping AWS integration tests")
    
    with patch('boto3.client') as mock_client:
        # Create mock clients for different services
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.return_value = {
            'Name': 'test-schedule',
            'State': 'ENABLED'
        }
        mock_scheduler.update_schedule.return_value = {
            'ScheduleArn': 'arn:aws:scheduler:us-east-1:123456789012:schedule/test-group/test-schedule'
        }
        mock_scheduler.create_schedule.return_value = {
            'ScheduleArn': 'arn:aws:scheduler:us-east-1:123456789012:schedule/test-group/test-schedule'
        }
        
        # Return appropriate mock based on service name
        def get_mock_client(service_name, **kwargs):
            if service_name == 'scheduler':
                return mock_scheduler
            return MagicMock()
        
        mock_client.side_effect = get_mock_client
        yield {
            'scheduler': mock_scheduler,
            'client_factory': mock_client
        }

@pytest.fixture
def mock_shopify_utils():
    """Mock bars_common_utils.shopify_utils functions"""
    # Mock both the layer version and any local lambda function copies
    patches = [
        patch('bars_common_utils.shopify_utils.get_inventory_item_and_quantity'),
        patch('bars_common_utils.shopify_utils.adjust_inventory'),
        patch('bars_common_utils.shopify_utils.get_product_variants'),
        # Also patch the local lambda function imports
        patch('MoveInventoryLambda.bars_common_utils.shopify_utils.get_inventory_item_and_quantity'),
        patch('MoveInventoryLambda.bars_common_utils.shopify_utils.adjust_inventory'),
        patch('MoveInventoryLambda.bars_common_utils.shopify_utils.get_product_variants'),
    ]
    
    mocks = []
    for p in patches:
        try:
            mocks.append(p.start())
        except ImportError:
            # Some imports might not exist, that's ok
            pass
    
    # Set default return values on the first set of mocks
    if len(mocks) >= 3:
        mock_get_inv, mock_adjust, mock_get_variants = mocks[0], mocks[1], mocks[2]
        
        # Default return values
        mock_get_inv.return_value = {
            'inventoryItemId': 'gid://shopify/InventoryItem/12345',
            'inventoryQuantity': 10
        }
        
        mock_get_variants.return_value = {
            'product': {
                'variants': {
                    'nodes': [
                        {
                            'title': 'Early Bird Registration',
                            'inventoryQuantity': 5,
                            'inventoryItem': {'id': 'gid://shopify/InventoryItem/11111'}
                        },
                        {
                            'title': 'Veteran (Season Pass Holders)',
                            'inventoryQuantity': 3,
                            'inventoryItem': {'id': 'gid://shopify/InventoryItem/22222'}
                        }
                    ]
                }
            }
        }
        
        yield {
            'get_inventory_item_and_quantity': mock_get_inv,
            'adjust_inventory': mock_adjust,
            'get_product_variants': mock_get_variants
        }
    
    # Cleanup
    for mock in mocks:
        try:
            mock.stop()
        except:  # noqa: E722
            pass

@pytest.fixture
def sample_lambda_event():
    """Sample Lambda event for testing"""
    return {
        'httpMethod': 'POST',
        'body': '{"test": "data"}',
        'headers': {'Content-Type': 'application/json'},
        'requestContext': {
            'requestId': 'test-request-id',
            'stage': 'test'
        }
    }

@pytest.fixture
def sample_lambda_context():
    """Sample Lambda context for testing"""
    context = MagicMock()
    context.function_name = 'test-function'
    context.function_version = '1'
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
    context.memory_limit_in_mb = 128
    context.remaining_time_in_millis.return_value = 30000
    context.log_group_name = '/aws/lambda/test-function'
    context.log_stream_name = '2023/01/01/[$LATEST]abcd1234'
    context.aws_request_id = 'test-request-id'
    return context

@pytest.fixture
def sample_move_inventory_event():
    """Sample event for MoveInventoryLambda testing"""
    return {
        'scheduleName': 'test-schedule',
        'productUrl': 'https://admin.shopify.com/store/test/products/12345',
        'sourceVariant': {
            'name': 'Veteran',
            'gid': 'gid://shopify/ProductVariant/11111',
            'type': 'veteran'
        },
        'destinationVariant': {
            'name': 'Early Bird',
            'gid': 'gid://shopify/ProductVariant/22222',
            'type': 'early'
        }
    }

@pytest.fixture
def sample_scheduler_event():
    """Sample event for scheduler lambda functions"""
    return {
        'body': {
            'scheduleName': 'test-schedule',
            'groupName': 'test-group',
            'scheduleTime': '2025-01-01T12:00:00',
            'timezone': 'America/New_York',
            'productGid': 'gid://shopify/Product/12345',
            'openVariantGid': 'gid://shopify/ProductVariant/11111',
            'waitlistVariantGid': 'gid://shopify/ProductVariant/22222',
            'updatedPrice': 25.00,
            'seasonStartDate': '1/1/25',
            'sport': 'kickball',
            'day': 'Monday',
            'division': 'Open'
        }
    }

@pytest.fixture
def sample_shopify_product_event():
    """Sample Shopify product webhook event for image update testing"""
    return {
        'body': {
            'id': 12345,
            'admin_graphql_api_id': 'gid://shopify/Product/12345',
            'title': 'Big Apple Kickball - Monday Open',
            'tags': 'kickball,monday,open',
            'image': {
                'src': 'https://cdn.shopify.com/original_image.png'
            },
            'variants': [
                {
                    'id': 11111,
                    'title': 'Open',
                    'inventory_quantity': 0,
                    'inventory_policy': 'deny'
                },
                {
                    'id': 22222,
                    'title': 'Waitlist',
                    'inventory_quantity': 0,
                    'inventory_policy': 'deny'
                }
            ]
        }
    }

@pytest.fixture
def mock_urllib_request():
    """Mock urllib.request for HTTP operations"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"success": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        yield mock_urlopen 