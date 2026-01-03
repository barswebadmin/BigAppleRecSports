"""
Test helpers for leadership hierarchy processing.
Allows testing CSV parsing and hierarchy building without Slack API calls.
"""
import csv
import os
from typing import Dict, List


def process_csv_to_hierarchy(csv_path: str) -> Dict:
    """
    Process a CSV file and build the leadership hierarchy without Slack API calls.
    
    Args:
        csv_path: Path to the CSV file
    
    Returns:
        Dictionary with 'hierarchy' and other metadata
    """
    # Import here to avoid circular imports and Slack initialization
    import sys
    backend_path = os.path.join(os.path.dirname(__file__), '../../../..')
    sys.path.insert(0, backend_path)
    
    from modules.integrations.slack.leadership.handlers import _build_leadership_hierarchy_and_mappings
    
    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        csv_data = list(reader)
    
    # Find header row (row with "POSITION, NAME")
    header_row = None
    for idx, row in enumerate(csv_data):
        if len(row) > 0 and 'POSITION' in row[0].upper() and 'NAME' in ','.join(row).upper():
            header_row = idx
            break
    
    if header_row is None:
        raise ValueError("Could not find header row in CSV")
    
    # Find Position and BARS EMAIL columns
    position_col = None
    email_col = None
    for idx, cell in enumerate(csv_data[header_row]):
        cell_lower = cell.strip().lower()
        if 'position' in cell_lower:
            position_col = idx
        if 'bars email' in cell_lower or 'bars_email' in cell_lower:
            email_col = idx
    
    if position_col is None or email_col is None:
        raise ValueError(f"Could not find required columns. Position: {position_col}, Email: {email_col}")
    
    # Build hierarchy (without Slack lookup)
    result = _build_leadership_hierarchy_and_mappings(csv_data, header_row, position_col, email_col)
    
    return result


def normalize_hierarchy_for_comparison(hierarchy: Dict) -> Dict:
    """
    Normalize hierarchy by removing Slack user IDs for comparison purposes.
    This allows comparing structure and data without comparing Slack API results.
    
    Args:
        hierarchy: The leadership hierarchy dict
    
    Returns:
        Normalized hierarchy dict with slack_user_id removed
    """
    import copy
    import json
    
    # Deep copy to avoid modifying original
    normalized = json.loads(json.dumps(hierarchy))
    
    def remove_slack_ids(obj):
        """Recursively remove slack_user_id fields."""
        if isinstance(obj, dict):
            if 'slack_user_id' in obj:
                del obj['slack_user_id']
            for value in obj.values():
                remove_slack_ids(value)
        elif isinstance(obj, list):
            for item in obj:
                remove_slack_ids(item)
    
    remove_slack_ids(normalized)
    return normalized

