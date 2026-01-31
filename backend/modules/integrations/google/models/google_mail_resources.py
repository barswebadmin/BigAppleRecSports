from typing import Optional, List

from shared.model_config import ApiModel


class EmailMessage(ApiModel):
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


class EmailSearchResult(ApiModel):
    """Result of email search."""
    messages: List[EmailMessage]
    total_count: int