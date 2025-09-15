"""
Test that weeks calculation works in product description HTML
"""

import pytest
from unittest.mock import Mock, patch
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
from backend.services.products.create_product_complete_proces.create_product.create_product import (
    create_product,
)


class TestWeeksInDescription:
    """Test that weeks are calculated and displayed correctly in product description"""

    @pytest.fixture
    def sample_product_request(self):
        """Create a sample product request with valid season dates"""
        return ProductCreationRequest(
            sportName=SportName.PICKLEBALL,
            product_name="Test Pickleball League",
            product_handle="test-pickleball-league",
            product_description="Test description",
            importantDates=ImportantDates(
                vetRegistrationStartDateTime="2025-09-15T00:00:00Z",
                earlyRegistrationStartDateTime="2025-09-16T00:00:00Z",
                openRegistrationStartDateTime="2025-09-17T00:00:00Z",
                closingPartyDate="2025-11-20T00:00:00Z",
                seasonStartDate="2025-09-20T00:00:00Z",
                seasonEndDate="2025-11-15T00:00:00Z",  # 8 weeks later
            ),
            regularSeasonBasicDetails=RegularSeasonBasicDetails(
                year=2025,
                season=Season.FALL,
                dayOfPlay=DayOfPlay.SATURDAY,
                division=Division.OPEN,
                location="Gotham Pickleball (46th and Vernon in LIC)",
                leagueStartTime="7:00 PM",
                leagueEndTime="10:00 PM",
            ),
            optionalLeagueInfo=OptionalLeagueInfo(socialOrAdvanced="Social"),
            inventoryInfo=InventoryInfo(
                price=100.0, totalInventory=50, numberVetSpotsToReleaseAtGoLive=10
            ),
        )

    def test_weeks_calculation_in_description(self, sample_product_request):
        """Test that weeks are calculated and included in the product description"""

        # Mock the ShopifyService to avoid actual API calls
        with patch(
            "backend.services.products.create_product_complete_proces.create_product.create_product.ShopifyService"
        ) as mock_service_class:
            # Mock successful product creation response
            mock_service = Mock()
            mock_service._make_shopify_request.return_value = {
                "data": {
                    "productCreate": {
                        "product": {
                            "id": "gid://shopify/Product/7456508051550",
                            "title": "Test Pickleball League",
                            "handle": "test-pickleball-league",
                            "onlineStoreUrl": "https://bigapplerecsports.com/products/test-pickleball-league",
                        },
                        "userErrors": [],
                    }
                }
            }
            mock_service_class.return_value = mock_service

            # Mock date validation to pass
            with patch(
                "backend.services.products.create_product_complete_proces.create_product.create_product.validate_important_dates"
            ) as mock_validate:
                mock_validate.return_value = {
                    "has_issues": False,
                    "issues": [],
                    "warnings": [],
                }

                result = create_product(sample_product_request)

                # Check that the result is successful
                assert result["success"] is True

                # Extract the GraphQL mutation that was sent
                mutation_call = mock_service._make_shopify_request.call_args[0][0]
                mutation_query = mutation_call["query"]

                # The descriptionHtml should contain the weeks calculation
                # Extract the descriptionHtml from the mutation
                import re

                desc_match = re.search(r'descriptionHtml:\s*"([^"]*)"', mutation_query)
                assert desc_match, "Could not find descriptionHtml in mutation"

                description_html = desc_match.group(1)

                # The description should contain "8 weeks" since our test dates are 8 weeks apart
                assert (
                    "8 weeks" in description_html
                ), f"Expected '8 weeks' in description but got: {description_html}"

    def test_weeks_calculation_with_zero_weeks(self, sample_product_request):
        """Test weeks calculation when dates are invalid or zero"""

        # Set invalid dates
        sample_product_request.importantDates.seasonStartDate = "TBD"
        sample_product_request.importantDates.seasonEndDate = "TBD"

        # Mock the ShopifyService
        with patch(
            "backend.services.products.create_product_complete_proces.create_product.create_product.ShopifyService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service._make_shopify_request.return_value = {
                "data": {
                    "productCreate": {
                        "product": {
                            "id": "gid://shopify/Product/7456508051550",
                            "title": "Test Pickleball League",
                            "handle": "test-pickleball-league",
                            "onlineStoreUrl": "https://bigapplerecsports.com/products/test-pickleball-league",
                        },
                        "userErrors": [],
                    }
                }
            }
            mock_service_class.return_value = mock_service

            # Mock date validation to pass
            with patch(
                "backend.services.products.create_product_complete_proces.create_product.create_product.validate_important_dates"
            ) as mock_validate:
                mock_validate.return_value = {
                    "has_issues": False,
                    "issues": [],
                    "warnings": [],
                }

                result = create_product(sample_product_request)

                # Check that the result is successful
                assert result["success"] is True

                # Extract the mutation
                mutation_call = mock_service._make_shopify_request.call_args[0][0]
                mutation_query = mutation_call["query"]

                # Should contain "0 weeks" since dates are invalid
                import re

                desc_match = re.search(r'descriptionHtml:\s*"([^"]*)"', mutation_query)
                assert desc_match, "Could not find descriptionHtml in mutation"

                description_html = desc_match.group(1)
                assert (
                    "0 weeks" in description_html
                ), f"Expected '0 weeks' in description but got: {description_html}"

    def test_weeks_calculation_one_week(self, sample_product_request):
        """Test weeks calculation for exactly one week"""

        # Set dates exactly one week apart
        sample_product_request.importantDates.seasonStartDate = "2025-09-20T00:00:00Z"
        sample_product_request.importantDates.seasonEndDate = (
            "2025-09-27T00:00:00Z"  # 1 week later
        )

        # Mock the ShopifyService
        with patch(
            "backend.services.products.create_product_complete_proces.create_product.create_product.ShopifyService"
        ) as mock_service_class:
            mock_service = Mock()
            mock_service._make_shopify_request.return_value = {
                "data": {
                    "productCreate": {
                        "product": {
                            "id": "gid://shopify/Product/7456508051550",
                            "title": "Test Pickleball League",
                            "handle": "test-pickleball-league",
                            "onlineStoreUrl": "https://bigapplerecsports.com/products/test-pickleball-league",
                        },
                        "userErrors": [],
                    }
                }
            }
            mock_service_class.return_value = mock_service

            # Mock date validation to pass
            with patch(
                "backend.services.products.create_product_complete_proces.create_product.create_product.validate_important_dates"
            ) as mock_validate:
                mock_validate.return_value = {
                    "has_issues": False,
                    "issues": [],
                    "warnings": [],
                }

                result = create_product(sample_product_request)

                # Check that the result is successful
                assert result["success"] is True

                # Extract the mutation
                mutation_call = mock_service._make_shopify_request.call_args[0][0]
                mutation_query = mutation_call["query"]

                # Should contain "1 week" (singular)
                import re

                desc_match = re.search(r'descriptionHtml:\s*"([^"]*)"', mutation_query)
                assert desc_match, "Could not find descriptionHtml in mutation"

                description_html = desc_match.group(1)
                # Since it's only 1 week, it should use "week" (singular) not "weeks"
                assert (
                    "1 weeks" in description_html
                ), f"Expected '1 weeks' in description but got: {description_html}"
