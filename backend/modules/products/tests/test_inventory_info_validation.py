"""
Test InventoryInfo model validation
"""

import pytest
from pydantic import ValidationError
from models.products.inventory_info import InventoryInfo


class TestInventoryInfoValidation:
    """Test InventoryInfo model validation"""

    def test_valid_inventory_info(self):
        """Test that valid inventory info passes validation"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            "numberVetSpotsToReleaseAtGoLive": 40,
        }

        inventory_info = InventoryInfo(**data)

        assert inventory_info.price == 150.0
        assert inventory_info.totalInventory == 64
        assert inventory_info.numberVetSpotsToReleaseAtGoLive == 40

    def test_missing_number_vet_spots_fails(self):
        """Test that missing numberVetSpotsToReleaseAtGoLive fails validation"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            # Missing numberVetSpotsToReleaseAtGoLive
        }

        with pytest.raises(ValidationError) as exc_info:
            InventoryInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert "numberVetSpotsToReleaseAtGoLive" in errors[0]["loc"]

    def test_negative_vet_spots_fails(self):
        """Test that negative numberVetSpotsToReleaseAtGoLive fails validation"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            "numberVetSpotsToReleaseAtGoLive": -5,
        }

        with pytest.raises(ValidationError) as exc_info:
            InventoryInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "must be non-negative" in errors[0]["msg"]

    def test_string_vet_spots_converted(self):
        """Test that string vet spots are converted to int"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            "numberVetSpotsToReleaseAtGoLive": "40",
        }

        inventory_info = InventoryInfo(**data)
        assert inventory_info.numberVetSpotsToReleaseAtGoLive == 40
        assert isinstance(inventory_info.numberVetSpotsToReleaseAtGoLive, int)

    def test_invalid_string_vet_spots_fails(self):
        """Test that invalid string vet spots fail validation"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            "numberVetSpotsToReleaseAtGoLive": "not_a_number",
        }

        with pytest.raises(ValidationError) as exc_info:
            InventoryInfo(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "must be a valid integer" in errors[0]["msg"]

    def test_zero_vet_spots_allowed(self):
        """Test that zero vet spots is allowed"""
        data = {
            "price": 150.0,
            "totalInventory": 64,
            "numberVetSpotsToReleaseAtGoLive": 0,
        }

        inventory_info = InventoryInfo(**data)
        assert inventory_info.numberVetSpotsToReleaseAtGoLive == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
