"""
Test suite for ProductCreationRequest model validation
Tests the Pydantic model validation logic directly
"""

import pytest
from models.products.product_creation_request import ProductCreationRequest
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)


class TestProductCreationRequestModel:
    """Test class for ProductCreationRequest model validation"""

    def test_valid_model_instantiation(self):
        """Test successful model instantiation with valid data"""
        valid_data = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": 2025,
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
                "leagueAssignmentTypes": ["Buddy Sign-up"],
                "sportSubCategory": "Foam",
                "socialOrAdvanced": "Social",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "11:00 PM",
            },
            "optionalLeagueInfo": {
                "socialOrAdvanced": "Social",
                "sportSubCategory": "Foam",
            },
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {
                "price": 150,
                "totalInventory": 64,
            },
        }

        result = ProductCreationRequest(**valid_data)
        assert result.sportName == "Dodgeball"
        assert result.regularSeasonBasicDetails.year == 2025
        assert result.inventoryInfo.price == 150

    def test_validate_request_data_success(self):
        """Test successful validation using the class method"""
        valid_data = {
            "sportName": "Pickleball",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "Spring",
                "dayOfPlay": "Saturday",
                "division": "Open",
                "location": "Gotham Pickleball (46th and Vernon in LIC)",
                "leagueStartTime": "10:00 AM",
                "leagueEndTime": "12:00 PM",
                "socialOrAdvanced": "Social",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-04-01T04:00:00.000Z",
                "seasonEndDate": "2025-06-15T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 85, "totalInventory": 32},
        }

        result = ProductCreationRequest.validate_request_data(valid_data)
        assert result.sportName == "Pickleball"
        assert result.regularSeasonBasicDetails.year == 2025

    def test_validate_request_data_failure(self):
        """Test validation failure with custom error"""
        invalid_data = {
            "sportName": "InvalidSport",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "InvalidSeason",
                "dayOfPlay": "Saturday",
                "division": "Open",
                "location": "Test Location",
                "leagueStartTime": "10:00 AM",
                "leagueEndTime": "12:00 PM",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-04-01T04:00:00.000Z",
                "seasonEndDate": "2025-06-15T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 85, "totalInventory": 32},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductCreationRequest.validate_request_data(invalid_data)

        errors = exc_info.value.get_errors()
        assert any("sportName" in error for error in errors)

    def test_sport_specific_validation_dodgeball(self):
        """Test sport-specific validation for Dodgeball"""
        # Test missing socialOrAdvanced
        data_missing_social = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "11:00 PM",
                "sportSubCategory": "Foam",
                # Missing socialOrAdvanced
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 150, "totalInventory": 64},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductCreationRequest.validate_request_data(data_missing_social)

        errors = exc_info.value.get_errors()
        assert any(
            "socialOrAdvanced is required for Dodgeball" in error for error in errors
        )

        # Test missing sportSubCategory
        data_missing_subcategory = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "11:00 PM",
                "socialOrAdvanced": "Social",
                # Missing sportSubCategory
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 150, "totalInventory": 64},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductCreationRequest.validate_request_data(data_missing_subcategory)

        errors = exc_info.value.get_errors()
        assert any(
            "sportSubCategory is required for Dodgeball" in error for error in errors
        )

    def test_sport_specific_validation_pickleball(self):
        """Test sport-specific validation for Pickleball"""
        # Test missing socialOrAdvanced
        data_missing_social = {
            "sportName": "Pickleball",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "Spring",
                "dayOfPlay": "Saturday",
                "division": "Open",
                "location": "Gotham Pickleball (46th and Vernon in LIC)",
                "leagueStartTime": "10:00 AM",
                "leagueEndTime": "12:00 PM",
                # Missing socialOrAdvanced
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-04-01T04:00:00.000Z",
                "seasonEndDate": "2025-06-15T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 85, "totalInventory": 32},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductCreationRequest.validate_request_data(data_missing_social)

        errors = exc_info.value.get_errors()
        assert any(
            "socialOrAdvanced is required for Pickleball" in error for error in errors
        )

    def test_model_config_enum_values(self):
        """Test that enum values are properly handled"""
        valid_data = {
            "sportName": "Kickball",
            "regularSeasonBasicDetails": {
                "year": 2025,
                "season": "Spring",  # String value for enum
                "dayOfPlay": "Saturday",
                "division": "WTNB+",
                "location": "Dewitt Clinton Park (52nd St & 11th Ave)",
                "leagueStartTime": "10:00 AM",
                "leagueEndTime": "12:00 PM",
            },
            "optionalLeagueInfo": {"socialOrAdvanced": "Social"},
            "importantDates": {
                "seasonStartDate": "2025-04-01T04:00:00.000Z",
                "seasonEndDate": "2025-06-15T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 85, "totalInventory": 32},
        }

        result = ProductCreationRequest(**valid_data)
        # Enum should be accessible as enum object
        assert result.regularSeasonBasicDetails.season.value == "Spring"
        assert result.regularSeasonBasicDetails.division.value == "WTNB+"
