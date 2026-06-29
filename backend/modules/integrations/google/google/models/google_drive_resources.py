from typing import Optional, Dict, Any
from pydantic import BaseModel
from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class SheetRevision(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Google Sheets revision information."""
    id: str
    modified_time: str
    modified_user: Optional[Dict[str, Any]] = None
    published: Optional[bool] = None
    published_auto: Optional[bool] = None
    published_domain: Optional[str] = None
    published_outside_domain: Optional[bool] = None