"""
Tests for Google Request Models

Basic tests to verify the new request model architecture works correctly.
"""

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError

from modules.integrations.google.models.requests import (
    GoogleUserIdentifierRequest,
    GoogleGroupIdentifierRequest,
    GoogleGroupMemberRequest,
    GoogleGroupCreateRequest,
    GoogleUserCreateRequest
)
from shared.api_models import ValidationAPIError


class TestGoogleUserIdentifierRequest:
    """Test GoogleUserIdentifierRequest validation and parsing."""

    def test_valid_email_identifier(self):
        """Test valid email identifier."""
        request = GoogleUserIdentifierRequest(identifier="user@example.com")
        parsed = request.parse()
        assert parsed == {"email": "user@example.com"}

    def test_valid_user_id_identifier(self):
        """Test valid user ID identifier."""
        request = GoogleUserIdentifierRequest(identifier="123456789")
        parsed = request.parse()
        assert parsed == {"user_id": "123456789"}

    def test_empty_identifier(self):
        """Test empty identifier raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserIdentifierRequest(identifier="")

    def test_whitespace_identifier(self):
        """Test whitespace-only identifier raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserIdentifierRequest(identifier="   ")

    def test_invalid_email_format(self):
        """Test invalid email format raises validation error."""
        request = GoogleUserIdentifierRequest(identifier="invalid-email")
        with pytest.raises(ValidationAPIError):
            request.parse()


class TestGoogleGroupIdentifierRequest:
    """Test GoogleGroupIdentifierRequest validation and parsing."""

    def test_valid_group_email_identifier(self):
        """Test valid group email identifier."""
        request = GoogleGroupIdentifierRequest(identifier="group@example.com")
        parsed = request.parse()
        assert parsed == {"group_email": "group@example.com"}

    def test_valid_group_id_identifier(self):
        """Test valid group ID identifier."""
        request = GoogleGroupIdentifierRequest(identifier="123456789")
        parsed = request.parse()
        assert parsed == {"group_id": "123456789"}

    def test_invalid_group_email_format(self):
        """Test invalid group email format raises validation error."""
        request = GoogleGroupIdentifierRequest(identifier="invalid-email")
        with pytest.raises(ValidationAPIError):
            request.parse()


class TestGoogleGroupMemberRequest:
    """Test GoogleGroupMemberRequest validation."""

    def test_valid_member_request(self):
        """Test valid member request."""
        request = GoogleGroupMemberRequest(
            group_email="group@example.com",
            member_email="user@example.com",
            role="MEMBER"
        )
        assert request.group_email == "group@example.com"
        assert request.member_email == "user@example.com"
        assert request.role == "MEMBER"

    def test_invalid_group_email(self):
        """Test invalid group email raises validation error."""
        with pytest.raises(ValidationError):
            GoogleGroupMemberRequest(
                group_email="invalid-email",
                member_email="user@example.com",
                role="MEMBER"
            )

    def test_invalid_member_email(self):
        """Test invalid member email raises validation error."""
        with pytest.raises(ValidationError):
            GoogleGroupMemberRequest(
                group_email="group@example.com",
                member_email="invalid-email",
                role="MEMBER"
            )

    def test_invalid_role(self):
        """Test invalid role raises validation error."""
        with pytest.raises(ValidationError):
            GoogleGroupMemberRequest(
                group_email="group@example.com",
                member_email="user@example.com",
                role="INVALID_ROLE"
            )

    def test_default_role(self):
        """Test default role is MEMBER."""
        request = GoogleGroupMemberRequest(
            group_email="group@example.com",
            member_email="user@example.com"
        )
        assert request.role == "MEMBER"


class TestGoogleGroupCreateRequest:
    """Test GoogleGroupCreateRequest validation."""

    def test_valid_group_create_request(self):
        """Test valid group create request."""
        request = GoogleGroupCreateRequest(
            email="group@example.com",
            name="Test Group",
            description="A test group"
        )
        assert request.email == "group@example.com"
        assert request.name == "Test Group"
        assert request.description == "A test group"

    def test_group_create_without_description(self):
        """Test group create request without description."""
        request = GoogleGroupCreateRequest(
            email="group@example.com",
            name="Test Group"
        )
        assert request.email == "group@example.com"
        assert request.name == "Test Group"
        assert request.description is None

    def test_invalid_email_format(self):
        """Test invalid email format raises validation error."""
        with pytest.raises(ValidationError):
            GoogleGroupCreateRequest(
                email="invalid-email",
                name="Test Group"
            )


class TestGoogleUserCreateRequest:
    """Test GoogleUserCreateRequest validation."""

    def test_valid_user_create_request(self):
        """Test valid user create request."""
        request = GoogleUserCreateRequest(
            primary_email="user@example.com",
            given_name="John",
            family_name="Doe",
            recovery_email="backup@example.com"
        )
        assert request.primary_email == "user@example.com"
        assert request.given_name == "John"
        assert request.family_name == "Doe"
        assert request.recovery_email == "backup@example.com"
        assert request.change_password_at_next_login is True

    def test_user_create_minimal_fields(self):
        """Test user create request with minimal fields."""
        request = GoogleUserCreateRequest(
            primary_email="user@example.com",
            given_name="John",
            family_name="Doe"
        )
        assert request.primary_email == "user@example.com"
        assert request.given_name == "John"
        assert request.family_name == "Doe"
        assert request.recovery_email is None
        assert request.password is None
        assert request.org_unit_path is None

    def test_invalid_primary_email(self):
        """Test invalid primary email raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserCreateRequest(
                primary_email="invalid-email",
                given_name="John",
                family_name="Doe"
            )

    def test_invalid_recovery_email(self):
        """Test invalid recovery email raises validation error."""
        with pytest.raises(ValidationError):
            GoogleUserCreateRequest(
                primary_email="user@example.com",
                given_name="John",
                family_name="Doe",
                recovery_email="invalid-email"
            )

    def test_none_recovery_email_is_valid(self):
        """Test None recovery email is valid."""
        request = GoogleUserCreateRequest(
            primary_email="user@example.com",
            given_name="John",
            family_name="Doe",
            recovery_email=None
        )
        assert request.recovery_email is None


class TestRequestModelServiceIntegration:
    """Test request models integrate properly with Google API services."""

    @patch('modules.integrations.google.models.requests.build_google_api_service')
    def test_user_request_service_integration(self, mock_build_service):
        """Test user request integrates with Google API service."""
        # Mock the service and its methods
        mock_service = Mock()
        mock_users = Mock()
        mock_service.users.return_value = mock_users
        mock_users.get.return_value.execute.return_value = {"id": "123", "primaryEmail": "user@example.com"}
        mock_build_service.return_value = mock_service

        # Create request and execute
        request = GoogleUserIdentifierRequest(identifier="user@example.com")
        result = request.execute_get_user()

        # Verify service was built with correct parameters
        mock_build_service.assert_called_once_with('admin', 'directory_v1', [
            'https://www.googleapis.com/auth/admin.directory.group',
            'https://www.googleapis.com/auth/admin.directory.group.member',
            'https://www.googleapis.com/auth/admin.directory.user',
        ])

        # Verify API call was made correctly
        mock_users.get.assert_called_once_with(userKey="user@example.com")
        assert result == {"id": "123", "primaryEmail": "user@example.com"}

    @patch('modules.integrations.google.models.requests.build_google_api_service')
    def test_group_member_request_service_integration(self, mock_build_service):
        """Test group member request integrates with Google API service."""
        # Mock the service and its methods
        mock_service = Mock()
        mock_members = Mock()
        mock_service.members.return_value = mock_members
        mock_members.insert.return_value.execute.return_value = {
            "email": "user@example.com",
            "role": "MEMBER"
        }
        mock_build_service.return_value = mock_service

        # Create request and execute
        request = GoogleGroupMemberRequest(
            group_email="group@example.com",
            member_email="user@example.com",
            role="MEMBER"
        )
        result = request.execute_add_member()

        # Verify service was built with correct parameters
        mock_build_service.assert_called_once()

        # Verify API call was made correctly
        mock_members.insert.assert_called_once_with(
            groupKey="group@example.com",
            body={"email": "user@example.com", "role": "MEMBER"}
        )
        assert result == {"email": "user@example.com", "role": "MEMBER"}