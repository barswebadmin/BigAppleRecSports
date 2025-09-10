from pydantic import BaseModel, field_validator, ConfigDict
from typing import List, Optional, Dict, Union

class ProcessLeadershipCSVRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "csv_data": [
                    ["Email", "First Name", "Last Name", "Other Data"],
                    ["user1@example.com", "John", "Doe", "Some data"],
                    ["user2@example.com", "Jane", "Smith", "More data"],
                    ["not-an-email", "Invalid", "Entry", "Will be filtered"]
                ],
                "spreadsheet_title": "2024 Leadership List",
                "year": 2024
            }
        }
    )
    
    csv_data: List[List[str]]  # Array of arrays representing CSV rows
    spreadsheet_title: Optional[str] = None
    year: Optional[int] = None

class RefundSlackNotificationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "order_number": "#12345",
                "requestor_name": {"first": "John", "last": "Doe"},
                "requestor_email": "john.doe@example.com",
                "refund_type": "refund",
                "notes": "Customer requested refund due to schedule conflict",
                "sheet_link": "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit#gid=1435845892&range=A5",
                "request_submitted_at": "2024-09-10T15:30:00Z"
            }
        }
    )
    
    order_number: str
    requestor_name: Union[str, Dict[str, str]]  # Can be string or {"first": "John", "last": "Doe"}
    requestor_email: str
    refund_type: str  # "refund" or "credit"
    notes: str
    sheet_link: Optional[str] = None  # Google Sheets link to the specific row
    request_submitted_at: Optional[str] = None  # ISO 8601 timestamp when form was submitted
    
    @field_validator('requestor_name')
    @classmethod
    def convert_requestor_name(cls, v):
        """Convert string requestor_name to dict format if needed"""
        if isinstance(v, str):
            # If it's a string, try to split into first and last
            parts = v.strip().split(' ', 1)  # Split on first space only
            if len(parts) == 2:
                return {"first": parts[0], "last": parts[1]}
            else:
                # If only one name, put it in first name
                return {"first": v.strip(), "last": ""}
        elif isinstance(v, dict):
            # Ensure required keys exist
            return {
                "first": v.get("first", ""),
                "last": v.get("last", "")
            }
        else:
            raise ValueError(f"requestor_name must be string or dict, got {type(v)}") 