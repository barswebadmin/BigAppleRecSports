
from datetime import datetime
from typing import Optional, List
import logging

from google.oauth2.service_account import Credentials
from modules.integrations.google.services._google_api_service_builder import build_google_api_service

from modules.integrations.google.base_methods import handle_http_errors
from modules.integrations.google.models.google_drive_resources import SheetRevision

logger = logging.getLogger(__name__)

class GoogleDriveService():    
    def __init__(self):
        
        required_scopes = [
            'https://www.googleapis.com/auth/drive',
        ]

        self.service = build_google_api_service('drive', 'v3', required_scopes)
        self.required_scopes = required_scopes  # Store for error diagnostics
        self.revisions = self.service.revisions()  # type: ignore[attr-defined]

    @handle_http_errors
    def get_sheet_revisions(
        self,
        spreadsheet_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[SheetRevision]:
        """
        Get sheet revision history, optionally filtered by time range.
        
        Args:
            spreadsheet_id: The ID of the Google Sheet
            start_time: Optional start time to filter revisions
            end_time: Optional end time to filter revisions
        
        Returns:
            List of SheetRevision objects
        
        Raises:
            HttpError: For Google API errors
        """
        logger.info(f"Fetching revisions for spreadsheet: {spreadsheet_id[:20]}...")
        
        revisions_result = self.revisions().list(
            fileId=spreadsheet_id
        ).execute()
        
        revisions_list = revisions_result.get('revisions', [])
        
        # Filter by time if provided
        if start_time or end_time:
            filtered_revisions = []
            for rev in revisions_list:
                modified_time_str = rev.get('modifiedTime', '')
                if modified_time_str:
                    try:
                        modified_time = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))
                        if start_time and modified_time < start_time:
                            continue
                        if end_time and modified_time > end_time:
                            continue
                        filtered_revisions.append(SheetRevision(**rev))
                    except Exception as e:
                        logger.warning(f"Could not parse revision time: {e}")
                        continue
            revisions_list = filtered_revisions
        else:
            revisions_list = [SheetRevision(**rev) for rev in revisions_list]
        
        logger.info(f"✅ Found {len(revisions_list)} revisions")
        
        return revisions_list