from __future__ import annotations

import os
from typing import Dict, Any, List
import requests


class SlackUsersClient:
    base_url = "https://slack.com/api"

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.verify = (
            "/etc/ssl/certs/ca-certificates.crt" if os.getenv("ENVIRONMENT") == "production" else True
        )

    def list_all_users(self) -> List[Dict[str, Any]]:
        users: List[Dict[str, Any]] = []
        cursor = None
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        while True:
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            resp = requests.get(f"{self.base_url}/users.list", headers=headers, params=params, verify=self.verify)
            data = resp.json()
            if not data.get("ok"):
                break
            members = data.get("members", [])
            users.extend(members)
            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        return users

    @staticmethod
    def find_candidates_by_last_name(users: List[Dict[str, Any]], last_name: str) -> List[Dict[str, Any]]:
        lname = (last_name or "").strip().lower()
        if not lname:
            return []
        candidates: List[Dict[str, Any]] = []
        for u in users:
            profile = u.get("profile", {})
            real_name = (profile.get("real_name_normalized") or profile.get("real_name") or u.get("name") or "").lower()
            if lname and (real_name.endswith(" " + lname) or real_name.split()[-1] == lname or lname in real_name):
                candidates.append(u)
        return candidates

