from typing import Optional, List

from pydantic import BaseModel
from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class EmailMessage(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Gmail message structure."""
    id: str
    thread_id: str
    subject: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: Optional[List[str]] = None
    date: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None


class EmailSearchResult(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Result of email search."""
    messages: List[EmailMessage]
    total_count: int