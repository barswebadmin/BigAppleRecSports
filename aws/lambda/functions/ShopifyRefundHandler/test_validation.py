"""Tests for the fuzzy email/name matching against a Shopify order's metadata.

We use lightweight dataclass stand-ins for the Shopify codegen types so these
tests run without httpx / a live schema. The validation module accepts any
duck-typed object that satisfies its ``OrderLike`` Protocol; these fakes do.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from validation import (
    email_candidates,
    first_name_candidates,
    last_name_candidates,
    validate_request_against_order,
)


# --- Stand-ins for the codegen'd Shopify types ------------------------------


@dataclass
class FakeAttr:
    key: str
    value: str | None


@dataclass
class FakeLineItem:
    custom_attributes: list[FakeAttr] = field(default_factory=list)


@dataclass
class FakeCustomer:
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@dataclass
class FakeLineItems:
    nodes: list[FakeLineItem] = field(default_factory=list)


@dataclass
class FakeOrder:
    line_items: FakeLineItems
    customer: FakeCustomer | None = None
    email: str | None = None


def _order(
    attrs: list[tuple[str, str | None]] | None = None,
    *,
    billing_email: str | None = None,
    customer_email: str | None = None,
    customer_first: str | None = None,
    customer_last: str | None = None,
) -> FakeOrder:
    line_item = FakeLineItem(
        custom_attributes=[FakeAttr(key=k, value=v) for k, v in (attrs or [])]
    )
    return FakeOrder(
        line_items=FakeLineItems(nodes=[line_item]),
        customer=FakeCustomer(
            email=customer_email, first_name=customer_first, last_name=customer_last
        ),
        email=billing_email,
    )


# --- Email candidate harvesting --------------------------------------------


def test_email_candidates_pulls_any_attribute_with_email_address_in_key():
    """Three different form field labels containing 'email address' all surface."""
    order = _order([
        ("Best Contact Email Address", "best@example.com"),
        ("Player Email Address", "player@example.com"),
        ("Backup Email Address", "backup@example.com"),
        ("First Name", "Jane"),  # unrelated — must NOT appear
    ])
    pairs = email_candidates(order)
    assert ("Best Contact Email Address", "best@example.com") in pairs
    assert ("Player Email Address", "player@example.com") in pairs
    assert ("Backup Email Address", "backup@example.com") in pairs
    assert all("Name" not in label for label, _ in pairs)


def test_email_candidates_match_is_case_insensitive_on_the_attribute_key():
    order = _order([("BEST CONTACT email Address", "x@x.com"), ("emailaddress", "y@y.com")])
    pairs = email_candidates(order)
    # "BEST CONTACT email Address" contains the substring "email address" (case-insensitive)
    assert ("BEST CONTACT email Address", "x@x.com") in pairs
    # "emailaddress" (no space) does NOT contain "email address" (space matters)
    assert not any(label == "emailaddress" for label, _ in pairs)


def test_email_candidates_skips_attributes_with_blank_values():
    order = _order([("Best Contact Email Address", ""), ("Player Email Address", None)])
    pairs = email_candidates(order)
    assert pairs == []  # empty/None values filtered out


def test_email_candidates_includes_order_billing_and_customer_emails():
    order = _order(
        billing_email="billing@example.com",
        customer_email="customer@example.com",
    )
    pairs = email_candidates(order)
    assert ("order.email", "billing@example.com") in pairs
    assert ("order.customer.email", "customer@example.com") in pairs


# --- First/last name candidate harvesting ----------------------------------


def test_first_name_candidates_includes_preferred_first_name_variants():
    order = _order([
        ("First Name", "Jane"),
        ("Preferred First Name", "Jenny"),
        ("preferred_first_name", "Jen"),  # GAS form field name variant
    ])
    pairs = first_name_candidates(order)
    labels = [label for label, _ in pairs]
    assert "First Name" in labels
    assert "Preferred First Name" in labels
    assert "preferred_first_name" in labels


def test_last_name_candidates_falls_back_to_customer_when_no_line_item_attribute():
    order = _order(customer_last="Doe")
    pairs = last_name_candidates(order)
    assert pairs == [("order.customer.lastName", "Doe")]


# --- End-to-end validation -------------------------------------------------


def test_all_three_checks_pass_with_canonical_payload():
    """Happy path: form-submitted email/first/last match Best-Contact-Email and
    First/Last Name line-item attributes verbatim."""
    order = _order([
        ("Best Contact Email Address", "jane@example.com"),
        ("First Name", "Jane"),
        ("Last Name", "Doe"),
    ])
    result = validate_request_against_order(
        request_email="jane@example.com",
        request_first_name="Jane",
        request_last_name="Doe",
        order=order,
    )
    assert result.all_passed
    assert result.email.matched_against == "Best Contact Email Address"
    assert result.first_name.matched_against == "First Name"
    assert result.last_name.matched_against == "Last Name"
    assert result.warnings == []


def test_case_and_whitespace_are_normalized_during_comparison():
    order = _order([("Best Contact Email Address", "  Jane@Example.COM  ")])
    result = validate_request_against_order(
        request_email="JANE@example.com",
        request_first_name="x",
        request_last_name="x",
        order=order,
    )
    assert result.email.matched
    assert result.email.matched_against == "Best Contact Email Address"


def test_email_match_picks_any_address_among_candidates():
    """The request email need only match ONE of the multiple addresses on the order."""
    order = _order([
        ("Best Contact Email Address", "best@example.com"),
        ("Player Email Address", "player@example.com"),
    ])
    result = validate_request_against_order(
        request_email="player@example.com",
        request_first_name="x",
        request_last_name="x",
        order=order,
    )
    assert result.email.matched
    assert result.email.matched_against == "Player Email Address"


def test_billing_email_matches_when_no_line_item_email_attribute():
    """A registration that didn't ask "best contact" still has the billing email."""
    order = _order(billing_email="billing@example.com")
    result = validate_request_against_order(
        request_email="billing@example.com",
        request_first_name="x",
        request_last_name="x",
        order=order,
    )
    assert result.email.matched
    assert result.email.matched_against == "order.email"


def test_no_candidates_means_no_match_and_a_warning():
    order = _order()  # no attributes, no customer, no billing
    result = validate_request_against_order(
        request_email="jane@example.com",
        request_first_name="Jane",
        request_last_name="Doe",
        order=order,
    )
    assert not result.email.matched
    assert not result.first_name.matched
    assert not result.last_name.matched
    assert len(result.warnings) == 3


def test_partial_failure_returns_per_field_warnings():
    """Email matches, names don't → exactly two warnings, email branch passed."""
    order = _order([("Best Contact Email Address", "jane@example.com")])
    result = validate_request_against_order(
        request_email="jane@example.com",
        request_first_name="WrongFirst",
        request_last_name="WrongLast",
        order=order,
    )
    assert result.email.matched
    assert not result.first_name.matched
    assert not result.last_name.matched
    assert not result.all_passed
    assert len(result.warnings) == 2
    assert all("First name" in w or "Last name" in w for w in result.warnings)


@pytest.mark.parametrize(
    "request_value",
    ["", "   ", "\t\n"],
)
def test_empty_request_value_never_matches(request_value):
    """An empty/whitespace request field can't accidentally match an empty candidate."""
    order = _order([("Best Contact Email Address", "jane@example.com")])
    result = validate_request_against_order(
        request_email=request_value,
        request_first_name="x",
        request_last_name="x",
        order=order,
    )
    assert not result.email.matched
