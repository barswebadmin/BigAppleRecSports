from __future__ import annotations

from typing import Dict, Any, List, Optional
import requests
import os


class SlackUsergroupClient:
    base_url = "https://slack.com/api"

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        # Use environment SSL cert path or default to True for system certs
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        self.verify = ssl_cert_file if os.path.exists(ssl_cert_file) else True

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = requests.post(f"{self.base_url}/{endpoint}", data=payload, headers=headers, verify=self.verify)
        try:
            return response.json()
        except Exception:
            return {"ok": False, "error": f"invalid_json:{response.status_code}"}

    def list_usergroups(self) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        response = requests.get(f"{self.base_url}/usergroups.list", headers=headers, verify=self.verify)
        data = response.json()
        if not data.get("ok"):
            return []
        return data.get("usergroups", [])

    def get_usergroup_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        for group in self.list_usergroups():
            if group.get("handle") == handle:
                return group
        return None

    def create_usergroup(self, name: str, handle: str, description: Optional[str] = None) -> Optional[str]:
        payload = {"name": name, "handle": handle}
        if description:
            payload["description"] = description
        data = self._post("usergroups.create", payload)
        if data.get("ok"):
            return data.get("usergroup", {}).get("id")
        return None

    def update_usergroup_users(self, usergroup_id: str, user_ids: List[str]) -> bool:
        payload = {"usergroup": usergroup_id, "users": ",".join(user_ids)}
        data = self._post("usergroups.users.update", payload)
        return bool(data.get("ok"))

