"""
Unit tests for shopifyProductUpdateHandler function.

Tests sport detection, image updates, and the main lambda handler.
"""

import sys
import os
from unittest.mock import patch, MagicMock

# Add the specific lambda function to path
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__),
                    '../../shopifyProductUpdateHandler')
)

from lambda_function import lambda_handler  # type: ignore
from sport_detection import (detect_sport, get_sold_out_image_url,  # type: ignore
                             is_all_closed, get_supported_sports)
from shopify_image_updater import ShopifyImageUpdater  # type: ignore


class TestSportDetection:
    """Test sport detection functionality"""

    def test_detect_sport_from_title(self):
        """Test sport detection from product title"""
        test_cases = [
            ("Big Apple Kickball - Monday Open", "kickball"),
            ("Big Apple Bowling - Tuesday League", "bowling"),
            ("Big Apple Dodgeball - Wednesday Night", "dodgeball"),
            ("Big Apple Pickleball - Thursday Morning", "pickleball"),
            ("Some Other Product", None),
            ("", None)
        ]

        for title, expected_sport in test_cases:
            result = detect_sport(title, "")
            assert result == expected_sport, f"Failed for title: {title}"

    def test_detect_sport_from_tags(self):
        """Test sport detection from product tags"""
        test_cases = [
            ("", "kickball,monday,open", "kickball"),
            ("", "bowling,tuesday,league", "bowling"),
            ("", "dodgeball,wednesday", "dodgeball"),
            ("", "pickleball,thursday", "pickleball"),
            ("", "other,tags,here", None)
        ]

        for title, tags, expected_sport in test_cases:
            result = detect_sport(title, tags)
            assert result == expected_sport, f"Failed for tags: {tags}"

    def test_get_sold_out_image_url(self):
        """Test sold-out image URL retrieval"""
        test_cases = [
            ("kickball",
             "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/"
             "Kickball_WaitlistOnly.png?v=1751381022"),
            ("bowling",
             "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/"
             "Bowling_ClosedWaitList.png?v=1750988743"),
            ("dodgeball",
             "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/"
             "Dodgeball_Closed.png?v=1750214647"),
            ("pickleball",
             "https://cdn.shopify.com/s/files/1/0554/7553/5966/files/"
             "Pickleball_WaitList.png?v=1750287195"),
            ("unknown", None)
        ]

        for sport, expected_url in test_cases:
            result = get_sold_out_image_url(sport)
            assert result == expected_url, f"Failed for sport: {sport}"

    def test_is_all_closed(self):
        """Test variant closure detection"""
        # All variants closed
        all_closed_variants = [
            {'title': 'Open', 'inventory_quantity': 0,
             'inventory_policy': 'deny'},
            {'title': 'Waitlist', 'inventory_quantity': 0,
             'inventory_policy': 'deny'}
        ]
        assert is_all_closed(all_closed_variants) is True

        # Some variants open
        some_open_variants = [
            {'title': 'Open', 'inventory_quantity': 5,
             'inventory_policy': 'deny'},
            {'title': 'Waitlist', 'inventory_quantity': 0,
             'inventory_policy': 'deny'}
        ]
        assert is_all_closed(some_open_variants) is False

        # Continue policy allows purchases regardless of inventory
        continue_policy_variants = [
            {'title': 'Open', 'inventory_quantity': 0,
             'inventory_policy': 'continue'}
        ]
        assert is_all_closed(continue_policy_variants) is False

    def test_get_supported_sports(self):
        """Test supported sports list"""
        sports = get_supported_sports()
        expected_sports = ["bowling", "dodgeball", "kickball", "pickleball"]
        assert sports == expected_sports


class TestShopifyImageUpdater:
    """Test Shopify image updater functionality"""

    def test_initialization(self, mock_shopify_env):
        """Test ShopifyImageUpdater initialization"""
        updater = ShopifyImageUpdater()
        assert updater.access_token == "test_token"
        assert updater.shop_domain == "09fe59-3.myshopify.com"

    def test_update_product_image_success(self, mock_shopify_env,
                                          mock_urllib_request):
        """Test successful product image update"""
        updater = ShopifyImageUpdater()

        # Mock successful REST API response
        mock_urllib_request.return_value.__enter__.return_value.read.\
            return_value = b'{"success": true}'

        result = updater.update_product_image(
            product_id="12345",
            product_gid="gid://shopify/Product/12345",
            image_url="https://example.com/sold-out-image.png",
            sport="kickball"
        )

        assert result is True
        assert mock_urllib_request.called

    def test_update_product_image_with_fallback(self, mock_shopify_env,
                                                mock_urllib_request):
        """Test image update with GraphQL fallback when REST fails"""
        updater = ShopifyImageUpdater()

        # Mock REST failure, then GraphQL success
        mock_urllib_request.side_effect = [
            Exception("REST API failed"),  # First call fails
            # Second succeeds
            MagicMock(read=lambda: b'{"data": {"productUpdate": '
                                    b'{"product": {"id": "123"}}}}')
        ]

        with patch.object(updater, '_try_rest_image_update',
                          return_value=False), \
             patch.object(updater, '_replace_media_graphql',
                          return_value=True):

            result = updater.update_product_image(
                product_id="12345",
                product_gid="gid://shopify/Product/12345",
                image_url="https://example.com/sold-out-image.png",
                sport="kickball",
                original_image="https://example.com/original.png"
            )

            assert result is True


class TestShopifyProductUpdateHandler:
    """Test main lambda handler functionality"""

    def test_successful_image_update(self, mock_shopify_env,
                                     sample_shopify_product_event,
                                     sample_lambda_context,
                                     mock_urllib_request):
        """Test successful product image update flow"""
        # All variants are closed
        sample_shopify_product_event['body']['variants'] = [
            {'id': 11111, 'title': 'Open', 'inventory_quantity': 0,
             'inventory_policy': 'deny'},
            {'id': 22222, 'title': 'Waitlist', 'inventory_quantity': 0,
             'inventory_policy': 'deny'}
        ]

        result = lambda_handler(sample_shopify_product_event,
                                sample_lambda_context)

        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Image updated successfully' in response_body['message']
        assert response_body['sport'] == 'kickball'

    def test_variants_not_all_closed(self, mock_shopify_env,
                                     sample_shopify_product_event,
                                     sample_lambda_context):
        """Test when not all variants are closed - should not update image"""
        # Some variants still have inventory
        sample_shopify_product_event['body']['variants'] = [
            {'id': 11111, 'title': 'Open', 'inventory_quantity': 5,
             'inventory_policy': 'deny'},
            {'id': 22222, 'title': 'Waitlist', 'inventory_quantity': 0,
             'inventory_policy': 'deny'}
        ]

        result = lambda_handler(sample_shopify_product_event,
                                sample_lambda_context)

        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Not all variants are closed' in response_body['message']

    def test_unsupported_sport(self, mock_shopify_env, sample_lambda_context):
        """Test with unsupported sport - should not update image"""
        event = {
            'body': {
                'id': 12345,
                'admin_graphql_api_id': 'gid://shopify/Product/12345',
                'title': 'Big Apple Tennis - Monday Open',  # Unsupported
                'tags': 'tennis,monday,open',
                'image': {'src': 'https://cdn.shopify.com/original_image.png'},
                'variants': [
                    {'id': 11111, 'title': 'Open', 'inventory_quantity': 0,
                     'inventory_policy': 'deny'}
                ]
            }
        }

        result = lambda_handler(event, sample_lambda_context)

        assert result['statusCode'] == 200
        response_body = result['body']
        assert response_body['success'] is True
        assert 'Unsupported sport' in response_body['message']

    def test_missing_required_data(self, mock_shopify_env,
                                   sample_lambda_context):
        """Test with missing required data"""
        incomplete_event = {
            'body': {
                'id': 12345,
                # Missing admin_graphql_api_id and variants
            }
        }

        result = lambda_handler(incomplete_event, sample_lambda_context)

        assert result['statusCode'] == 400
        response_body = result['body']
        assert 'Missing required product data' in response_body['error']

    def test_image_update_failure(self, mock_shopify_env,
                                  sample_shopify_product_event,
                                  sample_lambda_context):
        """Test when image update fails"""
        # Mock image updater to fail
        with patch('shopify_image_updater.ShopifyImageUpdater.'
                   'update_product_image', return_value=False):
            result = lambda_handler(sample_shopify_product_event,
                                    sample_lambda_context)

        assert result['statusCode'] == 500
        response_body = result['body']
        assert 'Failed to update product image' in response_body['error']

    def test_event_parsing(self, mock_shopify_env, sample_lambda_context):
        """Test different event body formats"""
        # String body
        string_event = {
            'body': '{"id": 12345, "admin_graphql_api_id": '
                    '"gid://shopify/Product/12345", "title": "Test Product", '
                    '"variants": []}'
        }

        with patch('bars_common_utils.event_utils.parse_event_body') as \
                mock_parse:
            mock_parse.return_value = {
                'id': 12345,
                'admin_graphql_api_id': 'gid://shopify/Product/12345',
                'title': 'Test Product',
                'variants': []
            }

            result = lambda_handler(string_event, sample_lambda_context)

            assert mock_parse.called
            assert result['statusCode'] == 200  # Should parse successfully

    def test_version_info_retrieval(self):
        """Test version information retrieval"""
        from version import get_version_info  # type: ignore

        version_info = get_version_info()
        assert 'version' in version_info
        assert 'description' in version_info
        assert 'author' in version_info
        assert version_info['author'] == 'BARS' 