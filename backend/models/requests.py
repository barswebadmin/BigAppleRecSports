from pydantic import BaseModel
from typing import List, Optional

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