from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class ValueRange(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Google Sheets API ValueRange response structure."""
    range_: Optional[str] = Field(None, alias='range')  # 'range' is a Python keyword
    major_dimension: Optional[str] = None  # 'ROWS' or 'COLUMNS'
    values: Optional[list[list[str]]] = None


class UpdateValuesResponse(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Google Sheets API UpdateValuesResponse structure."""
    spreadsheet_id: Optional[str] = None
    updated_cells: Optional[int] = None
    updated_columns: Optional[int] = None
    updated_rows: Optional[int] = None
    updated_range: Optional[str] = None


class BatchUpdateValuesResponse(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Google Sheets API BatchUpdateValuesResponse structure."""
    total_updated_cells: int
    total_updated_columns: int
    total_updated_rows: int
    total_updated_sheets: int
    responses: list[UpdateValuesResponse]


class SheetDataWithFormatting(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Sheet data including values and formatting."""
    values: List[List[str]]
    backgrounds: List[List[Dict[str, Any]]]
    row_count: int
    column_count: int