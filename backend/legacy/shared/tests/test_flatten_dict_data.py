"""
Tests for flatten_dict_data utility function.
"""

import pytest
from shared.dict_utils import flatten_dict_data


@pytest.fixture
def simple_dict():
    """Simple flat dictionary fixture."""
    return {"name": "John", "age": 30, "city": "New York"}


@pytest.fixture
def nested_dict():
    """Nested dictionary fixture."""
    return {
        "user": {"name": "John", "age": 30},
        "status": "active"
    }


@pytest.fixture
def deeply_nested_dict():
    """Deeply nested dictionary fixture."""
    return {
        "product": {
            "info": {"name": "Widget", "price": 100},
            "category": "electronics",
        },
        "vendor": "ACME",
    }


@pytest.fixture
def dict_with_none():
    """Dictionary with None values fixture."""
    return {
        "name": "John",
        "address": {"street": None, "city": "New York"},
        "phone": None,
    }


@pytest.fixture
def dict_with_empty_nested():
    """Dictionary with empty nested dict fixture."""
    return {
        "name": "John",
        "address": {},
        "contact": {"email": "john@example.com"},
    }


class TestFlattenDictData:
    """Test flatten_dict_data utility function."""

    def test_flatten_simple_dict(self, simple_dict):
        """Test flattening a simple flat dictionary."""
        result = flatten_dict_data(simple_dict)
        assert result == {"name": "John", "age": 30, "city": "New York"}

    def test_flatten_nested_dict(self, nested_dict):
        """Test flattening a nested dictionary with dot notation."""
        result = flatten_dict_data(nested_dict)
        expected = {"user.name": "John", "user.age": 30, "status": "active"}
        assert result == expected

    def test_flatten_deeply_nested_dict(self, deeply_nested_dict):
        """Test flattening a deeply nested dictionary."""
        result = flatten_dict_data(deeply_nested_dict)
        expected = {
            "product.info.name": "Widget",
            "product.info.price": 100,
            "product.category": "electronics",
            "vendor": "ACME",
        }
        assert result == expected

    def test_flatten_with_none_values(self, dict_with_none):
        """Test flattening with None values."""
        result = flatten_dict_data(dict_with_none)
        expected = {
            "name": "John",
            "address.street": None,
            "address.city": "New York",
            "phone": None
        }
        assert result == expected

    def test_flatten_with_empty_nested_dict(self, dict_with_empty_nested):
        """Test flattening with empty nested dictionaries."""
        result = flatten_dict_data(dict_with_empty_nested)
        expected = {"name": "John", "contact.email": "john@example.com"}
        assert result == expected

    @pytest.mark.parametrize("input_dict,expected", [
        (
            {"a": {"b": 1}, "c": 2},
            {"a.b": 1, "c": 2}
        ),
        (
            {"level1": {"level2": {"level3": "value"}}},
            {"level1.level2.level3": "value"}
        ),
        (
            {"top": "value", "nested": {"middle": {"bottom": "deep"}}},
            {"top": "value", "nested.middle.bottom": "deep"}
        ),
    ])
    def test_flatten_various_structures(self, input_dict, expected):
        """Test flattening various nested structures using parameterization."""
        result = flatten_dict_data(input_dict)
        assert result == expected

    def test_flatten_with_custom_result_dict(self, nested_dict):
        """Test that custom result dict is used and updated."""
        result = {"existing": "key"}
        flatten_dict_data(nested_dict, result=result)
        assert "existing" in result
        assert "user.name" in result
        assert result["existing"] == "key"

    def test_flatten_with_custom_prefix(self, simple_dict):
        """Test flattening with a custom prefix."""
        result = flatten_dict_data(simple_dict, prefix="data")
        expected = {
            "data.name": "John",
            "data.age": 30,
            "data.city": "New York"
        }
        assert result == expected
