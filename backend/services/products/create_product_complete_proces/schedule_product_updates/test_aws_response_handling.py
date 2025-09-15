"""
Test AWS response handling in schedule_product_updates for different action types and response codes
"""

import pytest
from unittest.mock import patch, Mock
from models.products.product_creation_request import ProductCreationRequest, SportName
from models.products.important_dates import ImportantDates
from models.products.regular_season_basic_details import (
    RegularSeasonBasicDetails,
    Season,
    DayOfPlay,
    Division,
)
from models.products.inventory_info import InventoryInfo
from models.products.optional_league_info import OptionalLeagueInfo
from backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates import (
    schedule_product_updates,
    send_aws_lambda_request,
)


class TestAWSResponseHandling:
    """Test AWS response handling for different Lambda action types and response codes"""

    @pytest.fixture
    def sample_product_request(self):
        """Sample product request for testing"""
        return ProductCreationRequest(
            sportName=SportName.PICKLEBALL,
            product_name="Test Pickleball League",
            product_handle="test-pickleball-league",
            product_description="Test description",
            importantDates=ImportantDates(
                vetRegistrationStartDateTime="2025-09-15T00:00:00Z",
                earlyRegistrationStartDateTime="2025-09-16T00:00:00Z",
                openRegistrationStartDateTime="2025-09-17T00:00:00Z",
                seasonStartDate="2025-09-20T00:00:00Z",
                seasonEndDate="2025-11-15T00:00:00Z",
            ),
            regularSeasonBasicDetails=RegularSeasonBasicDetails(
                year=2025,
                season=Season.FALL,
                dayOfPlay=DayOfPlay.TUESDAY,
                division=Division.OPEN,
                location="Gotham Pickleball (46th and Vernon in LIC)",
                leagueStartTime="7:00 PM",
                leagueEndTime="10:00 PM",
            ),
            optionalLeagueInfo=OptionalLeagueInfo(socialOrAdvanced="Social"),
            inventoryInfo=InventoryInfo(
                price=100.0,
                totalInventory=64,
                numberVetSpotsToReleaseAtGoLive=40,
            ),
        )

    @pytest.fixture
    def mock_product_data(self):
        """Mock product creation data"""
        return {
            "productUrl": "https://admin.shopify.com/store/09fe59-3/products/7456508051550",
            "product_gid": "gid://shopify/Product/7456508051550",
        }

    @pytest.fixture
    def mock_variants_data(self):
        """Mock variants creation data"""
        return {
            "data": {
                "variant_mapping": {
                    "vet": "gid://shopify/ProductVariant/42032228073566",
                    "early": "gid://shopify/ProductVariant/42032228106334",
                    "open": "gid://shopify/ProductVariant/42032228139102",
                    "waitlist": "gid://shopify/ProductVariant/42032228171870",
                }
            }
        }

    def test_send_aws_lambda_request_success_200(self):
        """Test send_aws_lambda_request with 200 success response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "success",
            "message": "Inventory movements scheduled successfully",
            "scheduleId": "inv-move-123",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "create-scheduled-inventory-movements"},
                "https://example.com/lambda",
            )

            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["response"]["status"] == "success"
            assert (
                "Inventory movements scheduled successfully"
                in result["response"]["message"]
            )

    def test_send_aws_lambda_request_success_201(self):
        """Test send_aws_lambda_request with 201 created response"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "created",
            "message": "Price changes scheduled successfully",
            "scheduleId": "price-change-456",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "create-scheduled-price-changes"},
                "https://example.com/lambda",
            )

            assert result["success"] is True
            assert result["status_code"] == 201
            assert result["response"]["status"] == "created"

    def test_send_aws_lambda_request_success_202(self):
        """Test send_aws_lambda_request with 202 accepted response"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "accepted",
            "message": "Initial inventory addition scheduled successfully",
            "scheduleId": "init-inv-789",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "create-initial-inventory-addition-and-title-change"},
                "https://example.com/lambda",
            )

            assert result["success"] is True
            assert result["status_code"] == 202
            assert result["response"]["status"] == "accepted"

    def test_send_aws_lambda_request_success_203(self):
        """Test send_aws_lambda_request with 203 response for remaining inventory"""
        mock_response = Mock()
        mock_response.status_code = 203
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "status": "scheduled",
            "message": "Remaining inventory addition scheduled successfully",
            "scheduleId": "remaining-inv-101",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "add-inventory-to-live-product"},
                "https://example.com/lambda",
            )

            assert result["success"] is True
            assert result["status_code"] == 203
            assert result["response"]["status"] == "scheduled"

    def test_send_aws_lambda_request_failure_400(self):
        """Test send_aws_lambda_request with 400 bad request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = "Bad Request: Missing required field: productUrl"

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "create-scheduled-inventory-movements"},
                "https://example.com/lambda",
            )

            assert result["success"] is False
            assert result["status_code"] == 400
            assert result["error"] == "aws_request_failed"
            assert "Bad Request" in result["message"]

    def test_send_aws_lambda_request_failure_422(self):
        """Test send_aws_lambda_request with 422 unprocessable entity"""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = "Unsupported actionType: invalid-action"

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "invalid-action"},
                "https://example.com/lambda",
            )

            assert result["success"] is False
            assert result["status_code"] == 422
            assert result["error"] == "aws_request_failed"
            assert "Unsupported actionType" in result["message"]

    def test_send_aws_lambda_request_failure_500(self):
        """Test send_aws_lambda_request with 500 internal server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = "Internal Server Error: Lambda function crashed"

        with patch("requests.post") as mock_post:
            mock_post.return_value = mock_response

            result = send_aws_lambda_request(
                {"actionType": "create-scheduled-inventory-movements"},
                "https://example.com/lambda",
            )

            assert result["success"] is False
            assert result["status_code"] == 500
            assert result["error"] == "aws_request_failed"
            assert "Internal Server Error" in result["message"]

    def test_schedule_product_updates_all_successful_responses(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test schedule_product_updates with all AWS requests succeeding"""

        def mock_aws_success(*args, **kwargs):
            """Mock successful AWS responses with different status codes"""
            request = args[0]
            action_type = request.get("actionType")

            # Return different status codes based on action type
            if action_type == "create-scheduled-inventory-movements":
                status_code = 200
                message = "Inventory movements scheduled"
            elif action_type == "create-scheduled-price-changes":
                status_code = 201
                message = "Price changes scheduled"
            elif action_type == "create-initial-inventory-addition-and-title-change":
                status_code = 202
                message = "Initial inventory addition scheduled"
            elif action_type == "add-inventory-to-live-product":
                status_code = 203
                message = "Remaining inventory addition scheduled"
            else:
                status_code = 200
                message = "Generic success"

            return {
                "success": True,
                "status_code": status_code,
                "response": {
                    "status": "success",
                    "message": message,
                    "scheduleId": f"schedule-{action_type}-123",
                },
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_success

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                # Should be successful overall
                assert result["success"] is True
                assert "scheduling_summary" in result

                # Check that AWS was called multiple times
                assert (
                    mock_aws.call_count >= 3
                )  # At least inventory moves, price changes, initial inventory

                # Verify different action types were called
                aws_call_args = mock_aws.call_args_list
                action_types_called = [
                    call[0][0]["actionType"] for call in aws_call_args
                ]

                assert "create-scheduled-inventory-movements" in action_types_called
                assert "create-scheduled-price-changes" in action_types_called
                assert (
                    "create-initial-inventory-addition-and-title-change"
                    in action_types_called
                )
                # May or may not have remaining inventory depending on values

    def test_schedule_product_updates_mixed_responses(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test schedule_product_updates with mixed success/failure responses"""

        call_count = 0

        def mock_aws_mixed(*args, **kwargs):
            """Mock mixed AWS responses - some succeed, some fail"""
            nonlocal call_count
            call_count += 1

            # First call succeeds, second fails
            if call_count == 1:
                return {
                    "success": True,
                    "status_code": 200,
                    "response": {
                        "status": "success",
                        "message": "First request succeeded",
                    },
                }
            else:
                return {
                    "success": False,
                    "status_code": 400,
                    "error": "aws_request_failed",
                    "message": "AWS request failed: 400 - Bad Request",
                }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_mixed

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                # Overall result should still be successful (no early exit)
                assert result["success"] is True
                assert "scheduling_summary" in result

                # Should have both successful and failed requests
                summary = result["scheduling_summary"]
                assert summary["successful_requests"] >= 1
                assert summary["failed_requests"] >= 1

    def test_schedule_product_updates_no_aws_url_configured(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test schedule_product_updates when no AWS URL is configured"""

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = None
            mock_settings.aws_create_product_endpoint = None

            result = schedule_product_updates(
                sample_product_request, mock_product_data, mock_variants_data
            )

            # Should still be successful but with warnings
            assert result["success"] is True
            assert "scheduling_summary" in result

            # All requests should have failed due to no URL
            summary = result["scheduling_summary"]
            assert summary["successful_requests"] == 0
            assert summary["failed_requests"] > 0

    def test_schedule_product_updates_return_to_frontend_structure(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test that schedule_product_updates returns the correct structure for frontend"""

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.return_value = {
                    "success": True,
                    "status_code": 200,
                    "response": {
                        "status": "success",
                        "message": "Scheduled successfully",
                    },
                }

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                # Verify the structure that should be returned to frontend
                assert "success" in result
                assert "scheduling_summary" in result
                assert "aws_responses" in result

                # Check scheduling summary structure
                summary = result["scheduling_summary"]
                assert "total_requests" in summary
                assert "successful_requests" in summary
                assert "failed_requests" in summary
                assert "requests_attempted" in summary

                # Check AWS responses structure
                aws_responses = result["aws_responses"]
                assert isinstance(aws_responses, list)

                if aws_responses:
                    first_response = aws_responses[0]
                    assert "request_index" in first_response
                    assert "action_type" in first_response
                    assert "schedule_name" in first_response
                    assert "aws_response" in first_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
