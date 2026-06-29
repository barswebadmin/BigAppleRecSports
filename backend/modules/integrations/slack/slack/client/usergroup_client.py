from __future__ import annotations

from typing import Dict, Any, List, Optional

from shared_utilities.api_clients.http_client import AsyncHTTPClient, RetryPolicy


class SlackUsergroupClient(AsyncHTTPClient):
    """Async Slack Usergroups API client with centralized HTTP error handling and retries."""

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

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Post data to Slack API endpoint with form encoding."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            # Use inherited async HTTP client with automatic retries
            response = await self.post(f"/{endpoint}", data=payload, headers=headers)
            return response.json()
        except Exception:
            return {"ok": False, "error": f"invalid_json:{response.status_code}"}

    async def list_usergroups(self) -> List[Dict[str, Any]]:
        """List all usergroups with automatic error handling."""
        try:
            # Use inherited async HTTP client with automatic retries
            response = await self.get("/usergroups.list")
            data = response.json()
            if not data.get("ok"):
                return []
            return data.get("usergroups", [])
        except Exception:
            return []

    async def get_usergroup_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        """Get usergroup by handle."""
        usergroups = await self.list_usergroups()
        for group in usergroups:
            if group.get("handle") == handle:
                return group
        return None

    async def create_usergroup(
        self, name: str, handle: str, description: Optional[str] = None
    ) -> Optional[str]:
        """Create a new usergroup."""
        payload = {"name": name, "handle": handle}
        if description:
            payload["description"] = description
        data = await self._post("usergroups.create", payload)
        if data.get("ok"):
            return data.get("usergroup", {}).get("id")
        return None

    async def update_usergroup_users(self, usergroup_id: str, user_ids: List[str]) -> bool:
        """Update usergroup members."""
        payload = {"usergroup": usergroup_id, "users": ",".join(user_ids)}
        data = await self._post("usergroups.users.update", payload)
        return bool(data.get("ok"))

