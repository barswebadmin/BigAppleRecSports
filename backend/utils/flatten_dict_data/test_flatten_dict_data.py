"""
Tests for flatten_dict_data utility functions
"""

from utils.flatten_dict_data import flatten_dict_data, flatten_dict_data_with_prefix


class TestFlattenDictData:
    """Test flatten_dict_data utility functions"""

    def test_flatten_simple_dict(self):
        """Test flattening a simple flat dictionary"""
        simple_dict = {"name": "John", "age": 30, "city": "New York"}

        result = flatten_dict_data(simple_dict)

        assert result == {"name": "John", "age": 30, "city": "New York"}

    def test_flatten_nested_dict(self):
        """Test flattening a nested dictionary"""
        nested_dict = {
            "name": "John",
            "address": {"street": "123 Main St", "city": "New York", "country": "USA"},
            "age": 30,
        }

        result = flatten_dict_data(nested_dict)

        expected = {
            "name": "John",
            "street": "123 Main St",
            "city": "New York",
            "country": "USA",
            "age": 30,
        }
        assert result == expected

    def test_flatten_deeply_nested_dict(self):
        """Test flattening a deeply nested dictionary"""
        deeply_nested = {
            "level1": {
                "level2": {"level3": {"value": "deep"}, "other": "value2"},
                "simple": "value1",
            },
            "top": "value0",
        }

        result = flatten_dict_data(deeply_nested)

        expected = {
            "value": "deep",
            "other": "value2",
            "simple": "value1",
            "top": "value0",
        }
        assert result == expected

    def test_flatten_with_none_values(self):
        """Test flattening with None values"""
        dict_with_none = {
            "name": "John",
            "address": {"street": None, "city": "New York"},
            "phone": None,
        }

        result = flatten_dict_data(dict_with_none)

        expected = {"name": "John", "street": None, "city": "New York", "phone": None}
        assert result == expected

    def test_flatten_with_empty_nested_dict(self):
        """Test flattening with empty nested dictionaries"""
        dict_with_empty = {
            "name": "John",
            "address": {},
            "contact": {"email": "john@example.com"},
        }

        result = flatten_dict_data(dict_with_empty)

        expected = {"name": "John", "email": "john@example.com"}
        assert result == expected

    def test_flatten_with_prefix_simple(self):
        """Test flatten_dict_data_with_prefix with simple nesting"""
        nested_dict = {"user": {"name": "John", "age": 30}, "status": "active"}

        result = flatten_dict_data_with_prefix(nested_dict)

        expected = {"user.name": "John", "user.age": 30, "status": "active"}
        assert result == expected

    def test_flatten_with_prefix_deep_nesting(self):
        """Test flatten_dict_data_with_prefix with deep nesting"""
        deeply_nested = {
            "product": {
                "info": {"name": "Widget", "price": 100},
                "category": "electronics",
            },
            "vendor": "ACME",
        }

        result = flatten_dict_data_with_prefix(deeply_nested)

        expected = {
            "product.info.name": "Widget",
            "product.info.price": 100,
            "product.category": "electronics",
            "vendor": "ACME",
        }
        assert result == expected

    def test_flatten_product_data_structure(self):
        """Test flattening a structure similar to product data"""
        product_data = {
            "sportName": "Pickleball",
            "division": "Open",
            "optionalLeagueInfo": {
                "socialOrAdvanced": "Advanced",
                "sportSubCategory": "Foam",
                "types": ["Draft"],
            },
            "importantDates": {
                "seasonStartDate": "2025-10-15",
                "seasonEndDate": "2025-12-10",
            },
            "inventoryInfo": {"price": 150, "totalInventory": 64},
        }

        result = flatten_dict_data(product_data)

        expected = {
            "sportName": "Pickleball",
            "division": "Open",
            "socialOrAdvanced": "Advanced",
            "sportSubCategory": "Foam",
            "types": ["Draft"],
            "seasonStartDate": "2025-10-15",
            "seasonEndDate": "2025-12-10",
            "price": 150,
            "totalInventory": 64,
        }
        assert result == expected

    def test_flatten_with_arrays_and_primitives(self):
        """Test flattening with arrays and primitive values"""
        mixed_data = {
            "name": "Test",
            "tags": ["tag1", "tag2"],
            "metadata": {"version": 1.0, "active": True, "items": [1, 2, 3]},
            "count": 42,
        }

        result = flatten_dict_data(mixed_data)

        expected = {
            "name": "Test",
            "tags": ["tag1", "tag2"],
            "version": 1.0,
            "active": True,
            "items": [1, 2, 3],
            "count": 42,
        }
        assert result == expected
