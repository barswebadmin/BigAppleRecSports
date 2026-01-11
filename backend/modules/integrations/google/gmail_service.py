"""
Google Gmail API service methods and models.

Contains Gmail-specific functionality: models, methods, and helper functions.
"""

import logging
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from backend.shared.model_config import ApiModel
from .base_methods import handle_http_errors

logger = logging.getLogger(__name__)


# Models
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


# Service methods (to be mixed into GoogleApiClient)
class GmailServiceMixin:
    """Mixin class containing Google Gmail API methods."""
    
    @handle_http_errors
    def find_emails(
        self,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        after_date: Optional[datetime] = None,
        before_date: Optional[datetime] = None,
        days_ago: Optional[int] = None,
        max_results: int = 50,
        include_body: bool = True
    ) -> EmailSearchResult:
        """
        Find emails sent by the authenticated user matching search criteria.
        
        Args:
            subject: Subject line text to search for (partial match)
            body_text: Body text to search for (partial match)
            from_address: From address to filter by (defaults to authenticated user)
            to_address: To address to filter by
            after_date: Only return emails sent after this date
            before_date: Only return emails sent before this date
            days_ago: Shortcut - search emails from the past N days (e.g., 7 for past week)
            max_results: Maximum number of results to return (default: 50, max: 500)
            include_body: If True, fetch full message body (default: True)
        
        Returns:
            EmailSearchResult containing list of EmailMessage objects and total count
        
        Raises:
            HttpError: For Google API errors
        
        Example:
            >>> client = GoogleApiClient()
            >>> # Find emails with "waitlist" in subject from past week
            >>> result = client.find_emails(subject="waitlist", days_ago=7)
            >>> print(f"Found {result.total_count} emails")
            >>> for msg in result.messages:
            ...     print(f"{msg.subject} - {msg.date}")
            >>> 
            >>> # Find emails with "position" in body
            >>> result = client.find_emails(body_text="position")
            >>> 
            >>> # Find emails with both subject and body matches
            >>> result = client.find_emails(subject="waitlist", body_text="position")
        """
        # Build Gmail search query
        query_parts = []
        
        # Default to emails sent by the authenticated user
        if from_address:
            query_parts.append(f'from:{from_address}')
        else:
            query_parts.append('from:me')
        
        if subject:
            query_parts.append(f'subject:"{subject}"')
        
        if body_text:
            query_parts.append(f'"{body_text}"')
        
        if to_address:
            query_parts.append(f'to:{to_address}')
        
        # Date filtering
        if days_ago:
            # Gmail API supports newer_than with days (1d, 2d, ..., 7d, 1m, 1y)
            if days_ago <= 7:
                query_parts.append(f'newer_than:{days_ago}d')
            else:
                # For longer periods, calculate the date
                cutoff_date = datetime.now() - timedelta(days=days_ago)
                query_parts.append(f'after:{cutoff_date.strftime("%Y/%m/%d")}')
        else:
            if after_date:
                query_parts.append(f'after:{after_date.strftime("%Y/%m/%d")}')
            if before_date:
                query_parts.append(f'before:{before_date.strftime("%Y/%m/%d")}')
        
        query = ' '.join(query_parts)
        
        logger.info(f"Searching Gmail with query: {query}")
        
        # Search for messages
        messages_list = []
        page_token = None
        total_fetched = 0
        
        while total_fetched < max_results:
            request_params: Dict[str, Any] = {
                'userId': 'me',
                'q': query,
                'maxResults': min(max_results - total_fetched, 500)
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            response = self.gmail_service.users().messages().list(**request_params).execute()
            
            message_ids = response.get('messages', [])
            if not message_ids:
                break
            
            # Fetch message details
            for msg_ref in message_ids:
                if total_fetched >= max_results:
                    break
                
                msg_id = msg_ref['id']
                message = self._get_message_details(msg_id, include_body=include_body)
                if message:
                    messages_list.append(message)
                    total_fetched += 1
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        logger.info(f"✅ Found {len(messages_list)} emails matching search criteria")
        
        return EmailSearchResult(
            messages=messages_list,
            total_count=len(messages_list)
        )
    
    @handle_http_errors
    def _get_message_details(self, message_id: str, include_body: bool = True) -> Optional[EmailMessage]:
        """
        Get detailed information about a Gmail message.
        
        Args:
            message_id: Gmail message ID
            include_body: If True, include full message body
        
        Returns:
            EmailMessage object or None if message not found
        """
        format_type = 'full' if include_body else 'metadata'
        
        message = self.gmail_service.users().messages().get(
            userId='me',
            id=message_id,
            format=format_type
        ).execute()
        
        headers = message.get('payload', {}).get('headers', [])
        
        # Extract headers
        subject = None
        from_address = None
        to_addresses = None
        date = None
        
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name == 'subject':
                subject = value
            elif name == 'from':
                from_address = value
            elif name == 'to':
                to_addresses = [addr.strip() for addr in value.split(',')]
            elif name == 'date':
                date = value
        
        # Extract body
        body_text = None
        body_html = None
        
        if include_body:
            body_text, body_html = self._extract_message_body(message.get('payload', {}))
        
        return EmailMessage(
            id=message.get('id', ''),
            thread_id=message.get('threadId', ''),
            subject=subject,
            from_address=from_address,
            to_addresses=to_addresses,
            date=date,
            snippet=message.get('snippet'),
            body_text=body_text,
            body_html=body_html
        )
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """
        Extract text and HTML body from Gmail message payload.
        
        Args:
            payload: Gmail message payload dictionary
        
        Returns:
            Tuple of (body_text, body_html)
        """
        body_text = None
        body_html = None
        
        # Check if message has parts (multipart)
        parts = payload.get('parts', [])
        
        if parts:
            # Multipart message - search through parts
            for part in parts:
                mime_type = part.get('mimeType', '')
                body_data = part.get('body', {}).get('data')
                
                if mime_type == 'text/plain' and body_data and not body_text:
                    body_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html' and body_data and not body_html:
                    body_html = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                
                # Recursively check nested parts
                nested_parts = part.get('parts', [])
                if nested_parts:
                    nested_text, nested_html = self._extract_message_body({'parts': nested_parts})
                    if nested_text and not body_text:
                        body_text = nested_text
                    if nested_html and not body_html:
                        body_html = nested_html
        else:
            # Simple message - single part
            mime_type = payload.get('mimeType', '')
            body_data = payload.get('body', {}).get('data')
            
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                if mime_type == 'text/plain':
                    body_text = decoded
                elif mime_type == 'text/html':
                    body_html = decoded
        
        return body_text, body_html
