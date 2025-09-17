"""
Test suite for create_product service
Tests the product creation business logic
"""

from models.products.product_creation_request import ProductCreationRequest
from services.products.create_product import create_product


class TestCreateProductService:
    """Test class for create_product service"""

    def test_create_product_success(self):
        """Test successful product creation"""
        # Create a valid ProductCreationRequest instance
        valid_data = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": 2025,
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
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

        validated_request = ProductCreationRequest(**valid_data)
        result = create_product(validated_request)

        assert result["success"] is True
        assert result["message"] == "Product created successfully"
        assert "product_id" in result
        assert result["data"]["sport"] == "Dodgeball"
        assert result["data"]["day"] == "Tuesday"
        assert result["data"]["division"] == "Open"
        assert result["data"]["season"] == "Fall 2025"
        assert result["data"]["location"] == "Elliott Center (26th St & 9th Ave)"
        assert result["data"]["price"] == 150
        assert result["data"]["inventory"] == 64

    def test_create_product_with_different_sports(self):
        """Test product creation with different sports"""
        sports_data = [
            {
                "sportName": "Pickleball",
                "location": "Gotham Pickleball (46th and Vernon in LIC)",
                "division": "Open",
                "expected_season": "Spring 2025",
                "socialOrAdvanced": "Social",
            },
            {
                "sportName": "Kickball",
                "location": "Dewitt Clinton Park (52nd St & 11th Ave)",
                "division": "WTNB+",
                "expected_season": "Summer 2025",
                "socialOrAdvanced": "Social",
            },
            {
                "sportName": "Bowling",
                "location": "Frames Bowling Lounge (40th St and 9th Ave)",
                "division": "Open",
                "expected_season": "Winter 2025",
            },
        ]

        for sport_data in sports_data:
            season = sport_data["expected_season"].split()[0]
            valid_data = {
                "sportName": sport_data["sportName"],
                "regularSeasonBasicDetails": {
                    "year": 2025,
                    "season": season,
                    "dayOfPlay": "Wednesday",
                    "division": sport_data["division"],
                    "location": sport_data["location"],
                    "leagueStartTime": "7:00 PM",
                    "leagueEndTime": "9:00 PM",
                    "socialOrAdvanced": sport_data.get("socialOrAdvanced"),
                },
                "optionalLeagueInfo": {},
                "importantDates": {
                    "seasonStartDate": "2025-04-01T04:00:00.000Z",
                    "seasonEndDate": "2025-06-15T04:00:00.000Z",
                    "vetRegistrationStartDateTime": "2025-03-15T23:00:00.000Z",
                    "earlyRegistrationStartDateTime": "2025-03-16T23:00:00.000Z",
                    "openRegistrationStartDateTime": "2025-03-17T23:00:00.000Z",
                },
                "inventoryInfo": {"price": 100, "totalInventory": 48},
            }

            validated_request = ProductCreationRequest(**valid_data)
            result = create_product(validated_request)

            assert result["success"] is True
            assert result["data"]["sport"] == sport_data["sportName"]
            assert result["data"]["season"] == sport_data["expected_season"]
            assert result["data"]["location"] == sport_data["location"]

    def test_create_product_data_structure(self):
        """Test that the returned data structure contains all expected fields"""
        valid_data = {
            "sportName": "Pickleball",
            "regularSeasonBasicDetails": {
                "year": 2025,
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

        validated_request = ProductCreationRequest(**valid_data)
        result = create_product(validated_request)

        # Test top-level structure
        assert "success" in result
        assert "message" in result
        assert "product_id" in result
        assert "data" in result

        # Test data structure
        data = result["data"]
        expected_fields = [
            "sport",
            "day",
            "division",
            "season",
            "location",
            "price",
            "inventory",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

        # Test data types
        assert isinstance(data["sport"], str)
        assert isinstance(data["day"], str)
        assert isinstance(data["division"], str)
        assert isinstance(data["season"], str)
        assert isinstance(data["location"], str)
        assert isinstance(data["price"], (int, float))
        assert isinstance(data["inventory"], int)

    def test_product_id_generation(self):
        """Test that product IDs are generated and unique"""
        valid_data = {
            "sportName": "Dodgeball",
            "regularSeasonBasicDetails": {
                "year": 2025,
                "season": "Fall",
                "dayOfPlay": "Tuesday",
                "division": "Open",
                "location": "Elliott Center (26th St & 9th Ave)",
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
            "inventoryInfo": {"price": 150, "totalInventory": 64},
        }

        validated_request = ProductCreationRequest(**valid_data)

        # Create multiple products and ensure unique IDs
        results = []
        for _ in range(3):
            result = create_product(validated_request)
            results.append(result["product_id"])

        # All IDs should be unique
        assert len(set(results)) == 3

        # All IDs should start with "temp_"
        for product_id in results:
            assert product_id.startswith("temp_")
            assert len(product_id) > 5  # Should be longer than just "temp_"
