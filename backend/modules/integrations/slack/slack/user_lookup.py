"""Slack user lookup — thin wrapper around shared_utilities.

Pure lookup functions live in shared_utilities.clients.slack.user_lookup.
This module re-exports them and adds enrich_hierarchy (backend-only, uses LeadershipHierarchy).
"""

from typing import TYPE_CHECKING, Dict, Optional

from slack_sdk import WebClient

# Re-export all pure functions from shared_utilities
from shared_utilities.clients.slack.user_lookup import (
    find_candidates_by_last_name,
    list_all_users,
    lookup_user,
    lookup_user_by_email,
    lookup_user_by_id,
    lookup_user_ids_by_emails,
)

import logging

if TYPE_CHECKING:
    from modules.leadership.domain.models import LeadershipHierarchy

logger = logging.getLogger(__name__)

__all__ = [
    "list_all_users",
    "find_candidates_by_last_name",
    "lookup_user",
    "lookup_user_by_email",
    "lookup_user_by_id",
    "lookup_user_ids_by_emails",
    "enrich_hierarchy",
]


def enrich_hierarchy(
    client: WebClient,
    hierarchy: "LeadershipHierarchy",
    max_workers: int = 10,
) -> Dict[str, Optional[str]]:
    """Enrich a leadership hierarchy with Slack user IDs (backend-only)."""
    emails = hierarchy.get_all_emails()
    if not emails:
        logger.warning("No emails found in hierarchy to enrich")
        return {}

    results = lookup_user_ids_by_emails(client=client, emails=emails, max_workers=max_workers)
    _add_slack_ids_to_hierarchy(hierarchy, results)
    found = sum(1 for uid in results.values() if uid)
    logger.info("Enrichment complete: %d/%d Slack user IDs found", found, len(emails))
    return results


def _add_slack_ids_to_hierarchy(
    hierarchy: "LeadershipHierarchy",
    results: Dict[str, Optional[str]],
) -> None:
    hierarchy_dict = hierarchy.to_dict()
    for section_key, section_data in hierarchy_dict.items():
        if section_key == "vacant_positions":
            continue
        if isinstance(section_data, list):
            for person in section_data:
                if person and isinstance(person, dict):
                    bars_email = person.get("bars_email", "").strip()
                    if bars_email:
                        person["slack_user_id"] = results.get(bars_email)
            continue
        if isinstance(section_data, dict):
            _enrich_nested_dict(section_data, results)


def _enrich_nested_dict(data: Dict, results: Dict[str, Optional[str]]) -> None:
    for value in data.values():
        if isinstance(value, dict):
            if "bars_email" in value:
                bars_email = value.get("bars_email", "").strip()
                if bars_email:
                    value["slack_user_id"] = results.get(bars_email)
            else:
                _enrich_nested_dict(value, results)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    if "bars_email" in item:
                        bars_email = item.get("bars_email", "").strip()
                        if bars_email:
                            item["slack_user_id"] = results.get(bars_email)
                    else:
                        _enrich_nested_dict(item, results)
