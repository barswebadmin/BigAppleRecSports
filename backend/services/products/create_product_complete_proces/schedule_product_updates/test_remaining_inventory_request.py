"""
Test for remaining inventory request in schedule_product_updates
"""

import pytest
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


class TestRemainingInventoryRequest:
    """Test remaining inventory request logic"""

    @pytest.fixture
    def base_product_request(self):
        """Base product request for testing"""
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
                totalInventory=100,  # Will be modified in tests
                numberVetSpotsToReleaseAtGoLive=40,  # Will be modified in tests
            ),
        )

    @pytest.fixture
    def mock_product_data(self):
        """Mock product data"""
        return {
            "productUrl": "https://admin.shopify.com/store/09fe59-3/products/7456508051550",
            "product_gid": "gid://shopify/Product/7456508051550",
        }

    @pytest.fixture
    def mock_variants_data(self):
        """Mock variants data"""
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

    def test_remaining_inventory_request_added_when_total_greater_than_vet_spots(
        self, base_product_request, mock_product_data, mock_variants_data
    ):
        """Test that remaining inventory request is added when totalInventory > numberVetSpotsToReleaseAtGoLive"""

        # Set inventory values where total > vet spots
        base_product_request.inventoryInfo.totalInventory = 100
        base_product_request.inventoryInfo.numberVetSpotsToReleaseAtGoLive = 40

        # Mock AWS settings
        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"

            # Mock AWS lambda request
            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.return_value = {
                    "success": True,
                    "response": {"message": "success"},
                }

                result = schedule_product_updates(
                    base_product_request, mock_product_data, mock_variants_data
                )

                # Should be successful
                assert result["success"] is True

                # Check that AWS was called
                assert mock_aws.called

                # Get all the requests that were sent to AWS
                aws_call_args = mock_aws.call_args_list
                requests_sent = [
                    call[0][0] for call in aws_call_args
                ]  # First argument of each call

                # Find remaining inventory request
                remaining_inventory_requests = [
                    req
                    for req in requests_sent
                    if req.get("groupName") == "add-remaining-inventory-to-live-product"
                ]

                # Should have exactly one remaining inventory request
                assert len(remaining_inventory_requests) == 1

                remaining_req = remaining_inventory_requests[0]

                # Verify the request structure
                assert remaining_req["actionType"] == "add-inventory-to-live-product"
                assert (
                    "auto-add-remaining-inventory-7456508051550-pb-tuesday-openDiv"
                    in remaining_req["scheduleName"]
                )
                assert (
                    remaining_req["groupName"]
                    == "add-remaining-inventory-to-live-product"
                )
                assert (
                    remaining_req["variantGid"]
                    == "gid://shopify/ProductVariant/42032228106334"
                )  # early variant
                assert remaining_req["inventoryToAdd"] == 60  # 100 - 40 = 60

    def test_remaining_inventory_request_not_added_when_total_equals_vet_spots(
        self, base_product_request, mock_product_data, mock_variants_data
    ):
        """Test that remaining inventory request is NOT added when totalInventory == numberVetSpotsToReleaseAtGoLive"""

        # Set inventory values where total == vet spots
        base_product_request.inventoryInfo.totalInventory = 40
        base_product_request.inventoryInfo.numberVetSpotsToReleaseAtGoLive = 40

        # Mock AWS settings
        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"

            # Mock AWS lambda request
            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.return_value = {
                    "success": True,
                    "response": {"message": "success"},
                }

                result = schedule_product_updates(
                    base_product_request, mock_product_data, mock_variants_data
                )

                # Should be successful
                assert result["success"] is True

                # Get all the requests that were sent to AWS
                aws_call_args = mock_aws.call_args_list
                requests_sent = [call[0][0] for call in aws_call_args]

                # Find remaining inventory request
                remaining_inventory_requests = [
                    req
                    for req in requests_sent
                    if req.get("groupName") == "add-remaining-inventory-to-live-product"
                ]

                # Should have NO remaining inventory requests
                assert len(remaining_inventory_requests) == 0

    def test_remaining_inventory_request_not_added_when_total_less_than_vet_spots(
        self, base_product_request, mock_product_data, mock_variants_data
    ):
        """Test that remaining inventory request is NOT added when totalInventory < numberVetSpotsToReleaseAtGoLive"""

        # Set inventory values where total < vet spots
        base_product_request.inventoryInfo.totalInventory = 30
        base_product_request.inventoryInfo.numberVetSpotsToReleaseAtGoLive = 40

        # Mock AWS settings
        with patch("config.settings") as mock_settings:
            mock_settings.shopify_token = "test_token"

            # Mock AWS lambda request
            with patch(
                "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
            ) as mock_aws:
                mock_aws.return_value = {
                    "success": True,
                    "response": {"message": "success"},
                }

                result = schedule_product_updates(
                    base_product_request, mock_product_data, mock_variants_data
                )

                # Should be successful
                assert result["success"] is True

                # Get all the requests that were sent to AWS
                aws_call_args = mock_aws.call_args_list
                requests_sent = [call[0][0] for call in aws_call_args]

                # Find remaining inventory request
                remaining_inventory_requests = [
                    req
                    for req in requests_sent
                    if req.get("groupName") == "add-remaining-inventory-to-live-product"
                ]

                # Should have NO remaining inventory requests
                assert len(remaining_inventory_requests) == 0

    def test_remaining_inventory_calculation(
        self, base_product_request, mock_product_data, mock_variants_data
    ):
        """Test that remaining inventory is calculated correctly"""

        # Test various inventory scenarios
        test_cases = [
            (100, 25, 75),  # total=100, vet=25, remaining=75
            (80, 30, 50),  # total=80, vet=30, remaining=50
            (60, 10, 50),  # total=60, vet=10, remaining=50
        ]

        for total_inventory, vet_spots, expected_remaining in test_cases:
            base_product_request.inventoryInfo.totalInventory = total_inventory
            base_product_request.inventoryInfo.numberVetSpotsToReleaseAtGoLive = (
                vet_spots
            )

            # Mock AWS settings
            with patch("config.settings") as mock_settings:
                mock_settings.shopify_token = "test_token"

                # Mock AWS lambda request
                with patch(
                    "backend.services.products.create_product_complete_proces.schedule_product_updates.schedule_product_updates.send_aws_lambda_request"
                ) as mock_aws:
                    mock_aws.return_value = {
                        "success": True,
                        "response": {"message": "success"},
                    }

                    result = schedule_product_updates(
                        base_product_request, mock_product_data, mock_variants_data
                    )

                    # Should be successful
                    assert result["success"] is True

                    # Get remaining inventory request
                    aws_call_args = mock_aws.call_args_list
                    requests_sent = [call[0][0] for call in aws_call_args]

                    remaining_inventory_requests = [
                        req
                        for req in requests_sent
                        if req.get("groupName")
                        == "add-remaining-inventory-to-live-product"
                    ]

                    # Should have exactly one remaining inventory request
                    assert len(remaining_inventory_requests) == 1

                    remaining_req = remaining_inventory_requests[0]

                    # Check that the calculation is correct
                    assert remaining_req["inventoryToAdd"] == expected_remaining
