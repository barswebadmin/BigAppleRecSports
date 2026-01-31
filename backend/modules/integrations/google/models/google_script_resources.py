from typing import Optional

from shared.model_config import ApiModel

class ExecutionInfo(ApiModel):
    """Apps Script execution information."""
    name: Optional[str] = None
    execution_id: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    status: Optional[str] = None
    function_name: Optional[str] = None