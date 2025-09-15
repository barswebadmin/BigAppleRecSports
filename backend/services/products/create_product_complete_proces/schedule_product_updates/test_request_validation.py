"""
Test request format validation for schedule_product_updates
Ensures all generated requests match the expected Lambda function formats exactly
"""

import pytest
import re
from unittest.mock import patch
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
)


class TestRequestValidation:
    """Test that schedule_product_updates generates correctly formatted requests for each action type"""

    @pytest.fixture
    def sample_product_request(self):
        """Sample product request for testing"""
        return ProductCreationRequest(
            sportName=SportName.KICKBALL,
            product_name="Test Kickball League",
            product_handle="test-kickball-league",
            product_description="Test description",
            importantDates=ImportantDates(
                vetRegistrationStartDateTime="2025-09-15T00:00:00Z",
                earlyRegistrationStartDateTime="2025-09-16T00:00:00Z",
                openRegistrationStartDateTime="2025-09-17T00:00:00Z",
                seasonStartDate="2025-09-20T00:00:00Z",
                seasonEndDate="2025-11-15T00:00:00Z",
                offDatesCommaSeparated="2025-10-14,2025-11-28",
            ),
            regularSeasonBasicDetails=RegularSeasonBasicDetails(
                year=2025,
                season=Season.FALL,
                dayOfPlay=DayOfPlay.MONDAY,
                division=Division.OPEN,
                location="Central Park (Heckscher Ballfields)",
                leagueStartTime="6:30 PM",
                leagueEndTime="9:30 PM",
            ),
            optionalLeagueInfo=OptionalLeagueInfo(socialOrAdvanced="Social"),
            inventoryInfo=InventoryInfo(
                price=115.0,
                totalInventory=64,
                numberVetSpotsToReleaseAtGoLive=40,
            ),
        )

    @pytest.fixture
    def mock_product_data(self):
        """Mock product creation data"""
        return {
            "productUrl": "https://09fe59-3.myshopify.com/admin/products/7456789123456",
            "product_gid": "gid://shopify/Product/7456789123456",
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

    def validate_datetime_format(self, datetime_str: str) -> bool:
        """Validate datetime format matches Lambda expectations: YYYY-MM-DDTHH:MM:SS"""
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"
        return bool(re.match(pattern, datetime_str))

    def validate_gid_format(self, gid: str, entity_type: str) -> bool:
        """Validate Shopify GID format"""
        expected_pattern = f"gid://shopify/{entity_type}/\\d+"
        return bool(re.match(expected_pattern, gid))

    def validate_url_format(self, url: str) -> bool:
        """Validate Shopify admin URL format"""
        pattern = r"https://[^/]+\.myshopify\.com/admin/products/\d+"
        return bool(re.match(pattern, url))

    def test_create_scheduled_inventory_movements_request_format(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test create-scheduled-inventory-movements request format"""

        # Mock successful AWS response
        def mock_aws_request(request, url):
            # Validate the inventory movements request format
            if request.get("actionType") == "create-scheduled-inventory-movements":
                # REQUIRED FIELDS per Lambda documentation
                required_fields = [
                    "actionType",
                    "scheduleName",
                    "groupName",
                    "productUrl",
                    "sourceVariant",
                    "destinationVariant",
                    "newDatetime",
                    "note",
                    "totalInventory",
                    "numberVetSpotsToReleaseAtGoLive",
                ]

                for field in required_fields:
                    assert field in request, f"Missing required field: {field}"

                # Validate field formats
                assert request["actionType"] == "create-scheduled-inventory-movements"
                assert isinstance(request["scheduleName"], str)
                assert isinstance(request["groupName"], str)
                assert self.validate_url_format(request["productUrl"])
                assert self.validate_datetime_format(request["newDatetime"])
                assert isinstance(request["note"], str)
                assert isinstance(request["totalInventory"], int)
                assert isinstance(request["numberVetSpotsToReleaseAtGoLive"], int)

                # Validate sourceVariant structure
                source_variant = request["sourceVariant"]
                assert isinstance(source_variant, dict)
                assert "type" in source_variant
                assert "name" in source_variant
                assert "gid" in source_variant
                assert isinstance(source_variant["type"], str)
                assert isinstance(source_variant["name"], str)
                assert self.validate_gid_format(source_variant["gid"], "ProductVariant")

                # Validate destinationVariant structure
                dest_variant = request["destinationVariant"]
                assert isinstance(dest_variant, dict)
                assert "type" in dest_variant
                assert "name" in dest_variant
                assert "gid" in dest_variant
                assert isinstance(dest_variant["type"], str)
                assert isinstance(dest_variant["name"], str)
                assert self.validate_gid_format(dest_variant["gid"], "ProductVariant")

            return {
                "success": True,
                "status_code": 200,
                "response": {"message": "success"},
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_request

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                assert result["success"] is True

    def test_create_scheduled_price_changes_request_format(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test create-scheduled-price-changes request format"""

        def mock_aws_request(request, url):
            if request.get("actionType") == "create-scheduled-price-changes":
                # REQUIRED FIELDS per Lambda documentation
                required_fields = [
                    "actionType",
                    "sport",
                    "day",
                    "division",
                    "price",
                    "seasonStartDate",
                    "sportStartTime",
                    "productGid",
                    "openVariantGid",
                    "waitlistVariantGid",
                    "productUrl",
                ]

                for field in required_fields:
                    assert field in request, f"Missing required field: {field}"

                # Validate field formats
                assert request["actionType"] == "create-scheduled-price-changes"
                assert isinstance(request["sport"], str)
                assert isinstance(request["day"], str)
                assert isinstance(request["division"], str)
                assert isinstance(request["price"], (int, float))
                assert request["price"] > 0
                assert self.validate_gid_format(request["productGid"], "Product")
                assert self.validate_gid_format(
                    request["openVariantGid"], "ProductVariant"
                )
                assert self.validate_gid_format(
                    request["waitlistVariantGid"], "ProductVariant"
                )
                assert self.validate_url_format(request["productUrl"])

                # Validate date format (should be YYYY-MM-DD, not datetime)
                season_start = request["seasonStartDate"]
                date_pattern = r"^\d{4}-\d{2}-\d{2}$"
                assert re.match(
                    date_pattern, season_start
                ), f"Invalid date format: {season_start}"

                # Validate time format (should be HH:MM or HH:MM:SS)
                sport_time = request["sportStartTime"]
                time_pattern = r"^\d{1,2}:\d{2}(:\d{2})?$"
                assert re.match(
                    time_pattern, sport_time
                ), f"Invalid time format: {sport_time}"

                # Optional fields validation
                if "offDatesCommaSeparated" in request:
                    off_dates = request["offDatesCommaSeparated"]
                    if off_dates:  # Can be empty string
                        # Should be comma-separated dates: YYYY-MM-DD,YYYY-MM-DD
                        dates = off_dates.split(",")
                        for date in dates:
                            assert re.match(
                                date_pattern, date.strip()
                            ), f"Invalid off date: {date}"

            return {
                "success": True,
                "status_code": 201,
                "response": {"message": "success"},
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_request

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                assert result["success"] is True

    def test_create_initial_inventory_addition_request_format(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test create-initial-inventory-addition-and-title-change request format"""

        def mock_aws_request(request, url):
            if (
                request.get("actionType")
                == "create-initial-inventory-addition-and-title-change"
            ):
                # REQUIRED FIELDS per Lambda documentation
                required_fields = [
                    "actionType",
                    "scheduleName",
                    "groupName",
                    "productUrl",
                    "productTitle",
                    "variantGid",
                    "newDatetime",
                    "numberVetSpotsToReleaseAtGoLive",
                ]

                for field in required_fields:
                    assert field in request, f"Missing required field: {field}"

                # Validate field formats
                assert (
                    request["actionType"]
                    == "create-initial-inventory-addition-and-title-change"
                )
                assert isinstance(request["scheduleName"], str)
                assert isinstance(request["groupName"], str)
                assert self.validate_url_format(request["productUrl"])
                assert isinstance(request["productTitle"], str)
                assert self.validate_gid_format(request["variantGid"], "ProductVariant")
                assert self.validate_datetime_format(request["newDatetime"])
                assert isinstance(request["numberVetSpotsToReleaseAtGoLive"], int)
                assert request["numberVetSpotsToReleaseAtGoLive"] >= 0

                # Optional fields validation
                if "note" in request:
                    assert isinstance(request["note"], str)
                if "totalInventory" in request:
                    assert isinstance(request["totalInventory"], int)
                    assert request["totalInventory"] > 0

            return {
                "success": True,
                "status_code": 202,
                "response": {"message": "success"},
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_request

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                assert result["success"] is True

    def test_add_inventory_to_live_product_request_format(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test add-inventory-to-live-product request format"""

        def mock_aws_request(request, url):
            if request.get("actionType") == "add-inventory-to-live-product":
                # REQUIRED FIELDS per Lambda documentation
                required_fields = [
                    "actionType",
                    "scheduleName",
                    "groupName",
                    "productUrl",
                    "productTitle",
                    "variantGid",
                    "newDatetime",
                    "inventoryToAdd",
                ]

                for field in required_fields:
                    assert field in request, f"Missing required field: {field}"

                # Validate field formats
                assert request["actionType"] == "add-inventory-to-live-product"
                assert isinstance(request["scheduleName"], str)
                assert request["groupName"] == "add-remaining-inventory-to-live-product"
                assert self.validate_url_format(request["productUrl"])
                assert isinstance(request["productTitle"], str)
                assert self.validate_gid_format(request["variantGid"], "ProductVariant")
                assert self.validate_datetime_format(request["newDatetime"])
                assert isinstance(request["inventoryToAdd"], int)
                assert request["inventoryToAdd"] > 0

                # Validate schedule name format for remaining inventory
                schedule_name = request["scheduleName"]
                assert "auto-add-remaining-inventory-" in schedule_name
                assert schedule_name.endswith("-kb-monday-open")  # Based on test data

                # Optional fields validation
                if "note" in request:
                    assert isinstance(request["note"], str)
                if "totalInventory" in request:
                    assert isinstance(request["totalInventory"], int)
                if "numberVetSpotsToReleaseAtGoLive" in request:
                    assert isinstance(request["numberVetSpotsToReleaseAtGoLive"], int)

            return {
                "success": True,
                "status_code": 203,
                "response": {"message": "success"},
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_request

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                assert result["success"] is True

    def test_all_action_types_generated_with_correct_formats(
        self, sample_product_request, mock_product_data, mock_variants_data
    ):
        """Test that all 4 action types are generated with correct formats in a single call"""

        action_types_seen = set()

        def mock_aws_request(request, url):
            action_type = request.get("actionType")
            action_types_seen.add(action_type)

            # Run validation based on action type
            if action_type == "create-scheduled-inventory-movements":
                self._validate_inventory_movements_request(request)
            elif action_type == "create-scheduled-price-changes":
                self._validate_price_changes_request(request)
            elif action_type == "create-initial-inventory-addition-and-title-change":
                self._validate_initial_inventory_request(request)
            elif action_type == "add-inventory-to-live-product":
                self._validate_add_inventory_request(request)

            return {
                "success": True,
                "status_code": 200,
                "response": {"message": "success"},
            }

        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"
            mock_settings.aws_schedule_product_changes_url = (
                "https://example.com/lambda"
            )

            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.side_effect = mock_aws_request

                result = schedule_product_updates(
                    sample_product_request, mock_product_data, mock_variants_data
                )

                assert result["success"] is True

                # Verify we generated requests for the expected action types
                expected_action_types = {
                    "create-scheduled-inventory-movements",
                    "create-scheduled-price-changes",
                    "create-initial-inventory-addition-and-title-change",
                    "add-inventory-to-live-product",  # Should be included since totalInventory (64) > vetSpots (40)
                }
                assert action_types_seen == expected_action_types

    def _validate_inventory_movements_request(self, request):
        """Helper to validate inventory movements request"""
        required_fields = ["sourceVariant", "destinationVariant", "newDatetime"]
        for field in required_fields:
            assert field in request
        assert self.validate_datetime_format(request["newDatetime"])
        assert "type" in request["sourceVariant"]
        assert "gid" in request["sourceVariant"]

    def _validate_price_changes_request(self, request):
        """Helper to validate price changes request"""
        required_fields = ["sport", "day", "division", "price", "seasonStartDate"]
        for field in required_fields:
            assert field in request
        assert isinstance(request["price"], (int, float))
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", request["seasonStartDate"])

    def _validate_initial_inventory_request(self, request):
        """Helper to validate initial inventory request"""
        required_fields = ["scheduleName", "productTitle", "variantGid", "newDatetime"]
        for field in required_fields:
            assert field in request
        assert self.validate_datetime_format(request["newDatetime"])
        assert self.validate_gid_format(request["variantGid"], "ProductVariant")

    def _validate_add_inventory_request(self, request):
        """Helper to validate add inventory request"""
        required_fields = [
            "scheduleName",
            "inventoryToAdd",
            "variantGid",
            "newDatetime",
        ]
        for field in required_fields:
            assert field in request
        assert isinstance(request["inventoryToAdd"], int)
        assert request["inventoryToAdd"] > 0
        assert self.validate_datetime_format(request["newDatetime"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
