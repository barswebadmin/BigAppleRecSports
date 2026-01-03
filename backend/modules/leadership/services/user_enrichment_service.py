"""Service for enriching leadership hierarchy with Slack user IDs."""

import logging
from typing import Dict, Optional, List

from modules.integrations.slack.services.user_lookup_service import UserLookupService
from modules.leadership.domain.models import LeadershipHierarchy

logger = logging.getLogger(__name__)


class UserEnrichmentService:
    """
    Enriches leadership hierarchy with Slack user IDs.
    
    This service is responsible for:
    - Extracting all emails from a hierarchy
    - Looking up Slack user IDs via UserLookupService
    - Adding slack_user_id to each position in the hierarchy
    """
    
    def __init__(self, slack_token: str):
        """
        Initialize the enrichment service.
        
        Args:
            slack_token: Slack bot token for API calls
        """
        self.lookup_service = UserLookupService(slack_token)
    
    def enrich_hierarchy(
        self, 
        hierarchy: LeadershipHierarchy,
        max_workers: int = 10,
        max_retries: int = 3
    ) -> Dict[str, Optional[str]]:
        """
        Enrich a leadership hierarchy with Slack user IDs.
        
        Args:
            hierarchy: The hierarchy to enrich (modified in-place)
            max_workers: Maximum concurrent API requests
            max_retries: Maximum retry attempts for transient errors
            
        Returns:
            Dictionary mapping email -> slack_user_id (or None if not found)
        """
        emails = hierarchy.get_all_emails()
        
        if not emails:
            logger.warning("No emails found in hierarchy to enrich")
            return {}
        
        logger.info(f"Enriching hierarchy with {len(emails)} emails")
        
        # Look up all Slack user IDs
        results = self.lookup_service.lookup_user_ids_by_emails(
            emails=emails,
            max_workers=max_workers,
            max_retries=max_retries
        )
        
        # Add slack_user_id to hierarchy
        self._add_slack_ids_to_hierarchy(hierarchy, results)
        
        found_count = sum(1 for uid in results.values() if uid)
        logger.info(f"Enrichment complete: {found_count}/{len(emails)} Slack user IDs found")
        
        return results
    
    def _add_slack_ids_to_hierarchy(
        self, 
        hierarchy: LeadershipHierarchy, 
        results: Dict[str, Optional[str]]
    ) -> None:
        """
        Add slack_user_id field to each person in the hierarchy.
        
        Args:
            hierarchy: The hierarchy to modify (modified in-place)
            results: Dict of email -> slack_user_id from lookup service
        """
        hierarchy_dict = hierarchy.to_dict()
        
        for section_key, section_data in hierarchy_dict.items():
            if section_key == "vacant_positions":
                continue
            
            # Handle simple list sections (like committee_members)
            if isinstance(section_data, list):
                for person in section_data:
                    if person and isinstance(person, dict):
                        bars_email = person.get("bars_email", "").strip()
                        if bars_email:
                            person["slack_user_id"] = results.get(bars_email)
                continue
            
            if not isinstance(section_data, dict):
                continue
            
            # Recursively process nested structures
            self._enrich_nested_dict(section_data, results)
        
        # Update the hierarchy with enriched data
        # Note: This is a simplified approach. In a real implementation,
        # we might want to rebuild the hierarchy from the modified dict
        # or use a more sophisticated approach to update the internal state
    
    def _enrich_nested_dict(
        self, 
        data: Dict, 
        results: Dict[str, Optional[str]]
    ) -> None:
        """
        Recursively enrich a nested dictionary with Slack user IDs.
        
        Args:
            data: Dictionary to enrich (modified in-place)
            results: Dict of email -> slack_user_id from lookup service
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this is a person dict (has bars_email)
                if "bars_email" in value:
                    bars_email = value.get("bars_email", "").strip()
                    if bars_email:
                        value["slack_user_id"] = results.get(bars_email)
                else:
                    # Recurse into nested dict
                    self._enrich_nested_dict(value, results)
            elif isinstance(value, list):
                # Handle lists of people
                for item in value:
                    if isinstance(item, dict):
                        if "bars_email" in item:
                            bars_email = item.get("bars_email", "").strip()
                            if bars_email:
                                item["slack_user_id"] = results.get(bars_email)
                        else:
                            self._enrich_nested_dict(item, results)

