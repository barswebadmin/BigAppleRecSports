"""HTTP response wrapper — simple delegation to httpx.Response."""

import json
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, NamedTuple

import httpx as HX


@dataclass
class HttpResponse:
    raw: HX.Response

    @property
    def status_code(self) -> int:
        return self.raw.status_code

    @property
    def code(self) -> int:
        return self.status_code

    @property
    def ok(self) -> bool:
        return self.raw.is_success

    # @property
    # def status(self) -> NamedTuple:
    #     return namedtuple("status", ["code", "ok"])(self.status_code, self.ok)

    @property
    def body(self) -> str | dict[str, Any] | list[Any] | None:
        if not self.raw.content:
            return None
        try:
            return self.raw.json()
        except json.JSONDecodeError:
            return self.raw.text

    def error_message(self) -> str:
        raw_res = self.raw
        request: HX.Request = raw_res.request
        method = request.method
        url = request.url
        return f"{method} {url} failed: {raw_res.status_code} {raw_res.reason_phrase} — {raw_res.text[:300]}"
