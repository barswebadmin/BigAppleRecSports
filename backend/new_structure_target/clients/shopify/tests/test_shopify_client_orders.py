from unittest.mock import patch
import shopify  # type: ignore

from new_structure_target.clients.shopify.core.shopify_client import get_order_details


class DummyOrder:
    def __init__(self, data):
        self._data = data
        self.attributes = data

    def to_dict(self):
        return self._data


def test_get_order_details_by_id_numeric():
    dummy = DummyOrder({"id": 12345, "name": "#12345", "email": "user@example.com"})
    with patch("new_structure_target.clients.shopify.core.shopify_client.shopify.Order.find", return_value=dummy) as mocked:
        result = get_order_details(order_id="12345")
        assert result["success"] is True
        assert result["order"]["name"] == "#12345"
        mocked.assert_called_once()


def test_get_order_details_by_name_search_first():
    dummy = DummyOrder({"id": 12345, "name": "#12345"})
    with patch.object(shopify.Order, "search", return_value=[dummy], create=True) as mocked_search:
        with patch.object(shopify.Order, "find") as mocked_find:
            result = get_order_details(order_number="#12345")
            assert result["success"] is True
            assert result["order"]["id"] == 12345
            mocked_search.assert_called_once()
            mocked_find.assert_not_called()


def test_get_order_details_by_name_find_search_fallback():
    dummy = DummyOrder({"id": 22222, "name": "#22222"})
    # No search attribute path; ensure find(from_='search', ...) works
    def find_side_effect(*args, **kwargs):
        if kwargs.get("from_") == "search":
            return [dummy]
        return []

    with patch.object(shopify.Order, "find", side_effect=find_side_effect):
        result = get_order_details(order_number="22222")
        assert result["success"] is True
        assert result["order"]["name"] == "#22222"


def test_get_order_details_by_name_find_name_filter_fallback():
    dummy = DummyOrder({"id": 33333, "name": "#33333"})
    # Force find(from_='search', ...) to fail, so the final fallback runs
    def find_side_effect(*args, **kwargs):
        if kwargs.get("from_") == "search" or kwargs.get("q"):
            raise Exception("search endpoint not available")
        if kwargs.get("name") == "#33333":
            return [dummy]
        return []

    with patch.object(shopify.Order, "find", side_effect=find_side_effect):
        result = get_order_details(order_number="#33333")
        assert result["success"] is True
        assert result["order"]["id"] == 33333


