from typing import Optional

from pydantic import BaseModel
from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT

class ExecutionInfo(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Apps Script execution information."""
    name: Optional[str] = None
    execution_id: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    status: Optional[str] = None
    function_name: Optional[str] = None