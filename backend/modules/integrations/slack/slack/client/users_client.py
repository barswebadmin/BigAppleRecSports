"""Async Slack Users API client with centralized HTTP error handling and retries."""

from __future__ import annotations

from typing import Dict, Any, List

from shared_utilities.api_clients.http_client import AsyncHTTPClient, RetryPolicy


class SlackUsersClient(AsyncHTTPClient):
    """Async Slack Users API client with centralized HTTP error handling and retries."""

    def __init__(self, bearer_token: str, **kwargs):
        # Set up SSL verification based on environment
        verify = (
            "/etc/ssl/certs/ca-certificates.crt"
            if os.getenv("ENVIRONMENT") == "production"
            else True
        )

        # Configure retry policy for Slack API
        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            retryable_status_codes=[429, 500, 502, 503, 504]  # Include 429 for rate limiting
        )

        # Initialize with Slack API base URL and configuration using component-based headers
        super().__init__(
            base_url="https://slack.com/api",
            auth={"authorization": f"Bearer {bearer_token}"},
            verify=verify,
            retry_policy=retry_policy,
            **kwargs
        )

    async def list_all_users(self) -> List[Dict[str, Any]]:
        """List all users with automatic pagination and error handling."""
        users: List[Dict[str, Any]] = []
        cursor = None

        while True:
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor

            # Use inherited async HTTP client with automatic retries
            response = await self.get("/users.list", params=params)
            data = response.json()

            if not data.get("ok"):
                break

            members = data.get("members", [])
            users.extend(members)
            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break

        return users

    @staticmethod
    def find_candidates_by_last_name(
        users: List[Dict[str, Any]], last_name: str
    ) -> List[Dict[str, Any]]:
        """Find user candidates by last name."""
        lname = (last_name or "").strip().lower()
        if not lname:
            return []

        candidates: List[Dict[str, Any]] = []
        for u in users:
            profile = u.get("profile", {})
            real_name = (
                profile.get("real_name_normalized")
                or profile.get("real_name")
                or u.get("name")
                or ""
            ).lower()
            if lname and (
                real_name.endswith(" " + lname)
                or real_name.split()[-1] == lname
                or lname in real_name
            ):
                candidates.append(u)

        return candidates