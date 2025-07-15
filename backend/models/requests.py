from pydantic import BaseModel
from typing import List, Optional, Dict

class ProcessLeadershipCSVRequest(BaseModel):
    csv_data: List[List[str]]  # Array of arrays representing CSV rows
    spreadsheet_title: Optional[str] = None
    year: Optional[int] = None
    
    class Config:
        json_schema_extra = {
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

class RefundSlackNotificationRequest(BaseModel):
    order_number: str
    requestor_name: Dict[str, str]  # {"first": "John", "last": "Doe"}
    requestor_email: str
    refund_type: str  # "refund" or "credit"
    notes: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_number": "#12345",
                "requestor_name": {"first": "John", "last": "Doe"},
                "requestor_email": "john.doe@example.com",
                "refund_type": "refund",
                "notes": "Customer requested refund due to schedule conflict"
            }
        } 