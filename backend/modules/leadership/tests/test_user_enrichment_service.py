"""Tests for UserEnrichmentService."""

import pytest
from unittest.mock import MagicMock, patch

from modules.leadership.services.user_enrichment_service import UserEnrichmentService
from modules.leadership.domain.models import LeadershipHierarchy, LeadershipMember


class TestUserEnrichmentService:
    """Test suite for UserEnrichmentService."""
    
    @pytest.fixture
    def mock_lookup_service(self):
        """Mock UserLookupService."""
        with patch('modules.leadership.services.user_enrichment_service.UserLookupService') as mock:
            yield mock
    
    @pytest.fixture
    def enrichment_service(self, mock_lookup_service):
        """Create an enrichment service with mocked lookup."""
        service = UserEnrichmentService(slack_token="test-token")
        return service
    
    @pytest.fixture
    def sample_hierarchy(self):
        """Create a sample hierarchy for testing."""
        hierarchy = LeadershipHierarchy()
        
        # Add some positions
        hierarchy.add_position(
            section="executive_board",
            role="commissioner",
            person=LeadershipMember(
                name="John Doe",
                personal_email="john@gmail.com",
                role="executive_board.commissioner",
                bars_email="john@bars.com",
                phone="111-222-3333",
                birthday="01/15"
            )
        )
        
        hierarchy.add_position(
            section="executive_board",
            role="vice_commissioner",
            person=LeadershipMember(
                name="Jane Smith",
                personal_email="jane@gmail.com",
                role="executive_board.vice_commissioner",
                bars_email="jane@bars.com"
            )
        )
        
        # Add a vacant position
        hierarchy.add_position(
            section="executive_board",
            role="treasurer",
            person=LeadershipMember(
                name="Vacant",
                personal_email="vacant@placeholder.com",
                role="executive_board.treasurer"
            )
        )
        
        # Add a committee member
        hierarchy.add_position(
            section="committee_members",
            role="member",
            person=LeadershipMember(
                name="Alice Johnson",
                personal_email="alice@gmail.com",
                role="committee_members.member",
                bars_email="alice@bars.com"
            )
        )
        
        return hierarchy
    
    def test_service_initialization(self, mock_lookup_service):
        """Test that service initializes correctly."""
        service = UserEnrichmentService(slack_token="test-token")
        
        assert service.lookup_service is not None
        mock_lookup_service.assert_called_once_with("test-token")
    
    def test_enrich_hierarchy_with_found_users(self, enrichment_service, sample_hierarchy, mock_lookup_service):
        """Test enriching hierarchy when Slack users are found."""
        # Mock the lookup results
        mock_instance = mock_lookup_service.return_value
        mock_instance.lookup_user_ids_by_emails.return_value = {
            "john@bars.com": "U123ABC",
            "jane@bars.com": "U456DEF",
            "alice@bars.com": "U789GHI"
        }
        enrichment_service.lookup_service = mock_instance
        
        # Enrich the hierarchy
        results = enrichment_service.enrich_hierarchy(sample_hierarchy)
        
        # Verify lookup was called with correct emails
        mock_instance.lookup_user_ids_by_emails.assert_called_once()
        call_args = mock_instance.lookup_user_ids_by_emails.call_args
        emails = call_args.kwargs['emails']
        assert set(emails) == {"john@bars.com", "jane@bars.com", "alice@bars.com"}
        
        # Verify results
        assert results["john@bars.com"] == "U123ABC"
        assert results["jane@bars.com"] == "U456DEF"
        assert results["alice@bars.com"] == "U789GHI"
    
    def test_enrich_hierarchy_with_not_found_users(self, enrichment_service, sample_hierarchy, mock_lookup_service):
        """Test enriching hierarchy when some Slack users are not found."""
        # Mock the lookup results with some None values
        mock_instance = mock_lookup_service.return_value
        mock_instance.lookup_user_ids_by_emails.return_value = {
            "john@bars.com": "U123ABC",
            "jane@bars.com": None,  # Not found
            "alice@bars.com": "U789GHI"
        }
        enrichment_service.lookup_service = mock_instance
        
        # Enrich the hierarchy
        results = enrichment_service.enrich_hierarchy(sample_hierarchy)
        
        # Verify results include None for not found
        assert results["john@bars.com"] == "U123ABC"
        assert results["jane@bars.com"] is None
        assert results["alice@bars.com"] == "U789GHI"
    
    def test_enrich_hierarchy_with_no_emails(self, enrichment_service, mock_lookup_service):
        """Test enriching hierarchy when no emails are present."""
        empty_hierarchy = LeadershipHierarchy()
        
        # Enrich the empty hierarchy
        results = enrichment_service.enrich_hierarchy(empty_hierarchy)
        
        # Verify no lookup was performed
        assert results == {}
    
    def test_enrich_hierarchy_passes_correct_parameters(self, enrichment_service, sample_hierarchy, mock_lookup_service):
        """Test that enrich_hierarchy passes max_workers and max_retries correctly."""
        mock_instance = mock_lookup_service.return_value
        mock_instance.lookup_user_ids_by_emails.return_value = {}
        enrichment_service.lookup_service = mock_instance
        
        # Enrich with custom parameters
        enrichment_service.enrich_hierarchy(
            sample_hierarchy,
            max_workers=5,
            max_retries=2
        )
        
        # Verify parameters were passed
        call_args = mock_instance.lookup_user_ids_by_emails.call_args
        assert call_args.kwargs['max_workers'] == 5
        assert call_args.kwargs['max_retries'] == 2
    
    def test_add_slack_ids_to_flat_structure(self, enrichment_service):
        """Test adding Slack IDs to a flat hierarchy structure."""
        hierarchy = LeadershipHierarchy()
        hierarchy.add_position(
            section="executive_board",
            role="commissioner",
            person=LeadershipMember(
                name="John Doe",
                personal_email="john@gmail.com",
                role="executive_board.commissioner",
                bars_email="john@bars.com"
            )
        )
        
        results = {
            "john@bars.com": "U123ABC"
        }
        
        enrichment_service._add_slack_ids_to_hierarchy(hierarchy, results)
        
        # Get the enriched dict
        hierarchy_dict = hierarchy.to_dict()
        
        # Verify slack_user_id was added
        assert hierarchy_dict["executive_board"]["commissioner"]["slack_user_id"] == "U123ABC"
    
    def test_add_slack_ids_to_nested_structure(self, enrichment_service):
        """Test adding Slack IDs to a nested hierarchy structure."""
        hierarchy = LeadershipHierarchy()
        
        # Add nested positions (like dodgeball.smallball_advanced.director)
        hierarchy.add_position(
            section="dodgeball",
            role="director",
            person=LeadershipMember(
                name="Jane Smith",
                personal_email="jane@gmail.com",
                role="dodgeball.smallball_advanced.director",
                bars_email="jane@bars.com"
            ),
            sub_section="smallball_advanced"
        )
        
        results = {
            "jane@bars.com": "U456DEF"
        }
        
        enrichment_service._add_slack_ids_to_hierarchy(hierarchy, results)
        
        # Get the enriched dict
        hierarchy_dict = hierarchy.to_dict()
        
        # Verify slack_user_id was added to nested structure
        assert hierarchy_dict["dodgeball"]["smallball_advanced"]["director"]["slack_user_id"] == "U456DEF"
    
    def test_add_slack_ids_to_committee_members(self, enrichment_service):
        """Test adding Slack IDs to committee members list."""
        hierarchy = LeadershipHierarchy()
        hierarchy.add_position(
            section="committee_members",
            role="member1",
            person=LeadershipMember(
                name="Alice Johnson",
                personal_email="alice@gmail.com",
                role="committee_members.member1",
                bars_email="alice@bars.com"
            )
        )
        hierarchy.add_position(
            section="committee_members",
            role="member2",
            person=LeadershipMember(
                name="Bob Williams",
                personal_email="bob@gmail.com",
                role="committee_members.member2",
                bars_email="bob@bars.com"
            )
        )
        
        results = {
            "alice@bars.com": "U789GHI",
            "bob@bars.com": "U012JKL"
        }
        
        enrichment_service._add_slack_ids_to_hierarchy(hierarchy, results)
        
        # Get the enriched dict
        hierarchy_dict = hierarchy.to_dict()
        
        # Verify slack_user_ids were added to committee members
        committee = hierarchy_dict["committee_members"]
        assert len(committee) == 2
        assert committee[0]["slack_user_id"] == "U789GHI"
        assert committee[1]["slack_user_id"] == "U012JKL"
    
    def test_enrich_nested_dict_recursively(self, enrichment_service):
        """Test recursive enrichment of nested dictionaries."""
        nested_data = {
            "level1": {
                "level2": {
                    "person1": {
                        "name": "John Doe",
                        "bars_email": "john@bars.com"
                    },
                    "person2": {
                        "name": "Jane Smith",
                        "bars_email": "jane@bars.com"
                    }
                }
            }
        }
        
        results = {
            "john@bars.com": "U123ABC",
            "jane@bars.com": "U456DEF"
        }
        
        enrichment_service._enrich_nested_dict(nested_data, results)
        
        # Verify slack_user_ids were added recursively
        assert nested_data["level1"]["level2"]["person1"]["slack_user_id"] == "U123ABC"
        assert nested_data["level1"]["level2"]["person2"]["slack_user_id"] == "U456DEF"
    
    def test_enrich_nested_dict_with_lists(self, enrichment_service):
        """Test enrichment of dictionaries containing lists of people."""
        data_with_lists = {
            "team": {
                "members": [
                    {"name": "John Doe", "bars_email": "john@bars.com"},
                    {"name": "Jane Smith", "bars_email": "jane@bars.com"}
                ]
            }
        }
        
        results = {
            "john@bars.com": "U123ABC",
            "jane@bars.com": "U456DEF"
        }
        
        enrichment_service._enrich_nested_dict(data_with_lists, results)
        
        # Verify slack_user_ids were added to list items
        members = data_with_lists["team"]["members"]
        assert members[0]["slack_user_id"] == "U123ABC"
        assert members[1]["slack_user_id"] == "U456DEF"
    
    def test_enrich_hierarchy_handles_empty_emails(self, enrichment_service):
        """Test that empty emails are handled gracefully."""
        hierarchy = LeadershipHierarchy()
        hierarchy.add_position(
            section="executive_board",
            role="commissioner",
            person=LeadershipMember(
                name="John Doe",
                personal_email="john@gmail.com",
                role="executive_board.commissioner",
                bars_email="john@bars.com"
            )
        )
        hierarchy.add_position(
            section="executive_board",
            role="vacant_role",
            person=LeadershipMember(
                name="Vacant",
                personal_email="vacant@placeholder.com",
                role="executive_board.vacant_role"
            )
        )
        
        mock_instance = MagicMock()
        mock_instance.lookup_user_ids_by_emails.return_value = {
            "john@bars.com": "U123ABC"
        }
        enrichment_service.lookup_service = mock_instance
        
        # Should only lookup the non-empty email
        results = enrichment_service.enrich_hierarchy(hierarchy)
        
        # Verify only non-empty emails were looked up
        call_args = mock_instance.lookup_user_ids_by_emails.call_args
        emails = call_args.kwargs['emails']
        assert "john@bars.com" in emails
        assert "" not in emails
        assert len(emails) == 1

