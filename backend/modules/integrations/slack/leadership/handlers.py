"""Slack Bolt command and modal handlers for Leadership bot."""
import logging
from typing import List, Optional, Dict, Tuple

from slack_bolt import Ack
from slack_sdk import WebClient
from slack_sdk.models.blocks import Block

from modules.integrations.slack.leadership.bolt_app import app
from modules.integrations.slack.services.user_lookup_service import UserLookupService
from modules.integrations.slack.client.slack_config import SlackConfig
from modules.integrations.slack.helpers import update_ephemeral_message, download_and_parse_csv
from modules.leadership.services.csv_parser import LeadershipCSVParser
from modules.leadership.services.user_enrichment_service import UserEnrichmentService
from modules.integrations.slack.leadership.results_formatter import LeadershipResultsFormatter
from modules.integrations.slack.builders.generic_builders import GenericMessageBuilder
from modules.integrations.slack.builders.block_builders import SlackBlockBuilder
from modules.integrations.google import GoogleSheetsClient
from shared.csv import parse_csv_text
from shared.csv.csv_processor import CSVProcessor

logger = logging.getLogger(__name__)


@app.command("/update-bars-leadership")
def handle_update_bars_leadership_command(ack: Ack, command: dict, client: WebClient):
    """Handle /update-bars-leadership slash command. Opens a modal for Google Sheet URL."""
    ack()
    
    trigger_id = command["trigger_id"]
    
    blocks = [
        SlackBlockBuilder.text_input(
            action_id="sheet_url",
            label="Google Sheet URL",
            placeholder="https://docs.google.com/spreadsheets/d/...",
            block_id="sheet_url_block"
        ),
        GenericMessageBuilder.context([
            "💡 *Tip:* Make sure the sheet is shared with the BARS service account",
            "📧 Service account: `bars-backend-service@bars-backend-services.iam.gserviceaccount.com`"
        ])
    ]
    
    modal_view = SlackBlockBuilder.modal(
        title="Update BARS Leadership",
        blocks=blocks,
        submit_text="Fetch Sheet",
        close_text="Cancel",
        callback_id="update_leadership_modal"
    )
    
    client.views_open(trigger_id=trigger_id, view=modal_view)


@app.view("update_leadership_modal")
def handle_update_leadership_submission(ack: Ack, body: dict, view: dict, client: WebClient):
    """Handle leadership update modal submission - fetch and parse Google Sheet."""
    ack()
    
    user_id = body["user"]["id"]
    sheet_url = view["state"]["values"]["sheet_url_block"]["sheet_url"]["value"]
    
    try:
        sheets_client = GoogleSheetsClient()
        sheet_id = sheets_client.extract_sheet_id_from_url(sheet_url)
        
        initial_blocks = [
            GenericMessageBuilder.header("📊 Fetching Leadership Data"),
            GenericMessageBuilder.section(f"🔄 Downloading sheet: `{sheet_id[:20]}...`")
        ]
        
        client.chat_postEphemeral(
            channel=user_id,
            user=user_id,
            text="Fetching leadership data from Google Sheets...",
            blocks=initial_blocks
        )
        
        csv_data = sheets_client.fetch_sheet_as_csv(sheet_id)
        
        if not csv_data or len(csv_data) < 5:
            _post_error_message(
                client,
                user_id,
                f"Sheet appears empty or invalid. Found {len(csv_data)} rows."
            )
            return
        
        parser = LeadershipCSVParser()
        hierarchy = parser.parse(csv_data)
        
        enrichment_service = UserEnrichmentService(SlackConfig.Bots.Leadership.token)
        lookup_results = enrichment_service.enrich_hierarchy(hierarchy, max_workers=5, max_retries=3)
        
        formatter = LeadershipResultsFormatter()
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        result_blocks = formatter.format_results_for_slack(analysis)
        
        client.chat_postEphemeral(
            channel=user_id,
            user=user_id,
            text="Leadership data processed successfully",
            blocks=result_blocks
        )
        
    except PermissionError as e:
        logger.error(f"Google Sheets permission error: {e}")
        _post_error_message(
            client,
            user_id,
            f"❌ Permission denied: {str(e)}\n\nMake sure the sheet is shared with: `bars-backend-service@bars-backend-services.iam.gserviceaccount.com`"
        )
    except ValueError as e:
        logger.error(f"Invalid sheet URL or ID: {e}")
        _post_error_message(
            client,
            user_id,
            f"❌ Invalid Google Sheet URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing leadership sheet: {e}", exc_info=True)
        _post_error_message(
            client,
            user_id,
            f"❌ Error processing sheet: {str(e)}"
        )


@app.command("/get-user-ids")
def handle_get_user_ids_command(ack: Ack, command: dict, client: WebClient):
    """Handle /get-user-ids slash command. Opens a modal for CSV paste."""
    ack()
    
    trigger_id = command["trigger_id"]
    
    column_options = [(f"Column {chr(65+i)}", str(i)) for i in range(8)]
    
    blocks = [
        SlackBlockBuilder.text_input(
            action_id="csv_text",
            label="Paste CSV content",
            placeholder="Paste your CSV data here...",
            multiline=True,
            block_id="csv_input_block"
        ),
        SlackBlockBuilder.static_select(
            action_id="column_select",
            label="Email Column",
            options=column_options,
            placeholder="Select column",
            initial_option=("Column F", "5"),
            block_id="column_selector_block"
        ),
        GenericMessageBuilder.context([
            "💡 *Tip:* Column F is typically 'Personal Email' in leadership CSVs"
        ])
    ]
    
    modal_view = SlackBlockBuilder.modal(
        title="Get User IDs",
        blocks=blocks,
        submit_text="Look Up",
        close_text="Cancel",
        callback_id="csv_user_lookup_modal"
    )
    
    client.views_open(trigger_id=trigger_id, view=modal_view)


@app.view("csv_user_lookup_modal")
def handle_csv_user_lookup_submission(ack: Ack, body: dict, view: dict, client: WebClient):
    """Handle CSV user lookup modal submission."""
    ack()
    
    user_id = body["user"]["id"]
    csv_text = view["state"]["values"]["csv_input_block"]["csv_text"]["value"]
    column_index = int(view["state"]["values"]["column_selector_block"]["column_select"]["selected_option"]["value"])
    
    try:
        csv_data = parse_csv_text(csv_text)
        
        if not csv_data or len(csv_data) < 2:
            _post_error_message(client, user_id, "CSV appears empty or invalid")
            return
        
        csv_processor = CSVProcessor()
        values = csv_processor.extract_column_values(csv_data, column_index)
        emails = csv_processor.filter_valid_emails(values)
        
        if not emails:
            _post_error_message(client, user_id, f"No valid emails found in column {chr(65 + column_index)}")
            return
        
        lookup_service = UserLookupService(SlackConfig.Bots.Leadership.token)
        results = lookup_service.lookup_user_ids_by_emails(emails)
        
        _post_results_message(client, user_id, results)
        
    except Exception as e:
        logger.error(f"Error in CSV user lookup: {e}", exc_info=True)
        _post_error_message(client, user_id, f"Error processing CSV: {str(e)}")


def _post_results_message(client: WebClient, user_id: str, results: dict):
    """Post user lookup results to Slack."""
    found = {email: uid for email, uid in results.items() if uid}
    not_found = [email for email, uid in results.items() if not uid]
    
    builder = GenericMessageBuilder()
    blocks = [
        builder.header(f"Found {len(found)} / {len(results)} users"),
        builder.divider()
    ]
    
    if found:
        blocks.append(builder.section("*✅ Found:*"))
        for email, user_id in sorted(found.items()):
            blocks.append(builder.section(f"• {email}: `{user_id}`"))
    
    if not_found:
        blocks.append(builder.divider())
        blocks.append(builder.section("*❌ Not Found:*"))
        for email in sorted(not_found):
            blocks.append(builder.section(f"• {email}"))
    
    client.chat_postMessage(channel=user_id, blocks=blocks, text=f"Found {len(found)}/{len(results)} users")


def _post_error_message(client: WebClient, user_id: str, error_message: str):
    """Post an error message to the user."""
    builder = GenericMessageBuilder()
    client.chat_postMessage(
        channel=user_id,
        text=f"❌ Error: {error_message}",
        blocks=[builder.section(f"❌ *Error*\n{error_message}")]
    )


@app.event("file_shared")
def handle_file_shared(event: dict, client: WebClient, logger):
    """Handle file_shared event for CSV uploads."""
    file_id = event.get("file_id")
    user_id = event.get("user_id")
    channel_id = event.get("channel_id")
    
    if not file_id or not user_id or not channel_id:
        return
    
    try:
        file_info = client.files_info(file=file_id).get("file", {})
        file_name = file_info.get("name", "")
        file_type = file_info.get("filetype", "")
        
        if file_type != "csv" and not file_name.lower().endswith(".csv"):
            return
        
        file_url = file_info.get("url_private")
        
        if not file_url:
            return
        
        csv_data = download_and_parse_csv(file_url, client)
        
        if not csv_data:
            return
        
        header_row, position_col, email_col = _auto_detect_columns(csv_data)
        
        if header_row is None or position_col is None or email_col is None:
            return
        
        _post_file_upload_prompt(
            client, user_id, channel_id, file_id, file_name,
            header_row, position_col, email_col, csv_data
        )
        
    except Exception as e:
        logger.error(f"Error handling file upload: {e}", exc_info=True)


def _auto_detect_columns(csv_data: List[List[str]]) -> Tuple[Optional[int], Optional[int], int]:
    """Auto-detect header row, position column, and email column."""
    for row_idx, row in enumerate(csv_data[:10]):
        row_lower = [cell.lower().strip() if cell else "" for cell in row]
        
        position_col = None
        email_col = None
        
        for col_idx, header in enumerate(row_lower):
            if any(term in header for term in ["position", "role", "title"]):
                position_col = col_idx
            if "personal" in header and "email" in header:
                email_col = col_idx
        
        if position_col is not None and email_col is not None:
            return row_idx, position_col, email_col
    
    return 0, 0, 5


def _post_file_upload_prompt(
    client: WebClient, user_id: str, channel_id: str, file_id: str,
    file_name: str, header_row: int, position_col: int, email_col: int,
    csv_data: List[List[str]]
):
    """Post an ephemeral message prompting user to process the file."""
    header_preview = csv_data[header_row][:8] if len(csv_data) > header_row else []
    
    builder = GenericMessageBuilder()
    blocks = [
        builder.header("CSV File Detected"),
        builder.section(f"*File:* `{file_name}`"),
        builder.section(f"*Auto-detected columns:*\n• Position: Column {chr(65 + position_col)}\n• Email: Column {chr(65 + email_col)}"),
        builder.divider(),
        builder.actions([
            builder.confirm_button(
                text="✅ Process File",
                action_id="confirm_file_process",
                value=f"{file_id}|{position_col}|{email_col}|{header_row}"
            ),
            builder.button(
                text="✏️ Edit Columns",
                action_id="edit_file_columns",
                value=f"{file_id}|{header_row}"
            ),
            builder.button(
                text="❌ Cancel",
                action_id="cancel_file_process"
            )
        ])
    ]
    
    response = client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        blocks=blocks,
        text=f"CSV file detected: {file_name}"
    )


@app.action("confirm_file_process")
def handle_confirm_file_process(ack: Ack, body: dict, client: WebClient, action: dict):
    """Handle user confirming they want to process the uploaded CSV."""
    ack()
    
    try:
        user_id = body["user"]["id"]
        value = action["value"]
        file_id, position_col_str, email_col_str, header_row_str = value.split("|")
        position_col = int(position_col_str)
        email_col = int(email_col_str)
        header_row = int(header_row_str)
    except Exception as e:
        logger.error(f"Error parsing confirm_file_process parameters: {e}", exc_info=True)
        return
    
    response_url = body.get("response_url")
    
    if response_url:
        builder = GenericMessageBuilder()
        update_ephemeral_message(
            response_url,
            "Processing...",
            [builder.section("⏳ *Processing...* Looking up Slack user IDs")]
        )
    
    try:
        file_info = client.files_info(file=file_id).get("file", {})
        file_url = file_info.get("url_private")
        
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = download_and_parse_csv(file_url, client)
        
        if not csv_data:
            _post_error_message(client, user_id, "Could not download CSV file")
            return
        
        blocks = _process_leadership_csv(csv_data, header_row, position_col, email_col)
        
        if response_url:
            update_ephemeral_message(response_url, "Processing complete", blocks)
        
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        
        if response_url:
            builder = GenericMessageBuilder()
            update_ephemeral_message(
                response_url,
                "Error",
                [builder.section(f"❌ *Error* - {str(e)}")]
            )


@app.action("cancel_file_process")
def handle_cancel_file_process(ack: Ack, body: dict, client: WebClient):
    """Handle user canceling file processing."""
    ack()
    
    response_url = body.get("response_url")
    
    if response_url:
        builder = GenericMessageBuilder()
        update_ephemeral_message(
            response_url,
            "Cancelled",
            [builder.section("❌ Processing cancelled")]
        )


@app.action("edit_file_columns")
def handle_edit_file_columns(ack: Ack, body: dict, client: WebClient, action: dict):
    """Handle user requesting to edit column selection."""
    ack()
    
    value = action["value"]
    file_id, header_row_str = value.split("|")
    header_row = int(header_row_str)
    
    channel_id = body.get("channel", {}).get("id")
    message_ts = body.get("message", {}).get("ts")
    response_url = body.get("response_url")
    
    metadata = f"{file_id}|{header_row}|{channel_id}|{message_ts}|{response_url}"
    
    column_options = [(f"Column {chr(65+i)}", str(i)) for i in range(10)]
    
    blocks: List[Block] = [
        SlackBlockBuilder.static_select(
            action_id="position_column_select",
            label="Position Column",
            options=column_options,
            placeholder="Select position column",
            block_id="position_column_block"
        ),
        SlackBlockBuilder.static_select(
            action_id="email_column_select",
            label="Email Column",
            options=column_options,
            placeholder="Select email column",
            initial_option=("Column F", "5"),
            block_id="email_column_block"
        )
    ]
    
    modal_view = SlackBlockBuilder.modal(
        title="Select Columns",
        blocks=blocks,
        submit_text="Process",
        close_text="Cancel",
        callback_id="column_selection_modal",
        private_metadata=metadata
    )
    
    client.views_open(trigger_id=body["trigger_id"], view=modal_view)


@app.view("column_selection_modal")
def handle_column_selection_modal(ack: Ack, body: dict, view: dict, client: WebClient):
    """Handle modal submission with manually selected columns."""
    ack()
    
    user_id = body["user"]["id"]
    
    metadata = view["private_metadata"]
    parts = metadata.split("|")
    file_id = parts[0]
    header_row_index = int(parts[1])
    response_url = parts[4] if len(parts) > 4 else None
    
    position_col = int(view["state"]["values"]["position_column_block"]["position_column_select"]["selected_option"]["value"])
    email_col = int(view["state"]["values"]["email_column_block"]["email_column_select"]["selected_option"]["value"])
    
    if response_url:
        builder = GenericMessageBuilder()
        update_ephemeral_message(
            response_url,
            "Processing...",
            [builder.section("⏳ *Processing...* Looking up Slack user IDs")]
        )
    
    try:
        file_info = client.files_info(file=file_id).get("file", {})
        file_url = file_info.get("url_private")
        
        if not file_url:
            _post_error_message(client, user_id, "Could not get file URL")
            return
        
        csv_data = download_and_parse_csv(file_url, client)
        
        if not csv_data:
            _post_error_message(client, user_id, "Could not download CSV file")
            return
        
        blocks = _process_leadership_csv(csv_data, header_row_index, position_col, email_col)
        
        if response_url:
            update_ephemeral_message(response_url, "Processing complete", blocks)
        
    except Exception as e:
        logger.error(f"Error processing file with manual column selection: {e}", exc_info=True)
        
        if response_url:
            builder = GenericMessageBuilder()
            update_ephemeral_message(
                response_url,
                "Error",
                [builder.section(f"❌ *Error* - {str(e)}")]
            )


def _process_leadership_csv(
    csv_data: List[List[str]],
    header_row: int,
    position_col: int,
    email_col: int
) -> List[Block]:
    """Process leadership CSV and return Slack blocks with results."""
    csv_parser = LeadershipCSVParser()
    hierarchy = csv_parser.parse(csv_data)
    
    enrichment_service = UserEnrichmentService(SlackConfig.Bots.Leadership.token)
    results = enrichment_service.enrich_hierarchy(hierarchy)
    
    formatter = LeadershipResultsFormatter(GenericMessageBuilder())
    analysis = formatter.analyze_completeness(hierarchy, results)
    blocks = formatter.format_results_for_slack(analysis)
    
    return blocks

