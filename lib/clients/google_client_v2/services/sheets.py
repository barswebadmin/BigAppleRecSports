"""Sheets API service namespace with focused, modular methods."""

from typing import TYPE_CHECKING, Any

from ..scopes import SheetsScopes

if TYPE_CHECKING:
    from ..client import GoogleClient


class Sheets:
    """Sheets API operations namespace."""
    
    def __init__(self, client: "GoogleClient"):
        self.client = client
    
    def get_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> list[list[Any]]:
        """Get values from a spreadsheet range.
        
        Args:
            spreadsheet_id: Spreadsheet ID
            range_name: A1 notation range (e.g., "Sheet1!A1:D10")
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readonly)
        
        Returns:
            List of rows, where each row is a list of cell values
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [SheetsScopes.readonly]
        
        sheets_service = self.client.service("sheets", "v4", subject, scopes)
        
        result = self.client.execute(
            sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ),
            scopes=scopes,
        )
        
        return result.get("values", [])
    
    def append_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Append rows to a spreadsheet.
        
        Args:
            spreadsheet_id: Spreadsheet ID
            range_name: A1 notation range to append to
            values: Rows to append (list of row lists)
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)
        
        Returns:
            Response dict with updates info
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [SheetsScopes.readwrite]
        
        sheets_service = self.client.service("sheets", "v4", subject, scopes)
        
        return self.client.execute(
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values},
            ),
            scopes=scopes,
        )
    
    def update_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        values: list[list[Any]],
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Update values in a spreadsheet range.
        
        Args:
            spreadsheet_id: Spreadsheet ID
            range_name: A1 notation range
            values: New values (list of row lists)
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)
        
        Returns:
            Response dict with updates info
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [SheetsScopes.readwrite]
        
        sheets_service = self.client.service("sheets", "v4", subject, scopes)
        
        return self.client.execute(
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values},
            ),
            scopes=scopes,
        )
    
    def clear_values(
        self,
        spreadsheet_id: str,
        range_name: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Clear values in a spreadsheet range.
        
        Args:
            spreadsheet_id: Spreadsheet ID
            range_name: A1 notation range
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)
        
        Returns:
            Response dict
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [SheetsScopes.readwrite]
        
        sheets_service = self.client.service("sheets", "v4", subject, scopes)
        
        return self.client.execute(
            sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
            ),
            scopes=scopes,
        )
