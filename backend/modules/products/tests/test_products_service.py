"""
Test suite for ProductsService.create_product_creation_request validation
Tests cover all validation rules including sport-specific requirements
"""

import pytest
from modules.products.services.products_service import ProductsService
from models.products.product_creation_request_validation_error import (
    ProductCreationRequestValidationError,
)


class TestIsValidProductCreationRequest:
    """Test class for product creation request validation"""

    def test_valid_complete_product_data(self):
        """Test validation with complete valid product data"""
        complete_data = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": "2025",
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
                "leagueAssignmentTypes": ["Buddy Sign-up"],
                "sportSubCategory": "Foam",
                "socialOrAdvanced": "Social",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "11:00 PM",
                "alternativeStartTime": "9:00 PM",
                "alternativeEndTime": "12:00 AM",
            },
            "optionalLeagueInfo": {
                "socialOrAdvanced": "Social",
                "sportSubCategory": "Foam",
                "types": ["Buddy Sign-up"],
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
                "numberVetSpotsToReleaseAtGoLive": 40,
            },
        }

        result = ProductsService.to_product_creation_request(complete_data)

        assert result.sportName == "Dodgeball"
        assert (
            result.regularSeasonBasicDetails.location
            == "Elliott Center (26th St & 9th Ave)"
        )

    def test_missing_required_fields_raises_validation_error(self):
        """Test that missing required fields raises ProductCreationRequestValidationError"""
        incomplete_data = {
            "sportName": "Pickleball",
            # Missing: regularSeasonBasicDetails entirely
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
            ProductsService.to_product_creation_request(incomplete_data)

        errors = exc_info.value.get_errors(formatted=True)
        error_text = " ".join(errors)  # type: ignore

        assert "regularSeasonBasicDetails: Field required" in error_text

    def test_invalid_enum_values_raises_validation_error(self):
        """Test that invalid enum values raise ProductCreationRequestValidationError"""
        data_invalid_enums = {
            "sportName": "Basketball",  # Invalid sport
            "regularSeasonBasicDetails": {
                "dayOfPlay": "Everyday",  # Invalid day
                "division": "Professional",  # Invalid division
                "season": "Monsoon",  # Invalid season
                "year": "2025",
                "location": "Elliott Center (26th St & 9th Ave)",  # Valid for Dodgeball
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "10:00 PM",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 100, "totalInventory": 50},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductsService.to_product_creation_request(data_invalid_enums)

        errors = exc_info.value.get_errors(formatted=True)
        error_text = " ".join(errors)  # type: ignore

        assert "sportName:" in error_text
        assert "regularSeasonBasicDetails.division:" in error_text

    def test_sport_specific_dodgeball_missing_required_fields(self):
        """Test that Dodgeball validation fails when missing socialOrAdvanced or sportSubCategory"""
        # Missing socialOrAdvanced for Dodgeball
        data_missing_social = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "division": "Open",
                "season": "Fall",
                "year": "2025",
                "dayOfPlay": "Tuesday",
                "location": "Elliott Center (26th St & 9th Ave)",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "11:00 PM",
            },
            "optionalLeagueInfo": {
                "sportSubCategory": "Foam"
                # Missing socialOrAdvanced
            },
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
            ProductsService.to_product_creation_request(data_missing_social)

        errors = exc_info.value.get_errors()
        assert any(
            "socialOrAdvanced is required for Dodgeball" in error for error in errors
        )

    def test_sport_specific_kickball_missing_social_or_advanced(self):
        """Test that Kickball validation fails when missing socialOrAdvanced"""
        data_missing_social = {
            "sportName": "Kickball",
            "regularSeasonBasicDetails": {
                "division": "Open",
                "season": "Spring",
                "year": "2025",
                "dayOfPlay": "Saturday",
                "location": "Dewitt Clinton Park (52nd St & 11th Ave)",
                "leagueStartTime": "10:00 AM",
                "leagueEndTime": "12:00 PM",
            },
            "optionalLeagueInfo": {
                # Missing socialOrAdvanced for Kickball
            },
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
            ProductsService.to_product_creation_request(data_missing_social)

        errors = exc_info.value.get_errors()
        assert any(
            "socialOrAdvanced is required for Kickball" in error for error in errors
        )

    def test_sport_specific_location_validation(self):
        """Test that location validation is sport-specific"""
        # Invalid location for Bowling
        data_invalid_bowling_location = {
            "sportName": "Bowling",
            "regularSeasonBasicDetails": {
                "division": "Open",
                "season": "Winter",
                "year": "2025",
                "dayOfPlay": "Friday",
                "location": "Elliott Center (26th St & 9th Ave)",  # Invalid for Bowling
                "leagueStartTime": "6:30 PM",
                "leagueEndTime": "9:30 PM",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-01-15T04:00:00.000Z",
                "seasonEndDate": "2025-03-15T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-01-01T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-01-02T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-01-03T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 120, "totalInventory": 48},
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductsService.to_product_creation_request(data_invalid_bowling_location)

        errors = exc_info.value.get_errors()
        assert any("not valid for Bowling" in error for error in errors)

    def test_multiple_validation_errors_returned_together(self):
        """Test that all validation errors are returned together, not just the first one"""
        data_multiple_errors = {
            "sportName": "InvalidSport",  # Invalid enum
            "regularSeasonBasicDetails": {
                "division": "InvalidDivision",  # Invalid enum
                "season": "InvalidSeason",  # Invalid enum
                "year": "invalid_year",  # Invalid year format
                "dayOfPlay": "InvalidDay",  # Invalid enum
                "location": "Invalid Location",  # Will be invalid for any sport
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "10:00 PM",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "invalid_date",  # Invalid date
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {
                "price": -50,  # Invalid negative price
                "totalInventory": "not_a_number",  # Invalid type
            },
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductsService.to_product_creation_request(data_multiple_errors)

        errors = exc_info.value.get_errors()

        # Should have multiple errors, not just one
        assert len(errors) >= 5

    def test_boundary_values_validation(self):
        """Test validation with boundary values"""
        # Test year boundaries
        data_year_too_low = {
            "sportName": "Pickleball",
            "regularSeasonBasicDetails": {
                "division": "Open",
                "season": "Fall",
                "year": "2023",  # Too low
                "dayOfPlay": "Monday",
                "location": "Gotham Pickleball (46th and Vernon in LIC)",
                "leagueStartTime": "8:00 PM",
                "leagueEndTime": "10:00 PM",
            },
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {
                "price": 0,  # Zero price (invalid)
                "totalInventory": 0,  # Zero inventory (invalid)
            },
        }

        with pytest.raises(ProductCreationRequestValidationError) as exc_info:
            ProductsService.to_product_creation_request(data_year_too_low)

        errors = exc_info.value.get_errors(formatted=True)
        error_text = " ".join(errors)  # type: ignore

        assert "Year must be between 2024 and 2030" in error_text

    def test_valid_minimal_data(self):
        """Test validation with minimal valid data (all optional fields None/missing)"""
        data_minimal_valid = {
            "sportName": "Pickleball",
            "regularSeasonBasicDetails": {
                "division": "Open",
                "season": "Spring",
                "year": "2025",
                "dayOfPlay": "Saturday",
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

        result = ProductsService.to_product_creation_request(data_minimal_valid)
        assert result is not None
        assert result.sportName == "Pickleball"
