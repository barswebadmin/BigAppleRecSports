"""
Tests for ProductsService validation
Mirrors the validation logic from the GAS project
"""

from services.products.products_service import ProductsService


class TestProductsServiceValidation:
    """Test ProductsService.is_valid_product_creation_request validation"""

    def test_valid_complete_product_data(self):
        """Test validation with complete valid product data"""
        valid_data = {
            "sportName": "Pickleball",
            "division": "Open",
            "season": "Fall",
            "year": "2025",
            "dayOfPlay": "Tuesday",
            "location": "Gotham Pickleball (46th and Vernon in LIC)",
            "leagueStartTime": "8:00 PM",
            "leagueEndTime": "11:00 PM",
            "alternativeStartTime": None,
            "alternativeEndTime": None,
            "optionalLeagueInfo": {
                "socialOrAdvanced": "Competitive/Advanced",
                "sportSubCategory": "",
                "types": ["Buddy Sign-up"],
            },
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "offDates": ["2025-11-26T04:00:00.000Z"],
                "newPlayerOrientationDateTime": None,
                "scoutNightDateTime": None,
                "openingPartyDate": None,
                "rainDate": None,
                "closingPartyDate": "TBD",
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

        result = ProductsService.is_valid_product_creation_request(valid_data)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_required_top_level_fields(self):
        """Test validation fails when required top-level fields are missing"""
        incomplete_data = {
            "sportName": "Pickleball",
            # Missing: dayOfPlay, division, season, year, location, leagueStartTime, leagueEndTime
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

        result = ProductsService.is_valid_product_creation_request(incomplete_data)

        assert result["valid"] is False
        assert any("Missing required fields:" in error for error in result["errors"])
        assert any("dayOfPlay" in error for error in result["errors"])
        assert any("division" in error for error in result["errors"])

    def test_missing_nested_objects(self):
        """Test validation fails when required nested objects are missing"""
        data_missing_nested = {
            "sportName": "Kickball",
            "dayOfPlay": "Wednesday",
            "division": "Open",
            "season": "Spring",
            "year": "2025",
            "location": "Central Park",
            "leagueStartTime": "7:00 PM",
            "leagueEndTime": "9:00 PM",
            # Missing: optionalLeagueInfo, importantDates, inventoryInfo
        }

        result = ProductsService.is_valid_product_creation_request(data_missing_nested)

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "importantDates" in error_text
        assert "inventoryInfo" in error_text
        assert "optionalLeagueInfo" in error_text

    def test_missing_required_nested_fields(self):
        """Test validation fails when required fields within nested objects are missing"""
        data_missing_nested_fields = {
            "sportName": "Bowling",
            "dayOfPlay": "Friday",
            "division": "Social",
            "season": "Winter",
            "year": "2025",
            "location": "Frames Bowling Lounge",
            "leagueStartTime": "6:30 PM",
            "leagueEndTime": "9:30 PM",
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-01-15T04:00:00.000Z",
                # Missing: seasonEndDate, vetRegistrationStartDateTime, earlyRegistrationStartDateTime, openRegistrationStartDateTime
            },
            "inventoryInfo": {
                "price": 120
                # Missing: totalInventory
            },
        }

        result = ProductsService.is_valid_product_creation_request(
            data_missing_nested_fields
        )

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "seasonEndDate" in error_text
        assert "totalInventory" in error_text
        assert "vetRegistrationStartDateTime" in error_text

    def test_invalid_enum_values(self):
        """Test validation fails for invalid enum values"""
        data_invalid_enums = {
            "sportName": "Basketball",  # Invalid sport
            "dayOfPlay": "Everyday",  # Invalid day
            "division": "Professional",  # Invalid division
            "season": "Monsoon",  # Invalid season
            "year": "2025",
            "location": "Somewhere",
            "leagueStartTime": "8:00 PM",
            "leagueEndTime": "10:00 PM",
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

        result = ProductsService.is_valid_product_creation_request(data_invalid_enums)

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "Invalid sportName" in error_text
        assert "Invalid dayOfPlay" in error_text
        assert "Invalid division" in error_text
        assert "Invalid season" in error_text

    def test_invalid_field_types(self):
        """Test validation fails for invalid field types"""
        data_invalid_types = {
            "sportName": 123,  # Should be string
            "dayOfPlay": "Monday",
            "division": "Open",
            "season": "Fall",
            "year": "not_a_year",  # Should be convertible to int
            "location": "Test Location",
            "leagueStartTime": "8:00 PM",
            "leagueEndTime": "10:00 PM",
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "2025-10-15T04:00:00.000Z",
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {
                "price": "not_a_number",  # Should be numeric
                "totalInventory": "also_not_a_number",  # Should be int
            },
        }

        result = ProductsService.is_valid_product_creation_request(data_invalid_types)

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "must be a string" in error_text or "must be a valid" in error_text
        assert "Year must be a valid integer" in error_text
        assert "Price must be a valid number" in error_text
        assert "Total inventory must be a valid integer" in error_text

    def test_invalid_date_formats(self):
        """Test validation fails for invalid date formats"""
        data_invalid_dates = {
            "sportName": "Dodgeball",
            "dayOfPlay": "Thursday",
            "division": "Advanced",
            "season": "Summer",
            "year": "2025",
            "location": "Elliott Center",
            "leagueStartTime": "7:00 PM",
            "leagueEndTime": "9:00 PM",
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": "not_a_date",  # Invalid date
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "offDates": [
                    "also_not_a_date",
                    "2025-11-26T04:00:00.000Z",
                ],  # Mixed valid/invalid
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 130, "totalInventory": 48},
        }

        result = ProductsService.is_valid_product_creation_request(data_invalid_dates)

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "must be a valid date format" in error_text

    def test_boundary_values(self):
        """Test validation handles boundary values correctly"""
        # Test year boundaries
        data_year_too_low = {
            "sportName": "Pickleball",
            "dayOfPlay": "Monday",
            "division": "Open",
            "season": "Fall",
            "year": "2023",  # Too low
            "location": "Test",
            "leagueStartTime": "8:00 PM",
            "leagueEndTime": "10:00 PM",
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

        result = ProductsService.is_valid_product_creation_request(data_year_too_low)

        assert result["valid"] is False
        error_text = " ".join(result["errors"])
        assert "Year must be between 2024 and 2030" in error_text
        assert "Price must be greater than 0" in error_text
        assert "Total inventory must be greater than 0" in error_text

    def test_null_and_empty_values(self):
        """Test validation handles null and empty values correctly"""
        data_null_empty = {
            "sportName": "",  # Empty string
            "dayOfPlay": None,  # Null value
            "division": "Open",
            "season": "Fall",
            "year": "2025",
            "location": "   ",  # Whitespace only
            "leagueStartTime": "8:00 PM",
            "leagueEndTime": "10:00 PM",
            "optionalLeagueInfo": {},
            "importantDates": {
                "seasonStartDate": None,  # Null required field
                "seasonEndDate": "2025-12-10T04:00:00.000Z",
                "vetRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-09-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-09-17T23:00:00.000Z",
            },
            "inventoryInfo": {"price": 150, "totalInventory": 64},
        }

        result = ProductsService.is_valid_product_creation_request(data_null_empty)

        assert result["valid"] is False
        assert any("Missing required fields:" in error for error in result["errors"])

    def test_valid_optional_fields(self):
        """Test validation allows optional fields to be None or missing"""
        data_minimal_valid = {
            "sportName": "Kickball",
            "dayOfPlay": "Saturday",
            "division": "WTNB+",
            "season": "Spring",
            "year": "2025",
            "location": "Central Park Field 1",
            "leagueStartTime": "10:00 AM",
            "leagueEndTime": "12:00 PM",
            "alternativeStartTime": None,  # Optional
            "alternativeEndTime": None,  # Optional
            "optionalLeagueInfo": {
                "socialOrAdvanced": None,  # Optional
                "sportSubCategory": None,  # Optional
                "types": None,  # Optional
            },
            "importantDates": {
                "seasonStartDate": "2025-04-01T04:00:00.000Z",
                "seasonEndDate": "2025-06-15T04:00:00.000Z",
                "offDates": None,  # Optional
                "newPlayerOrientationDateTime": None,  # Optional
                "scoutNightDateTime": None,  # Optional
                "openingPartyDate": None,  # Optional
                "rainDate": None,  # Optional
                "closingPartyDate": None,  # Optional
                "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
            },
            "inventoryInfo": {
                "price": 85,
                "totalInventory": 32,
                "numberVetSpotsToReleaseAtGoLive": None,  # Optional
            },
        }

        result = ProductsService.is_valid_product_creation_request(data_minimal_valid)

        assert result["valid"] is True
        assert result["errors"] == []
