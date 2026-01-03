"""Slack Bolt command and modal handlers for Leadership bot."""

import csv
import io
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
import requests

from slack_bolt import Ack, Say
from slack_sdk import WebClient

from modules.integrations.slack.leadership.bolt_app import app
from modules.integrations.slack.services.user_lookup_service import UserLookupService
from modules.integrations.slack.client.slack_config import SlackConfig
from modules.integrations.slack.builders.modal_handlers import SlackModalHandlers
from shared.csv.csv_processor import CSVProcessor

logger = logging.getLogger(__name__)

# Initialize modal handler for unified modal display
modal_handler = SlackModalHandlers(api_client=None, gas_webhook_url="")


@app.command("/get-user-ids")
def handle_get_user_ids_command(ack: Ack, command: dict, client: WebClient):
    """
    Handle /get-user-ids slash command.
    Opens a modal for CSV paste.
    """
    ack()
    
    user_id = command["user_id"]
    trigger_id = command["trigger_id"]
    
    modal_view = {
        "type": "modal",
        "callback_id": "csv_user_lookup_modal",
        "title": {"type": "plain_text", "text": "Get User IDs"},
        "submit": {"type": "plain_text", "text": "Look Up"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "csv_input_block",
                "label": {
                    "type": "plain_text",
                    "text": "Paste CSV content"
                },
                "element": {
                    "type": "plain_text_input",
                    "action_id": "csv_text",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Paste your CSV data here..."
                    }
                }
            },
            {
                "type": "input",
                "block_id": "column_selector_block",
                "label": {
                    "type": "plain_text",
                    "text": "Email Column"
                },
                "element": {
                    "type": "static_select",
                    "action_id": "column_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select column"
                    },
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Column F"},
                        "value": "5"
                    },
                    "options": [
                        {"text": {"type": "plain_text", "text": "Column A"}, "value": "0"},
                        {"text": {"type": "plain_text", "text": "Column B"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "Column C"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "Column D"}, "value": "3"},
                        {"text": {"type": "plain_text", "text": "Column E"}, "value": "4"},
                        {"text": {"type": "plain_text", "text": "Column F"}, "value": "5"},
                        {"text": {"type": "plain_text", "text": "Column G"}, "value": "6"},
                        {"text": {"type": "plain_text", "text": "Column H"}, "value": "7"},
                    ]
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 *Tip:* Column F is typically 'Personal Email' in leadership CSVs"
                    }
                ]
            }
        ]
    }
    
    modal_handler.show_modal(client, trigger_id, modal_view)


@app.view("csv_user_lookup_modal")
def handle_csv_user_lookup_submission(ack: Ack, body: dict, view: dict, client: WebClient):
    """
    Handle modal submission with CSV data.
    Extracts emails from specified column and looks up Slack user IDs.
    """
    ack()
    
    user_id = body["user"]["id"]
    
    csv_text = view["state"]["values"]["csv_input_block"]["csv_text"]["value"]
    column_index_str = view["state"]["values"]["column_selector_block"]["column_select"]["selected_option"]["value"]
    column_index = int(column_index_str)
    
    if not csv_text or not csv_text.strip():
        _post_error_message(client, user_id, "No CSV content provided")
        return
    
    try:
        csv_data = _parse_csv_text(csv_text)
        
        if not csv_data or len(csv_data) < 2:
            _post_error_message(client, user_id, "CSV must have at least a header row and one data row")
            return
        
        processor = CSVProcessor()
        emails = processor.extract_column_values(csv_data, column_index)
        
        if not emails:
            _post_error_message(client, user_id, f"No values found in column {chr(65 + column_index)}")
            return
        
        valid_emails = processor.filter_valid_emails(emails)
        
        if not valid_emails:
            _post_error_message(client, user_id, f"No valid email addresses found in column {chr(65 + column_index)}")
            return
        
        lookup_service = UserLookupService(SlackConfig.Bots.Leadership.token)
        results = lookup_service.lookup_user_ids_by_emails(valid_emails)
        
        _post_results_message(client, user_id, results)
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        _post_error_message(client, user_id, f"Error processing CSV: {str(e)}")


def _parse_csv_text(csv_text: str) -> List[List[str]]:
    """Parse CSV text into a list of lists."""
    reader = csv.reader(io.StringIO(csv_text))
    return list(reader)


def _post_results_message(client: WebClient, user_id: str, results: dict):
    """Post results message with found and not found users."""
    logger.info(f"Building results message for {len(results)} results")
    logger.info(f"Results data: {results}")
    
    found = {email: uid for email, uid in results.items() if uid}
    not_found = [email for email, uid in results.items() if not uid]
    
    logger.info(f"Found: {len(found)}, Not found: {len(not_found)}")
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ User ID Lookup Results"}
        }
    ]
    
    if found:
        # Split found users into chunks to avoid Slack's 3000 char block limit
        found_items = list(found.items())
        chunk_size = 20  # ~20 users per block = ~1400 chars (safe under 3000 limit)
        
        for i in range(0, len(found_items), chunk_size):
            chunk = found_items[i:i + chunk_size]
            chunk_text = "\n".join([f"`{email}` → `{uid}`" for email, uid in chunk])
            
            if i == 0:
                # First chunk shows total count
                header = f"*Found {len(found)} user(s):*\n{chunk_text}"
            else:
                # Subsequent chunks continue without header
                header = chunk_text
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header
                }
            })
    
    if not_found:
        # Split not found emails into chunks to avoid block limits
        chunk_size = 30  # ~30 emails per block
        
        for i in range(0, len(not_found), chunk_size):
            chunk = not_found[i:i + chunk_size]
            chunk_text = "\n".join([f"• `{email}`" for email in chunk])
            
            if i == 0:
                header = f"*❌ Not found ({len(not_found)}):*\n{chunk_text}"
            else:
                header = chunk_text
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header
                }
            })
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Total processed: {len(results)} email(s)"
            }
        ]
    })
    
    logger.info(f"Posting ephemeral message to user {user_id}")
    logger.info(f"Blocks structure: {blocks}")
    
    client.chat_postEphemeral(
        channel=user_id,
        user=user_id,
        blocks=blocks,
        text=f"Found {len(found)} users, {len(not_found)} not found"
    )


def _post_error_message(client: WebClient, user_id: str, error_message: str):
    """Post error message to user."""
    client.chat_postEphemeral(
        channel=user_id,
        user=user_id,
        text=f"❌ Error: {error_message}"
    )


def _categorize_positions_hierarchical(csv_data: List[List[str]], position_col: int, name_col: int, bars_email_col: int, personal_email_col: int, phone_col: int, birthday_col: int) -> Dict:
    """
    Categorize positions hierarchically with person data.
    
    Args:
        csv_data: Full CSV data including headers
        position_col: Index of the Position column
        name_col, bars_email_col, personal_email_col, phone_col, birthday_col: Column indices for person data
    
    Returns:
        Hierarchical dictionary structure with sections, teams, roles, and person data
    """
    # Define position patterns for fuzzy matching using helper functions
    # Pattern builders are defined at the bottom of this file
    position_patterns = {
        "executive_board": _build_executive_board_patterns(),
        "cross_sport": _build_cross_sport_patterns(),
        "bowling": _build_bowling_patterns(),
        "dodgeball": _build_dodgeball_patterns(),
        "kickball": _build_kickball_patterns(),
        "pickleball": _build_pickleball_patterns()
    }
    
    # Initialize result structure using helper functions
    # Dodgeball teams
    dodgeball_structure = _make_team_structure(
        "smallball_advanced", "smallball_social", 
        "wtnb_draft", "wtnb_social", 
        "foamball", "bigball",
        multi_value_roles={
            "player_experience": {"wtnb": False, "open": False}
        }
    )
    dodgeball_structure["player_experience"] = {"wtnb": None, "open": None}
    
    # Kickball teams
    kickball_structure = _make_team_structure(
        "sunday", "monday", "tuesday", 
        "draft_open", "draft_wtnb", 
        "saturday_open", "saturday_wtnb",
        multi_value_roles={
            "player_experience": {"wtnb": False, "open": True}  # open can have multiple people
        }
    )
    kickball_structure["player_experience"] = {"wtnb": None, "open": []}
    
    # Bowling teams
    bowling_structure = _make_team_structure(
        "sunday", "monday_open", "monday_wtnb",
        multi_value_roles={
            "player_experience": {"wtnb": False, "open": False}
        }
    )
    bowling_structure["player_experience"] = {"wtnb": None, "open": None}
    
    # Pickleball teams
    pickleball_structure = _make_team_structure(
        "advanced", "social", "wtnb", "ladder",
        multi_value_roles={
            "player_experience": {"wtnb": False, "open": False}
        }
    )
    pickleball_structure["player_experience"] = {"wtnb": None, "open": None}
    
    # Executive Board (single roles)
    executive_board_structure = {
        "commissioner": {"role": None},
        "vice_commissioner": {"role": None},
        "wtnb_commissioner": {"role": None},
        "secretary": {"role": None},
        "treasurer": {"role": None},
        "operations_commissioner": {"role": None},
        "dei_commissioner": {"role": None},
        "bowling_commissioner": {"role": None},
        "dodgeball_commissioner": {"role": None},
        "kickball_commissioner": {"role": None},
        "pickleball_commissioner": {"role": None}
    }
    
    # Cross-sport (single roles, not director/ops_manager)
    cross_sport_structure = {
        "communications": {"role": None},
        "events": {"open": None, "wtnb": None},
        "dei": {"open": None, "wtnb": None},
        "marketing": {"role": None},
        "philanthropy": {"role": None},
        "social_media": {"open": None, "wtnb": None},
        "technology": {"role": None},
        "permits_equipment": {"role": None}
    }
    
    result = {
        "executive_board": executive_board_structure,
        "cross_sport": cross_sport_structure,
        "bowling": bowling_structure,
        "dodgeball": dodgeball_structure,
        "kickball": kickball_structure,
        "pickleball": pickleball_structure,
        "committee_members": []  # Simple list of committee members
    }
    
    current_section = None
    
    for row_idx, row in enumerate(csv_data, start=1):
        if not row or len(row) == 0:
            continue
        
        # Get column A value (case-insensitive, stripped)
        col_a = row[0].strip().lower() if len(row) > 0 else ""
        
        # Check for section headers
        if "board of directors" in col_a:
            current_section = "executive_board"
            continue
        elif "cross" in col_a and "sport" in col_a and "leadership" in col_a:
            current_section = "cross_sport"
            continue
        elif "bowling" in col_a and "leadership" in col_a:
            current_section = "bowling"
            continue
        elif "dodgeball" in col_a and "leadership" in col_a:
            current_section = "dodgeball"
            continue
        elif "kickball" in col_a and "leadership" in col_a:
            current_section = "kickball"
            continue
        elif "pickleball" in col_a and "leadership" in col_a:
            current_section = "pickleball"
            continue
        elif "committee members" in col_a:
            # Committee members section (no pattern matching, just collect)
            current_section = "committee_members"
            continue
        
        # Process positions in current section
        if current_section and position_col < len(row):
            position = _clean_unicode_control_chars(row[position_col].strip())
            if not position:
                continue
            
            # Skip header row values (case-insensitive check)
            if position.lower() == "position":
                continue
            
            person_data = _extract_person_data(row, position, name_col, bars_email_col, personal_email_col, phone_col, birthday_col, row_idx)
            
            # For hierarchical sections (dodgeball, kickball), use fuzzy matching
            if current_section in position_patterns:
                matched = False
                
                # Build a list of all patterns with their keys and specificity
                # Specificity = number of required terms (more specific patterns should match first)
                # Exact matches get highest priority (specificity = 999)
                pattern_candidates = []
                for team_key, team_roles in position_patterns[current_section].items():
                    for role_key, pattern_options in team_roles.items():
                        if isinstance(pattern_options, dict) and "exact" in pattern_options:
                            # Exact match pattern - highest priority
                            pattern_candidates.append({
                                "team_key": team_key,
                                "role_key": role_key,
                                "pattern_options": pattern_options,
                                "specificity": 999,
                                "is_exact": True
                            })
                        elif isinstance(pattern_options, list) and len(pattern_options) > 0:
                            if isinstance(pattern_options[0], list):
                                # OR logic: calculate specificity as max terms in any group
                                specificity = max(len(terms) for terms in pattern_options)
                            else:
                                # Single list: specificity is number of terms
                                specificity = len(pattern_options)
                            
                            pattern_candidates.append({
                                "team_key": team_key,
                                "role_key": role_key,
                                "pattern_options": pattern_options,
                                "specificity": specificity,
                                "is_exact": False
                            })
                
                # Detect position characteristics for priority matching
                position_lower = position.lower()
                is_wtnb_position = "wtnb" in position_lower
                is_player_experience_position = "player experience" in position_lower
                
                # Calculate priority for each pattern and store it
                # Priority rules:
                # - Exact matches: 1000+
                # - WTNB patterns for WTNB positions: 500-999
                # - Non-WTNB patterns for WTNB positions: 0 (skip)
                # - Any pattern for non-WTNB positions: 1-499
                for candidate in pattern_candidates:
                    specificity = candidate["specificity"]
                    is_exact = candidate.get("is_exact", False)
                    
                    # Check if this is a WTNB pattern
                    pattern_options = candidate["pattern_options"]
                    is_wtnb_pattern = False
                    if isinstance(pattern_options, list) and len(pattern_options) > 0:
                        if isinstance(pattern_options[0], list):
                            # OR logic: check if any option contains "wtnb"
                            is_wtnb_pattern = any("wtnb" in str(terms).lower() for terms in pattern_options)
                        else:
                            # Single list
                            is_wtnb_pattern = "wtnb" in str(pattern_options).lower()
                    
                    # Calculate priority
                    if is_exact:
                        priority = 1000 + specificity
                    elif is_wtnb_position and is_wtnb_pattern:
                        priority = 500 + specificity
                    elif is_wtnb_position and not is_wtnb_pattern:
                        priority = 0  # Skip non-WTNB patterns for WTNB positions
                    else:
                        priority = specificity
                    
                    candidate["priority"] = priority
                
                # Sort by priority (descending) - highest priority first
                pattern_candidates.sort(key=lambda x: x["priority"], reverse=True)
                
                # Try to match against sorted patterns
                for candidate in pattern_candidates:
                    if matched:
                        break
                    
                    # Skip deprioritized patterns (priority = 0)
                    if candidate.get("priority", 0) == 0:
                        continue
                    
                    team_key = candidate["team_key"]
                    role_key = candidate["role_key"]
                    pattern_options = candidate["pattern_options"]
                    is_exact = candidate.get("is_exact", False)
                    
                    # Skip non-player_experience patterns if position contains "player experience"
                    if is_player_experience_position and team_key != "player_experience":
                        continue
                    
                    if is_exact:
                        # Exact match: position must be exactly this string (case-insensitive, whitespace-stripped)
                        exact_value = pattern_options["exact"]
                        if position.lower().strip() == exact_value.lower().strip():
                            result[current_section][team_key][role_key] = person_data
                            matched = True
                    elif isinstance(pattern_options, list) and len(pattern_options) > 0:
                        if isinstance(pattern_options[0], list):
                            # New format: multiple pattern options (OR logic)
                            for required_terms in pattern_options:
                                if _fuzzy_match_position(position, required_terms):
                                    # Special handling for kickball.player_experience.open (can have multiple)
                                    if current_section == "kickball" and team_key == "player_experience" and role_key == "open":
                                        result[current_section][team_key][role_key].append(person_data)
                                    else:
                                        result[current_section][team_key][role_key] = person_data
                                    matched = True
                                    break
                        else:
                            # Old format: single list of required terms
                            if _fuzzy_match_position(position, pattern_options):
                                result[current_section][team_key][role_key] = person_data
                                matched = True
            else:
                # For committee_members section, add snake_case position key
                if current_section == "committee_members":
                    result[current_section].append({
                        "position": position,
                        "position_key": _to_snake_case(position),
                        **person_data
                    })
                else:
                    # For other list sections (if any), just collect positions
                    result[current_section].append({"position": position, **person_data})
    
    return result


def _enrich_hierarchy_with_slack_ids(hierarchy: Dict, results: Dict) -> None:
    """
    Add slack_user_id field to each person in the hierarchy based on lookup results.
    
    Args:
        hierarchy: The leadership hierarchy dict (modified in-place)
        results: Dict of email -> slack_user_id from lookup service
    """
    for section_key, section_data in hierarchy.items():
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
        
        for team_key, team_data in section_data.items():
            if not isinstance(team_data, dict):
                continue
            
            for role_key, person_data in team_data.items():
                if isinstance(person_data, list):
                    # Multiple people in same role
                    for person in person_data:
                        if person and isinstance(person, dict):
                            bars_email = person.get("bars_email", "").strip()
                            if bars_email:
                                person["slack_user_id"] = results.get(bars_email)
                else:
                    # Single person
                    if person_data and isinstance(person_data, dict):
                        bars_email = person_data.get("bars_email", "").strip()
                        if bars_email:
                            person_data["slack_user_id"] = results.get(bars_email)


def _column_index_to_letter(col_idx: int) -> str:
    """Convert 0-based column index to Excel-style letter (0 -> A, 25 -> Z, 26 -> AA)."""
    result = ""
    col_idx += 1  # Convert to 1-based for Excel-style
    while col_idx > 0:
        col_idx -= 1
        result = chr(col_idx % 26 + ord('A')) + result
        col_idx //= 26
    return result


def _analyze_hierarchy_completeness(hierarchy: Dict, results: Dict) -> Dict:
    """
    Analyze the hierarchy to determine success/warning/failure status for each position.
    
    Args:
        hierarchy: The leadership hierarchy dict with person data
        results: Dict of email -> slack_user_id (or None) from lookup service
    
    Returns:
        Dictionary with:
        - successes: List of positions where all fields were found
        - warnings: List of positions with some missing fields (but has email + slack_id)
        - failures: List of positions missing critical fields (no email or no slack_id)
        - vacant_positions: List of positions marked as vacant
    """
    successes = []
    warnings = []
    failures = []
    vacant_positions = []
    
    def check_position(person_data: Dict, path: str, is_committee_member: bool = False):
        """Check a single position's completeness."""
        if not person_data or not isinstance(person_data, dict):
            return
        
        position_name = person_data.get("position", "Unknown")
        name = person_data.get("name", "").strip()
        
        # Check if position is vacant - if so, skip all other field checks
        if name.lower() == "vacant":
            vacant_positions.append({
                "path": path,
                "position": position_name
            })
            return
        
        bars_email = person_data.get("bars_email", "").strip()
        personal_email = person_data.get("personal_email", "").strip()
        phone = person_data.get("phone", "").strip()
        birthday = person_data.get("birthday", "").strip()
        
        # Extract CSV row and column info for detailed error reporting
        csv_row = person_data.get("_csv_row")
        csv_columns = person_data.get("_csv_columns", {})
        
        # Get Slack user ID from results
        slack_user_id = results.get(bars_email) if bars_email else None
        
        # Determine fields present and missing based on section type
        fields_present = []
        fields_missing = []
        fields_missing_details = []  # Will contain dicts with field name and CSV cell reference
        
        # Helper to add missing field with CSV cell reference
        def add_missing_field(field_name: str, value: str, col_key: str):
            fields_missing.append(field_name)
            if csv_row and col_key in csv_columns:
                col_letter = _column_index_to_letter(csv_columns[col_key])
                cell_ref = f"{col_letter}{csv_row}"
                fields_missing_details.append({
                    "field": field_name,
                    "cell": cell_ref,
                    "value": value or "(empty)"
                })
        
        # Always check name and bars_email
        if name:
            fields_present.append("name")
        else:
            add_missing_field("name", "", "name")
        
        if bars_email:
            fields_present.append("bars_email")
        else:
            add_missing_field("bars_email", "", "bars_email")
        
        # For committee members, slack_user_id, personal_email, and phone are optional
        # For everyone else, slack_user_id is required
        if not is_committee_member:
            if slack_user_id:
                fields_present.append("slack_user_id")
            else:
                # Special case: slack_user_id missing due to lookup failure
                add_missing_field("slack_user_id", f"(lookup failed for {bars_email})", "bars_email")
            
            if personal_email:
                fields_present.append("personal_email")
            else:
                add_missing_field("personal_email", "", "personal_email")
            
            if phone:
                fields_present.append("phone")
            else:
                add_missing_field("phone", "", "phone")
        else:
            # Committee members: track these but don't require them
            if slack_user_id:
                fields_present.append("slack_user_id")
            if personal_email:
                fields_present.append("personal_email")
            if phone:
                fields_present.append("phone")
        
        # Birthday is always optional for everyone
        if birthday:
            fields_present.append("birthday")
        else:
            add_missing_field("birthday", "", "birthday")
        
        # Categorize based on section type
        if is_committee_member:
            # Committee members: only require name and bars_email
            if not name or not bars_email:
                failures.append({
                    "path": path,
                    "position": position_name,
                    "name": name,
                    "fields_present": fields_present,
                    "fields_missing": fields_missing,
                    "fields_missing_details": fields_missing_details
                })
            elif len(fields_missing) == 0:
                successes.append({
                    "path": path,
                    "position": position_name
                })
            else:
                # Missing some optional fields
                warnings.append({
                    "path": path,
                    "position": position_name,
                    "name": name,
                    "fields_present": fields_present,
                    "fields_missing": fields_missing,
                    "fields_missing_details": fields_missing_details
                })
        else:
            # Leadership positions: require name, bars_email, and slack_user_id
            if not bars_email or not slack_user_id:
                failures.append({
                    "path": path,
                    "position": position_name,
                    "name": name,
                    "fields_present": fields_present,
                    "fields_missing": fields_missing,
                    "fields_missing_details": fields_missing_details
                })
            elif len(fields_missing) == 0:
                successes.append({
                    "path": path,
                    "position": position_name
                })
            else:
                warnings.append({
                    "path": path,
                    "position": position_name,
                    "name": name,
                    "fields_present": fields_present,
                    "fields_missing": fields_missing,
                    "fields_missing_details": fields_missing_details
                })
    
    # Walk through hierarchy
    for section_key, section_data in hierarchy.items():
        # Handle simple list sections (like committee_members)
        if isinstance(section_data, list):
            is_committee = (section_key == "committee_members")
            for idx, person in enumerate(section_data):
                check_position(person, f"{section_key}[{idx}]", is_committee_member=is_committee)
            continue
        
        if not isinstance(section_data, dict):
            continue
        
        for team_key, team_data in section_data.items():
            if not isinstance(team_data, dict):
                continue
            
            for role_key, person_data in team_data.items():
                path = f"{section_key}.{team_key}.{role_key}"
                
                if isinstance(person_data, list):
                    # Multiple people in same role
                    for idx, person in enumerate(person_data):
                        check_position(person, f"{path}[{idx}]", is_committee_member=False)
                else:
                    # Single person
                    check_position(person_data, path, is_committee_member=False)
    
    return {
        "successes": successes,
        "warnings": warnings,
        "failures": failures,
        "vacant_positions": vacant_positions
    }


def _build_results_blocks_from_hierarchy(hierarchy: Dict, found: Dict, not_found: List, missing_email_positions: List, email_to_position: Dict, email_to_section: Dict, results: Dict) -> List:
    """
    Build Slack blocks showing success/warning/failure summary instead of full listing.
    
    Args:
        hierarchy: The leadership hierarchy dict
        found: Dict of email -> user_id for found users
        not_found: List of emails that weren't found
        missing_email_positions: List of positions without emails
        email_to_position: Mapping of email -> position title
        email_to_section: Mapping of email -> section path
        results: Full results dict from lookup service
    
    Returns:
        List of Slack blocks for display
    """
    # Analyze completeness
    analysis = _analyze_hierarchy_completeness(hierarchy, results)
    
    successes = analysis["successes"]
    warnings = analysis["warnings"]
    failures = analysis["failures"]
    vacant_positions = analysis["vacant_positions"]
    
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "✅ Leadership Directory Processing Results"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary:*\n"
                        f"✅ *{len(successes)}* complete (all fields found)\n"
                        f"⚠️ *{len(warnings)}* partial (missing some fields)\n"
                        f"❌ *{len(failures)}* failed (missing email or Slack user ID)\n"
                        f"🔲 *{len(vacant_positions)}* vacant positions"
            }
        }
    ]
    
    # Show warnings (positions with some missing fields)
    if warnings:
        warning_text = "*⚠️ Partial Matches (missing some fields):*\n"
        for item in warnings[:15]:  # Limit to first 15
            name = item.get("name", "Unknown")
            position = item["position"]
            
            # Build detailed missing fields with CSV cell references
            if item.get("fields_missing_details"):
                detail_lines = []
                for detail in item["fields_missing_details"]:
                    field_name = detail["field"]
                    cell_ref = detail["cell"]
                    value = detail.get("value", "(empty)")
                    detail_lines.append(f"`{field_name}` (cell {cell_ref}: {value})")
                missing_str = "\n    - " + "\n    - ".join(detail_lines)
            else:
                missing_str = ", ".join(item["fields_missing"])
            
            warning_text += f"• *{name}* - `{position}`{missing_str}\n"
        
        if len(warnings) > 15:
            warning_text += f"\n_...and {len(warnings) - 15} more_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": warning_text
            }
        })
    
    # Show failures (positions missing critical fields)
    if failures:
        failure_text = "*❌ Failed Matches (missing email or Slack user ID):*\n"
        for item in failures[:15]:  # Limit to first 15
            name = item.get("name", "Unknown")
            position = item["position"]
            
            # Build detailed missing fields with CSV cell references
            if item.get("fields_missing_details"):
                detail_lines = []
                for detail in item["fields_missing_details"]:
                    field_name = detail["field"]
                    cell_ref = detail["cell"]
                    value = detail.get("value", "(empty)")
                    detail_lines.append(f"`{field_name}` (cell {cell_ref}: {value})")
                missing_str = "\n    - " + "\n    - ".join(detail_lines)
            else:
                missing_str = ", ".join(item["fields_missing"])
            
            failure_text += f"• *{name}* - `{position}`{missing_str}\n"
        
        if len(failures) > 15:
            failure_text += f"\n_...and {len(failures) - 15} more_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": failure_text
            }
        })
    
    # Show vacant positions
    if vacant_positions:
        vacant_text = "*🔲 Vacant Positions:*\n"
        for item in vacant_positions[:15]:  # Limit to first 15
            vacant_text += f"• `{item['position']}`\n"
        
        if len(vacant_positions) > 15:
            vacant_text += f"\n_...and {len(vacant_positions) - 15} more_"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": vacant_text
            }
        })
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"📊 Full hierarchy saved to result.json with {len(results)} total positions processed."
            }
        ]
    })
    
    return blocks


def _show_message_loading_status(response_url: str, loading_message: str = "Loading..."):
    """
    Update an ephemeral message to show a loading status.
    
    Args:
        response_url: The response URL from the Slack action
        loading_message: Custom loading message to display
    """
    try:
        response = requests.post(
            response_url,
            json={
                "text": loading_message,
                "replace_original": True,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⏳ *{loading_message}*"
                        }
                    }
                ]
            }
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error showing message loading status: {e}")


def _update_ephemeral_message(response_url: str, text: str, blocks: list, show_loading: bool = False, loading_message: str = "Loading..."):
    """
    Update an ephemeral message using response_url from a button action.
    Optionally shows a loading state first.
    
    Args:
        response_url: The response URL from the Slack action
        text: Plain text version of the message
        blocks: Slack Block Kit blocks for the message
        show_loading: Whether to show a loading state first
        loading_message: Custom loading message if show_loading is True
    """
    try:
        if show_loading:
            _show_message_loading_status(response_url, loading_message)
        
        response = requests.post(
            response_url,
            json={
                "text": text,
                "replace_original": True,
                "blocks": blocks
            }
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error updating ephemeral message: {e}")


# ============================================================================
# FILE UPLOAD HANDLERS
# ============================================================================

@app.event("file_shared")
def handle_file_shared(event: dict, client: WebClient, logger):
    """
    Handle file upload events in monitored channels.
    Detects CSV files with 'contact sheet' in filename.
    """
    file_id = event.get("file_id")
    user_id = event.get("user_id")
    channel_id = event.get("channel_id")
    
    if not file_id or not user_id or not channel_id:
        return
    
    # Only process files in #joe-test channel
    if channel_id != SlackConfig.Channels.JoeTest.id:
        return
    
    try:
        # Get file info
        file_info = client.files_info(file=file_id).get("file", {})
        filename = file_info.get("name", "").lower()
        mimetype = file_info.get("mimetype", "")
        
        logger.info(f"File uploaded: {filename} by {user_id} in {channel_id}")
        
        # Check if it's a CSV with "contact sheet" in name
        if "contact sheet" not in filename:
            return
        
        if not (filename.endswith(".csv") or "csv" in mimetype):
            logger.info(f"File is not CSV: {mimetype}")
            return
        
        # Download and parse CSV
        file_url = file_info.get("url_private")
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = _download_and_parse_csv(file_url, client)
        
        if not csv_data:
            _post_error_message(client, user_id, "Could not parse CSV file")
            return
        
        # Auto-detect columns
        position_col, email_col, header_row_index = _auto_detect_columns(csv_data)
        
        if position_col is None or email_col is None:
            _post_error_message(
                client, 
                user_id, 
                "Could not find 'Position' and 'BARS Email' columns in CSV"
            )
            return
        
        # Get header row for display
        header_row = csv_data[header_row_index] if header_row_index < len(csv_data) else []
        
        # Post ephemeral message asking if they want to process
        _post_file_upload_prompt(
            client, 
            channel_id, 
            user_id, 
            file_id,
            filename,
            position_col,
            email_col,
            header_row_index,
            len(csv_data),
            header_row
        )
        
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")


def _download_and_parse_csv(url: str, client: WebClient) -> Optional[List[List[str]]]:
    """Download CSV from Slack and parse it."""
    try:
        # Download file using bot token
        headers = {"Authorization": f"Bearer {SlackConfig.Bots.Leadership.token}"}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to download file: {response.status_code}")
            return None
        
        # Parse CSV
        csv_text = response.text
        reader = csv.reader(io.StringIO(csv_text))
        return list(reader)
        
    except Exception as e:
        logger.error(f"Error downloading/parsing CSV: {e}")
        return None


def _auto_detect_columns(csv_data: List[List[str]]) -> Tuple[Optional[int], Optional[int], int]:
    """
    Auto-detect Position and BARS Email columns.
    Returns (position_col_index, email_col_index, header_row_index).
    Prioritizes "BARS EMAIL" over generic "EMAIL".
    """
    for row_idx, row in enumerate(csv_data):
        position_col = None
        email_col = None
        bars_email_col = None
        
        for col_idx, cell in enumerate(row):
            cell_lower = cell.strip().lower()
            
            if "position" in cell_lower:
                position_col = col_idx
            
            # Prioritize "BARS EMAIL" over generic "EMAIL"
            if "bars email" in cell_lower:
                bars_email_col = col_idx
            elif "email" in cell_lower and email_col is None:
                email_col = col_idx
        
        # Prefer BARS EMAIL, fall back to any email column
        final_email_col = bars_email_col if bars_email_col is not None else email_col
        
        # If we found both columns in the same row, that's our header
        if position_col is not None and final_email_col is not None:
            return position_col, final_email_col, row_idx
    
    return None, None, -1


def _post_file_upload_prompt(
    client: WebClient,
    channel_id: str,
    user_id: str,
    file_id: str,
    filename: str,
    position_col: int,
    email_col: int,
    header_row_index: int,
    total_rows: int,
    header_row: List[str]
):
    """Post ephemeral message asking if user wants to process the CSV."""
    
    position_letter = chr(65 + position_col)  # 0=A, 1=B, etc.
    email_letter = chr(65 + email_col)
    
    # Get actual header text
    position_header = header_row[position_col].strip() if position_col < len(header_row) else "Position"
    email_header = header_row[email_col].strip() if email_col < len(header_row) else "BARS Email"
    
    # Build column list showing all headers in order
    column_list = []
    for idx, header in enumerate(header_row):
        if not header.strip():
            continue
        col_letter = chr(65 + idx)
        # Mark the detected columns
        if idx == position_col:
            column_list.append(f"• *`{header.strip()}`* (Column {col_letter}) ← Position")
        elif idx == email_col:
            column_list.append(f"• *`{header.strip()}`* (Column {col_letter}) ← BARS Email")
        else:
            column_list.append(f"• `{header.strip()}` (Column {col_letter})")
    
    columns_text = "\n".join(column_list) if column_list else "No columns detected"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Contact Sheet Detected"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*File:* `{filename}`\n*Rows:* {total_rows}\n*Header Row:* {header_row_index + 1}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Detected columns (in order):*\n{columns_text}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Would you like to get Slack user IDs for these emails?"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Yes, Get User IDs"
                    },
                    "style": "primary",
                    "action_id": "confirm_file_process",
                    "value": f"{file_id}|{position_col}|{email_col}|{header_row_index}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "✏️ Edit Columns"
                    },
                    "action_id": "edit_file_columns",
                    "value": f"{file_id}|{header_row_index}"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Cancel"
                    },
                    "action_id": "cancel_file_process"
                }
            ]
        }
    ]
    
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        blocks=blocks,
        text=f"Contact sheet detected: {filename}"
    )


@app.action("confirm_file_process")
def handle_confirm_file_process(ack: Ack, body: dict, client: WebClient, action: dict):
    """Handle user confirming they want to process the uploaded CSV."""
    ack()
    
    try:
        logger.info(f"🔵 CONFIRM FILE PROCESS - Action triggered")
        logger.info(f"Body keys: {body.keys()}")
        logger.info(f"Action value: {action.get('value')}")
        
        user_id = body["user"]["id"]
        value = action["value"]  # Format: file_id|position_col|email_col|header_row
        
        logger.info(f"Parsing value: {value}")
        file_id, position_col_str, email_col_str, header_row_str = value.split("|")
        position_col = int(position_col_str)
        email_col = int(email_col_str)
        header_row = int(header_row_str)
        logger.info(f"Parsed: file_id={file_id}, position_col={position_col}, email_col={email_col}, header_row={header_row}")
    except Exception as e:
        logger.error(f"🔴 FATAL ERROR in confirm_file_process (before main logic): {e}", exc_info=True)
        return
    
    # Get response_url to update ephemeral message
    response_url = body.get("response_url")
    channel_id = body.get("channel", {}).get("id")
    
    logger.info(f"Response URL: {response_url[:50] if response_url else 'None'}...")
    
    # Update the original message to show processing
    if response_url:
        logger.info(f"Updating ephemeral message to show processing...")
        _update_ephemeral_message(
            response_url,
            "Processing...",
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Processing...* Looking up Slack user IDs"
                    }
                }
            ]
        )
    else:
        logger.warning(f"Missing response_url, cannot update message")
    
    try:
        logger.info(f"Starting file processing for file_id={file_id}")
        # Get file info and download CSV
        file_info = client.files_info(file=file_id).get("file", {})
        file_url = file_info.get("url_private")
        logger.info(f"Got file URL: {file_url[:50] if file_url else 'None'}...")
        
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = _download_and_parse_csv(file_url, client)
        
        if not csv_data:
            _post_error_message(client, user_id, "Could not download CSV file")
            return
        
        # ═══════════════════════════════════════════════════════════════════════
        # BUILD LEADERSHIP HIERARCHY AND MAPPINGS
        # ═══════════════════════════════════════════════════════════════════════
        # This happens completely independently of Slack API calls
        mappings = _build_leadership_hierarchy_and_mappings(
            csv_data, header_row, position_col, email_col
        )
        
        hierarchy = mappings["hierarchy"]
        position_to_section = mappings["position_to_section"]
        email_to_position = mappings["email_to_position"]
        email_to_section = mappings["email_to_section"]
        valid_emails = mappings["emails"]
        missing_email_positions = mappings["missing_email_positions"]
        
        if not valid_emails:
            # Update message with error
            if response_url:
                _update_ephemeral_message(
                    response_url,
                    "Error",
                    [{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Error* - No emails found in column {chr(65 + email_col)}"
                        }
                    }]
                )
            return
        
        # ═══════════════════════════════════════════════════════════════════════
        # LOOKUP SLACK USER IDs
        # ═══════════════════════════════════════════════════════════════════════
        # Now that we have the hierarchy and mappings, look up Slack user IDs
        lookup_service = UserLookupService(SlackConfig.Bots.Leadership.token)
        results = lookup_service.lookup_user_ids_by_emails(valid_emails)
        
        # Enrich hierarchy with Slack user IDs
        _enrich_hierarchy_with_slack_ids(hierarchy, results)
        
        # Save enriched hierarchy to JSON file
        output_dir = Path(__file__).parent
        output_file = output_dir / "result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(hierarchy, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved enriched hierarchy to: {output_file}")
        
        # Build results blocks grouped by hierarchical structure
        found = {email: uid for email, uid in results.items() if uid}
        not_found = [email for email, uid in results.items() if not uid]
        
        blocks = _build_results_blocks_from_hierarchy(
            hierarchy, found, not_found, missing_email_positions,
            email_to_position, email_to_section, results
        )
        
        # Update the original message with full results
        if response_url:
            _update_ephemeral_message(
                response_url,
                f"Processing complete",
                blocks
            )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        
        # Update message to show error
        if response_url:
            _update_ephemeral_message(
                response_url,
                "Error",
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Error* - {str(e)}"
                        }
                    }
                ]
            )


@app.action("cancel_file_process")
def handle_cancel_file_process(ack: Ack, body: dict, client: WebClient):
    """Handle user canceling file processing."""
    ack()
    
    try:
        # Get response_url to update ephemeral message
        response_url = body.get("response_url")
        
        if response_url:
            # Update the message to show it was canceled
            _update_ephemeral_message(
                response_url,
                "❌ Canceled",
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ *Canceled* - CSV processing was canceled by user"
                        }
                    }
                ]
            )
    except Exception as e:
        logger.error(f"Error updating cancel message: {e}")


@app.action("edit_file_columns")
def handle_edit_file_columns(ack: Ack, body: dict, client: WebClient, action: dict):
    """Open modal to manually select columns."""
    ack()
    
    user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]
    value = action["value"]  # Format: file_id|header_row_index
    
    file_id, header_row_str = value.split("|")
    header_row_index = int(header_row_str)
    
    response_url = body.get("response_url")
    
    # Show loading modal immediately and get its view_id
    view_id = modal_handler.show_loading_modal(client, trigger_id, "Loading column data...")
    
    if not view_id:
        logger.error("Failed to open loading modal - no view_id returned")
        _post_error_message(client, user_id, "Failed to open loading modal")
        return
    
    try:
        # Get file and download CSV
        file_info = client.files_info(file=file_id).get("file", {})
        file_url = file_info.get("url_private")
        
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = _download_and_parse_csv(file_url, client)
        
        if not csv_data or header_row_index >= len(csv_data):
            _post_error_message(client, user_id, "Could not parse CSV file")
            return
        
        header_row = csv_data[header_row_index]
        
        # Build column options from header row
        column_options = []
        for idx, header in enumerate(header_row):
            if header.strip():
                col_letter = chr(65 + idx)
                column_options.append({
                    "text": {
                        "type": "plain_text",
                        "text": f"{header.strip()} (Column {col_letter})"
                    },
                    "value": str(idx)
                })
        
        if not column_options:
            _post_error_message(client, user_id, "No columns found in CSV")
            return
        
        # Find position column default
        position_default_idx = None
        for idx, header in enumerate(header_row):
            header_lower = header.strip().lower()
            if "position" in header_lower:
                position_default_idx = idx
                break
        
        # Find email column default (prefer BARS EMAIL)
        email_default_idx = None
        for idx, header in enumerate(header_row):
            header_lower = header.strip().lower()
            if "bars email" in header_lower:
                email_default_idx = idx
                break
            elif "email" in header_lower and email_default_idx is None:
                email_default_idx = idx
        
        # Get message context for persistence
        channel_id = body.get("channel", {}).get("id", "")
        container = body.get("container", {})
        message_ts = container.get("message_ts", "")
        
        # Build modal for column selection
        modal_view = {
            "type": "modal",
            "callback_id": "column_selection_modal",
            "title": {"type": "plain_text", "text": "Select Columns"},
            "submit": {"type": "plain_text", "text": "Get User IDs"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "private_metadata": f"{file_id}|{header_row_index}|{channel_id}|{message_ts}|{response_url}",
            "blocks": [
                {
                    "type": "input",
                    "block_id": "position_column_block",
                    "label": {
                        "type": "plain_text",
                        "text": "Position Column"
                    },
                    "element": {
                        "type": "static_select",
                        "action_id": "position_column_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select position column"
                        },
                        "options": column_options,
                        **({"initial_option": column_options[position_default_idx]} if position_default_idx is not None and position_default_idx < len(column_options) else {})
                    }
                },
                {
                    "type": "input",
                    "block_id": "email_column_block",
                    "label": {
                        "type": "plain_text",
                        "text": "Email Column"
                    },
                    "element": {
                        "type": "static_select",
                        "action_id": "email_column_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select email column"
                        },
                        "options": column_options,
                        **({"initial_option": column_options[email_default_idx]} if email_default_idx is not None and email_default_idx < len(column_options) else {})
                    }
                }
            ]
        }
        
        # Update the loading modal to show column selection
        logger.info(f"Updating modal {view_id} with column selection")
        modal_handler.update_modal(client, view_id, modal_view)
        
    except Exception as e:
        logger.error(f"Error loading column selection: {e}")
        
        # Update the loading modal to show error
        error_modal = {
            "type": "modal",
            "callback_id": "error_modal",
            "title": {"type": "plain_text", "text": "Error"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Error loading columns*\n\n{str(e)}"
                    }
                }
            ]
        }
        modal_handler.update_modal(client, view_id, error_modal)


@app.view("column_selection_modal")
def handle_column_selection_modal(ack: Ack, body: dict, view: dict, client: WebClient):
    """Handle modal submission with manually selected columns."""
    ack()
    
    user_id = body["user"]["id"]
    
    # Parse private metadata (includes message context and response_url)
    metadata = view["private_metadata"]
    parts = metadata.split("|")
    file_id = parts[0]
    header_row_index = int(parts[1])
    channel_id = parts[2] if len(parts) > 2 else None
    message_ts = parts[3] if len(parts) > 3 else None
    response_url = parts[4] if len(parts) > 4 else None
    
    # Get selected columns
    position_col_str = view["state"]["values"]["position_column_block"]["position_column_select"]["selected_option"]["value"]
    position_col = int(position_col_str)
    
    email_col_str = view["state"]["values"]["email_column_block"]["email_column_select"]["selected_option"]["value"]
    email_col = int(email_col_str)
    
    # Update the original ephemeral message to show processing
    if response_url:
        _update_ephemeral_message(
            response_url,
            "Processing...",
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⏳ *Processing...* Looking up Slack user IDs"
                    }
                }
            ]
        )
    
    try:
        # Get file and download CSV
        file_info = client.files_info(file=file_id).get("file", {})
        file_url = file_info.get("url_private")
        
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = _download_and_parse_csv(file_url, client)
        
        if not csv_data:
            _post_error_message(client, user_id, "Could not download CSV file")
            return
        
        # ═══════════════════════════════════════════════════════════════════════
        # BUILD LEADERSHIP HIERARCHY AND MAPPINGS
        # ═══════════════════════════════════════════════════════════════════════
        # This happens completely independently of Slack API calls
        mappings = _build_leadership_hierarchy_and_mappings(
            csv_data, header_row_index, position_col, email_col
        )
        
        hierarchy = mappings["hierarchy"]
        position_to_section = mappings["position_to_section"]
        email_to_position = mappings["email_to_position"]
        email_to_section = mappings["email_to_section"]
        valid_emails = mappings["emails"]
        missing_email_positions = mappings["missing_email_positions"]
        
        if not valid_emails:
            if response_url:
                _update_ephemeral_message(
                    response_url,
                    "Error",
                    [{
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Error* - No emails found in column {chr(65 + email_col)}"
                        }
                    }]
                )
            return
        
        # ═══════════════════════════════════════════════════════════════════════
        # LOOKUP SLACK USER IDs
        # ═══════════════════════════════════════════════════════════════════════
        # Now that we have the hierarchy and mappings, look up Slack user IDs
        lookup_service = UserLookupService(SlackConfig.Bots.Leadership.token)
        results = lookup_service.lookup_user_ids_by_emails(valid_emails)
        
        # Enrich hierarchy with Slack user IDs
        _enrich_hierarchy_with_slack_ids(hierarchy, results)
        
        # Save enriched hierarchy to JSON file
        output_dir = Path(__file__).parent
        output_file = output_dir / "result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(hierarchy, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved enriched hierarchy to: {output_file}")
        
        # Build results blocks grouped by hierarchical structure
        found = {email: uid for email, uid in results.items() if uid}
        not_found = [email for email, uid in results.items() if not uid]
        
        blocks = _build_results_blocks_from_hierarchy(
            hierarchy, found, not_found, missing_email_positions,
            email_to_position, email_to_section, results
        )
        
        # Update the original ephemeral message with results
        if response_url:
            _update_ephemeral_message(
                response_url,
                f"Processing complete",
                blocks
            )
        
    except Exception as e:
        logger.error(f"Error processing file with manual column selection: {e}")
        
        # Update the original ephemeral message with error
        if response_url:
            _update_ephemeral_message(
                response_url,
                "Error",
                [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ *Error* - {str(e)}"
                        }
                    }
                ]
            )


# ============================================================================
# POSITION CATEGORIZATION & MATCHING HELPERS
# ============================================================================


def _fuzzy_match_position(position: str, required_terms) -> bool:
    """
    Check if a position string matches required fuzzy terms.
    
    Supports:
    - List of strings: ALL must be found (AND logic)
    - List of lists: ANY inner list can match (OR logic for top level, AND for inner)
    
    Args:
        position: The position string to check
        required_terms: Either a list of strings or a list of lists
        
    Returns:
        True if the position matches the required terms
    """
    position_lower = position.lower().strip()
    
    # Check if this is OR logic (list of lists)
    if required_terms and isinstance(required_terms[0], list):
        # OR logic: at least one group must match
        for term_group in required_terms:
            if all(term.lower() in position_lower for term in term_group):
                return True
        return False
    else:
        # AND logic: all terms must be present
        return all(term.lower() in position_lower for term in required_terms)


# ============================================================================
# POSITION CATEGORIZATION & MATCHING HELPERS
# ============================================================================
# This section contains all logic for parsing CSV data, categorizing positions
# into hierarchical structures, and performing fuzzy matching on position titles.
#
# ORGANIZATION:
# 1. Pattern Builders - Create reusable director/ops_manager patterns for teams
# 2. Sport-Specific Pattern Builders - Define patterns for each sport (dodgeball, kickball, etc.)
# 3. Core Utilities - Fuzzy matching, data extraction, and hierarchy flattening
#
# ADDING A NEW SPORT:
# To add a new sport (e.g., bowling, pickleball):
# 1. Create a _build_{sport}_patterns() function using _make_director_ops_patterns()
# 2. Update _categorize_positions_hierarchical() to include the new sport in position_patterns
# 3. Add the sport structure using _make_team_structure() in the result initialization
# ============================================================================


# ──────────────────────────────────────────────────────────────────────────
# PATTERN BUILDERS
# ──────────────────────────────────────────────────────────────────────────


def _make_director_ops_patterns(*base_terms):
    """
    Generate director and operations manager patterns from base terms.
    
    Args:
        *base_terms: Terms that identify the team/league (e.g., "sunday", "small ball", "advanced")
    
    Returns:
        Dictionary with 'director' and 'ops_manager' keys containing term lists
    
    Example:
        _make_director_ops_patterns("sunday") → {
            "director": ["sunday", "director"],
            "ops_manager": ["sunday", "operations manager"]
        }
    """
    return {
        "director": list(base_terms) + ["director"],
        "ops_manager": list(base_terms) + ["operations manager"]
    }


def _make_team_structure(*team_keys, multi_value_roles=None):
    """
    Generate a team structure with director/ops_manager or custom roles.
    
    Args:
        *team_keys: Team names to create structure for
        multi_value_roles: Dict mapping team_key -> {role_key: is_multi} for custom roles
    
    Returns:
        Dictionary with team structures initialized
    
    Example:
        _make_team_structure("sunday", "monday") → {
            "sunday": {"director": None, "ops_manager": None},
            "monday": {"director": None, "ops_manager": None}
        }
    """
    multi_value_roles = multi_value_roles or {}
    structure = {}
    for key in team_keys:
        if key in multi_value_roles:
            # Custom structure for this team
            structure[key] = {}
            for role, is_multi in multi_value_roles[key].items():
                structure[key][role] = [] if is_multi else None
        else:
            # Standard director/ops_manager
            structure[key] = {"director": None, "ops_manager": None}
    return structure


def _make_player_experience_patterns(use_or_logic=False):
    """
    Generate player experience patterns (common across all sports).
    
    Args:
        use_or_logic: If True, wraps patterns in lists for OR logic support
    
    Returns:
        Dictionary with 'wtnb' and 'open' keys
    """
    if use_or_logic:
        return {
            "wtnb": [["player experience", "wtnb"]],
            "open": [["player experience", "open"]]
        }
    else:
        return {
            "wtnb": ["player experience", "wtnb"],
            "open": ["player experience", "open"]
        }


def _make_single_role_pattern(*terms):
    """
    Generate a single role pattern (for roles without director/ops_manager distinction).
    
    Args:
        *terms: Terms that identify the role (e.g., "communications", "marketing")
    
    Returns:
        List of terms for fuzzy matching
    
    Example:
        _make_single_role_pattern("communications") → ["communications"]
    """
    return list(terms)


# ──────────────────────────────────────────────────────────────────────────
# SPORT-SPECIFIC PATTERN BUILDERS
# ──────────────────────────────────────────────────────────────────────────


def _build_executive_board_patterns():
    """
    Build position patterns for executive board.
    These are single-role positions without director/ops_manager distinction.
    """
    return {
        "commissioner": {"role": {"exact": "commissioner"}},  # Exact match only
        "vice_commissioner": {"role": _make_single_role_pattern("vice commissioner")},
        "wtnb_commissioner": {"role": _make_single_role_pattern("commissioner", "wtnb")},
        "secretary": {"role": _make_single_role_pattern("secretary")},
        "treasurer": {"role": _make_single_role_pattern("treasurer")},
        "operations_commissioner": {"role": _make_single_role_pattern("operations", "commissioner")},
        "dei_commissioner": {
            "role": [["commissioner", "dei"], ["commissioner", "diversity"]]  # OR logic
        },
        "bowling_commissioner": {"role": _make_single_role_pattern("bowling", "commissioner")},
        "dodgeball_commissioner": {"role": _make_single_role_pattern("dodgeball", "commissioner")},
        "kickball_commissioner": {"role": _make_single_role_pattern("kickball", "commissioner")},
        "pickleball_commissioner": {"role": _make_single_role_pattern("pickleball", "commissioner")}
    }


def _build_cross_sport_patterns():
    """
    Build position patterns for cross-sport leadership.
    These roles don't have director/ops_manager distinction.
    Some roles have OR logic expressed as list of lists.
    """
    return {
        "communications": {"role": _make_single_role_pattern("communications")},
        "events": {
            "open": _make_single_role_pattern("events", "open"),
            "wtnb": _make_single_role_pattern("events", "wtnb")
        },
        "dei": {
            "open": [["diversity", "open"], ["dei", "open"]],  # OR logic: diversity OR dei
            "wtnb": [["diversity", "wtnb"], ["dei", "wtnb"]]
        },
        "marketing": {"role": _make_single_role_pattern("marketing")},
        "philanthropy": {"role": _make_single_role_pattern("philanthropy")},
        "social_media": {
            "open": _make_single_role_pattern("social media", "open"),
            "wtnb": _make_single_role_pattern("social media", "wtnb")
        },
        "technology": {"role": _make_single_role_pattern("technology")},
        "permits_equipment": {"role": _make_single_role_pattern("permits")}
    }


def _build_dodgeball_patterns():
    """
    Build position patterns for dodgeball teams.
    Section context determines sport - no need to require "dodgeball" in patterns.
    """
    return {
        # Non-WTNB Small Ball
        "smallball_advanced": _make_director_ops_patterns("small ball", "advanced"),
        "smallball_social": _make_director_ops_patterns("small ball", "social"),
        
        # WTNB Small Ball (draft and social)
        "wtnb_draft": _make_director_ops_patterns("wtnb", "small ball", "draft"),
        "wtnb_social": _make_director_ops_patterns("wtnb", "small ball", "social"),
        
        # Other ball types
        "foamball": _make_director_ops_patterns("foam ball"),
        "bigball": _make_director_ops_patterns("big ball"),
        
        "player_experience": _make_player_experience_patterns()
    }


def _build_kickball_patterns():
    """
    Build position patterns for kickball teams with OR logic support.
    OR logic is expressed as a list of lists, where each inner list is one option.
    Section context determines sport - no need to require "kickball" in patterns.
    """
    return {
        "sunday": {
            "director": [["sunday", "director"]],
            "ops_manager": [["sunday", "operations manager"]]
        },
        "monday": {
            "director": [["monday", "director"], ["weekday", "social", "director"]],
            "ops_manager": [["monday", "operations manager"], ["weekday", "social", "operations manager"]]
        },
        "tuesday": {
            "director": [["tuesday", "director"]],
            "ops_manager": [["tuesday", "operations manager"]]
        },
        "draft_open": {
            "director": [["wednesday", "director"]],
            "ops_manager": [["wednesday", "operations manager"]]
        },
        "draft_wtnb": {
            "director": [["thursday", "director"], ["wtnb", "draft", "director"]],
            "ops_manager": [["thursday", "operations manager"], ["wtnb", "draft", "operations manager"]]
        },
        "saturday_open": {
            "director": [["saturday", "open", "director"]],
            "ops_manager": [["saturday", "open", "operations manager"]]
        },
        "saturday_wtnb": {
            "director": [["saturday", "wtnb", "director"]],
            "ops_manager": [["saturday", "wtnb", "operations manager"]]
        },
        "player_experience": _make_player_experience_patterns(use_or_logic=True)  # Can have multiple people in 'open'
    }


def _build_bowling_patterns():
    """
    Build position patterns for bowling teams.
    Section context determines sport - no need to require "bowling" in patterns.
    """
    return {
        "sunday": _make_director_ops_patterns("sunday"),
        "monday_open": _make_director_ops_patterns("monday"),
        "monday_wtnb": _make_director_ops_patterns("wtnb"),
        "player_experience": _make_player_experience_patterns()
    }


def _build_pickleball_patterns():
    """
    Build position patterns for pickleball teams.
    Section context determines sport - no need to require "pickleball" in patterns.
    """
    return {
        "advanced": _make_director_ops_patterns("advanced"),
        "social": _make_director_ops_patterns("social"),
        "wtnb": _make_director_ops_patterns("wtnb"),
        "ladder": _make_director_ops_patterns("ladder"),
        "player_experience": _make_player_experience_patterns()
    }


# ──────────────────────────────────────────────────────────────────────────
# CORE UTILITIES
# ──────────────────────────────────────────────────────────────────────────


def _clean_unicode_control_chars(text: str) -> str:
    """
    Remove invisible Unicode control characters (like U+202C directional formatting).
    These characters often come from Google Sheets/Excel and cause issues in JSON/APIs.
    """
    import re
    # Remove Unicode control characters (category Cc and format characters)
    # U+202C, U+202D, U+200E, U+200F are common directional formatting chars
    return re.sub(r'[\u200E\u200F\u202A-\u202E\u2066-\u2069]', '', text)


def _to_snake_case(text: str) -> str:
    """
    Convert a string to snake_case by lowercasing and replacing spaces and special chars with underscores.
    """
    import re
    # Replace any non-alphanumeric character with underscore
    snake = re.sub(r'[^a-zA-Z0-9]+', '_', text.lower())
    # Remove leading/trailing underscores and collapse multiple underscores
    snake = re.sub(r'_+', '_', snake).strip('_')
    return snake


def _extract_person_data(row: List[str], position: str, name_col: int, bars_email_col: int, personal_email_col: int, phone_col: int, birthday_col: int, row_number: Optional[int] = None) -> Dict[str, Any]:
    """
    Extract person data from a CSV row, cleaning Unicode control characters.
    
    Args:
        row: The CSV row
        position: The position string
        name_col, bars_email_col, personal_email_col, phone_col, birthday_col: Column indices
        row_number: 1-based row number in the original CSV (for error reporting)
    
    Returns:
        Dictionary with person data (cleaned of invisible Unicode control chars)
    """
    def clean_field(col_idx: int) -> str:
        """Extract and clean a field from the row."""
        if col_idx < len(row):
            return _clean_unicode_control_chars(row[col_idx].strip())
        return ""
    
    person_data: Dict[str, Any] = {
        "position": position,
        "name": clean_field(name_col),
        "bars_email": clean_field(bars_email_col),
        "personal_email": clean_field(personal_email_col),
        "phone": clean_field(phone_col),
        "birthday": clean_field(birthday_col)
    }
    
    if row_number is not None:
        person_data["_csv_row"] = row_number
        person_data["_csv_columns"] = {
            "name": name_col,
            "bars_email": bars_email_col,
            "personal_email": personal_email_col,
            "phone": phone_col,
            "birthday": birthday_col
        }
    
    return person_data


def _build_leadership_hierarchy_and_mappings(csv_data: List[List[str]], header_row: int, position_col: int, email_col: int) -> Dict:
    """
    Build the complete leadership hierarchy and all necessary mappings from CSV data.
    
    ═══════════════════════════════════════════════════════════════════════
    THIS IS THE INDEPENDENT CATEGORIZATION AND MAPPING SECTION
    ═══════════════════════════════════════════════════════════════════════
    
    This function happens COMPLETELY INDEPENDENTLY of any Slack API calls or
    modal handling. It takes raw CSV data and builds all the hierarchical
    structures and mappings needed for the leadership directory.
    
    Args:
        csv_data: Full CSV data including headers
        header_row: Index of the header row
        position_col: Index of the Position column
        email_col: Index of the BARS Email column
    
    Returns:
        Dictionary containing:
        - hierarchy: Hierarchical structure with all positions
        - position_to_section: Mapping of position -> section key
        - email_to_position: Mapping of email -> position title
        - email_to_section: Mapping of email -> section key
        - emails: List of all valid emails found
        - missing_email_positions: List of positions without emails
    """
    # Detect additional column indices from header row
    header_row_data = csv_data[header_row]
    name_col = None
    phone_col = None
    birthday_col = None
    personal_email_col = None
    
    for idx, header in enumerate(header_row_data):
        header_lower = header.strip().lower()
        if header_lower == "name":
            name_col = idx
        elif header_lower == "phone":
            phone_col = idx
        elif "personal email" in header_lower:
            personal_email_col = idx
        elif header_lower == "birthday":
            birthday_col = idx
    
    # Build hierarchical structure with all position data
    hierarchy = _categorize_positions_hierarchical(
        csv_data, position_col, 
        name_col or 1, email_col, personal_email_col or 6, 
        phone_col or 2, birthday_col or 7
    )
    
    # Create position -> section mapping
    position_to_section = _flatten_hierarchy_to_position_map(hierarchy)
    
    # Extract emails and build mappings from data rows
    processor = CSVProcessor()
    data_rows = csv_data[header_row + 1:]  # Skip header
    
    email_to_position = {}
    email_to_section = {}
    emails = []
    missing_email_positions = []
    
    for row in data_rows:
        if email_col < len(row) and position_col < len(row):
            email = row[email_col].strip()
            position = row[position_col].strip()
            section = position_to_section.get(position)
            
            # Track positions that have no email
            if position and (not email or "@" not in email):
                missing_email_positions.append(position)
            
            if email and "@" in email and section:  # Only include if section is mapped
                emails.append(email)
                email_to_position[email] = position
                email_to_section[email] = section
    
    # Filter valid emails
    valid_emails = processor.filter_valid_emails(emails)
    
    return {
        "hierarchy": hierarchy,
        "position_to_section": position_to_section,
        "email_to_position": email_to_position,
        "email_to_section": email_to_section,
        "emails": valid_emails,
        "missing_email_positions": missing_email_positions
    }


def _generate_display_name_from_path(section_key: str, team_key: str, role_key: str) -> str:
    """
    Generate a human-readable display name from a hierarchical path.
    
    Args:
        section_key: Main section (e.g., "executive_board", "dodgeball")
        team_key: Team/role within section (e.g., "commissioner", "smallball_advanced")
        role_key: Specific role (e.g., "role", "director", "ops_manager")
    
    Returns:
        Human-readable display name
    """
    section_titles = {
        "executive_board": "Executive Board",
        "cross_sport": "Cross-Sport",
        "bowling": "Bowling",
        "dodgeball": "Dodgeball",
        "kickball": "Kickball",
        "pickleball": "Pickleball"
    }
    
    team_titles = {
        # Executive Board
        "commissioner": "Commissioner",
        "vice_commissioner": "Vice Commissioner",
        "wtnb_commissioner": "WTNB Commissioner",
        "secretary": "Secretary",
        "treasurer": "Treasurer",
        "operations_commissioner": "Operations Commissioner",
        "dei_commissioner": "DEI Commissioner",
        "bowling_commissioner": "Bowling Commissioner",
        "dodgeball_commissioner": "Dodgeball Commissioner",
        "kickball_commissioner": "Kickball Commissioner",
        "pickleball_commissioner": "Pickleball Commissioner",
        # Cross-Sport
        "communications": "Communications",
        "events": "Events",
        "dei": "DEI",
        "marketing": "Marketing",
        "philanthropy": "Philanthropy",
        "social_media": "Social Media",
        "technology": "Technology",
        "permits_equipment": "Permits & Equipment",
        # Bowling
        "sunday": "Sunday",
        "monday_open": "Monday Open",
        "monday_wtnb": "Monday WTNB",
        # Dodgeball
        "smallball_advanced": "Small Ball Advanced",
        "smallball_social": "Small Ball Social",
        "wtnb_draft": "WTNB Draft",
        "wtnb_social": "WTNB Social",
        "foamball": "Foam Ball",
        "bigball": "Big Ball",
        # Kickball
        "tuesday": "Tuesday",
        "draft_open": "Draft Open (Wednesday)",
        "draft_wtnb": "Draft WTNB (Thursday)",
        "saturday_open": "Saturday Open",
        "saturday_wtnb": "Saturday WTNB",
        # Shared
        "player_experience": "Player Experience",
        # Pickleball
        "advanced": "Advanced",
        "social": "Social",
        "wtnb": "WTNB",
        "ladder": "Ladder"
    }
    
    role_titles = {
        "role": "",  # For single-role positions
        "director": "Director",
        "ops_manager": "Operations Manager",
        "open": "Open",
        "wtnb": "WTNB"
    }
    
    section_title = section_titles.get(section_key, section_key.replace("_", " ").title())
    team_title = team_titles.get(team_key, team_key.replace("_", " ").title())
    role_title = role_titles.get(role_key, role_key.replace("_", " ").title())
    
    # Build the display name
    if role_key == "role":
        # Single-role positions (executive board, cross-sport)
        return f"{section_title} - {team_title}"
    elif team_key == "player_experience":
        # Player experience positions
        return f"{section_title} - Player Experience ({role_title})"
    else:
        # Standard director/ops_manager positions
        return f"{section_title} - {team_title} ({role_title})"


def _flatten_hierarchy_to_position_map(hierarchy: Dict) -> Dict[str, str]:
    """
    Flatten the hierarchical structure to a simple position -> section path mapping.
    
    Args:
        hierarchy: The hierarchical structure
    
    Returns:
        Dictionary mapping position strings to hierarchical section paths (e.g., "executive_board.commissioner", "dodgeball.smallball_advanced.director")
    """
    position_to_section = {}
    
    for section_key, section_data in hierarchy.items():
        if isinstance(section_data, list):
            # Simple list of positions (shouldn't happen with current structure)
            for item in section_data:
                if isinstance(item, dict) and "position" in item:
                    position_to_section[item["position"]] = section_key
        elif isinstance(section_data, dict):
            # Hierarchical structure
            for team_key, team_data in section_data.items():
                if isinstance(team_data, dict):
                    for role_key, person_data in team_data.items():
                        # Handle both single person (dict) and multiple people (list)
                        if isinstance(person_data, list):
                            # Multiple people in same role (e.g., kickball.player_experience.open)
                            for person in person_data:
                                if person and isinstance(person, dict) and "position" in person:
                                    position_to_section[person["position"]] = f"{section_key}.{team_key}.{role_key}"
                        elif person_data and isinstance(person_data, dict) and "position" in person_data:
                            # Single person
                            position_to_section[person_data["position"]] = f"{section_key}.{team_key}.{role_key}"
    
    return position_to_section

