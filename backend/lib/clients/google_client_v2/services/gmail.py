"""Gmail API service namespace with method scope mapping."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import GoogleClient


class Gmail:
    """Gmail API request builder with scope tracking.
    
    Builds prepared Google API requests aligned with Gmail API endpoints.
    Methods return request objects that must be executed by the client.
    
    Usage:
        client = GoogleClient()
        
        # Single request
        request = client.gmail.send_message(message_body={"raw": "..."})
        result = client.execute(request)
        
        # Paginated request
        api_method, params = client.gmail.list_messages(query="is:unread")
        results = client.paginate(api_method, result_key="messages", **params)
    """

    # Common Gmail scopes (for reference - NOT used as defaults for security)
    FULL_ACCESS = "https://mail.google.com/"
    READONLY = "https://www.googleapis.com/auth/gmail.readonly"
    SETTINGS_BASIC = "https://www.googleapis.com/auth/gmail.settings.basic"

    SCOPES_MAP: dict[str, list[str]] = {
        "send_message": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.addons.current.action.compose",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.send",
        ],
        "get_message": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.addons.current.message.action",
            "https://www.googleapis.com/auth/gmail.addons.current.message.metadata",
            "https://www.googleapis.com/auth/gmail.addons.current.message.readonly",
            "https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        "list_messages": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
        ],
        "get_send_as": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.settings.basic",
        ],
        "list_send_as": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.settings.basic",
        ],
    }

    def __init__(self, client: "GoogleClient"):
        self.client = client

    @property
    def required_scopes(self) -> list[str]:
        """Return all unique scopes required by any Gmail method."""
        all_scopes = set()
        for scopes in self.SCOPES_MAP.values():
            all_scopes.update(scopes)
        return sorted(all_scopes)

    def send_message(
        self,
        message_body: dict[str, Any],
        subject: str | None = None,
        scopes: list[str] | None = None,
        user_id: str = "me",
    ) -> Any:
        """Build a request to send an email message.

        Args:
            message_body: Message dict with 'raw' (base64url encoded RFC 2822 message)
            subject: Email to impersonate (uses client default if not provided)
            scopes: Required scopes (no default - must be explicit for security)
            user_id: User ID (default: "me")

        Returns:
            Prepared request (call .execute() to send)
        """
        subject = subject or self.client.default_subject
        # scopes = scopes or [self.FULL_ACCESS]  # Intentionally no default - explicit scopes required

        gmail = self.client.service("gmail", "v1", subject, scopes)

        return gmail.users().messages().send(userId=user_id, body=message_body)

    def get_message(
        self,
        message_id: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        user_id: str = "me",
        format: str = "full",
        metadata_headers: list[str] | None = None,
    ) -> Any:
        """Build a request to get a specific email message.

        Args:
            message_id: Gmail message ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Required scopes (no default - must be explicit for security)
            user_id: User ID (default: "me")
            format: Response format (minimal, full, raw, metadata)
            metadata_headers: Headers to include when format=metadata

        Returns:
            Prepared request (call .execute() to fetch)
        """
        subject = subject or self.client.default_subject
        # scopes = scopes or [self.READONLY]  # Intentionally no default - explicit scopes required

        gmail = self.client.service("gmail", "v1", subject, scopes)

        params: dict[str, Any] = {"userId": user_id, "id": message_id, "format": format}
        if metadata_headers:
            params["metadataHeaders"] = metadata_headers

        return gmail.users().messages().get(**params)

    def list_messages(
        self,
        subject: str | None = None,
        scopes: list[str] | None = None,
        user_id: str = "me",
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 100,
        include_spam_trash: bool = False,
    ) -> tuple[Any, dict[str, Any]]:
        """Build arguments for listing messages in mailbox.

        Args:
            subject: Email to impersonate (uses client default if not provided)
            scopes: Required scopes (no default - must be explicit for security)
            user_id: User ID (default: "me")
            query: Gmail search query string
            label_ids: Filter by label IDs
            max_results: Results per page (max: 500)
            include_spam_trash: Include spam/trash messages

        Returns:
            Tuple of (api_method, params) - pass to client.paginate() with result_key="messages"
        """
        subject = subject or self.client.default_subject
        # scopes = scopes or [self.READONLY]  # Intentionally no default - explicit scopes required

        gmail = self.client.service("gmail", "v1", subject, scopes)

        params: dict[str, Any] = {
            "userId": user_id,
            "maxResults": min(max_results, 500),
            "includeSpamTrash": include_spam_trash,
        }
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        return gmail.users().messages().list, params

    def get_send_as(
        self,
        send_as_email: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        user_id: str = "me",
    ) -> Any:
        """Build a request to get a specific send-as alias configuration.

        Args:
            send_as_email: Send-as email address to retrieve
            subject: Email to impersonate (uses client default if not provided)
            scopes: Required scopes (no default - must be explicit for security)
            user_id: User ID (default: "me")

        Returns:
            Prepared request (call .execute() to fetch)
        """
        subject = subject or self.client.default_subject
        # scopes = scopes or [self.SETTINGS_BASIC]  # Intentionally no default - explicit scopes required

        gmail = self.client.service("gmail", "v1", subject, scopes)

        return gmail.users().settings().sendAs().get(
            userId=user_id, sendAsEmail=send_as_email
        )

    def list_send_as(
        self,
        subject: str | None = None,
        scopes: list[str] | None = None,
        user_id: str = "me",
    ) -> Any:
        """Build a request to list all send-as aliases for an account.

        Args:
            subject: Email to impersonate (uses client default if not provided)
            scopes: Required scopes (no default - must be explicit for security)
            user_id: User ID (default: "me")

        Returns:
            Prepared request (call .execute() to fetch, response has "sendAs" key)
        """
        subject = subject or self.client.default_subject
        # scopes = scopes or [self.SETTINGS_BASIC]  # Intentionally no default - explicit scopes required

        gmail = self.client.service("gmail", "v1", subject, scopes)

        return gmail.users().settings().sendAs().list(userId=user_id)
