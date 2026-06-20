"""HTTP client: sync for single calls, async-backed for concurrent batch calls."""

import asyncio
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, ClassVar

import httpx as HX
from anyio import CapacityLimiter
from httpx_retries import Retry, RetryTransport

from infrastructure.batch_run import BatchResults, BatchRun
from infrastructure.clients.http.client_auth import BasicAuth, BearerAuth
from infrastructure.clients.http.http_response import HttpResponse
from infrastructure.base_types.http_methods import HttpMethod

logging.getLogger("httpx").addHandler(logging.StreamHandler())


def is_auth_failure(outcome: object) -> bool:
    """Fatal predicate for HTTP batch calls: 401/403 dooms every sibling sharing the same credentials.

    Network errors and timeouts do not have ``status_code``, so they stay retainable by default.
    Pass to ``HttpClient.batch(is_fatal=is_auth_failure)`` or use it as the default.
    """
    return getattr(outcome, "status_code", None) in (401, 403)


@dataclass
class BatchItemRequest:
    """Per-item overrides for one request in a ``HttpClient.batch`` call.

    ``params``, ``body``, and ``auth`` override the shared values supplied to ``batch()``.
    Any field left as ``None`` falls back to the ``batch()``-level default.
    """

    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    auth: BasicAuth | BearerAuth | str | None = None


@dataclass
class HttpClient:
    """HTTP client with sync methods for single calls and an async-backed ``batch`` for concurrent work.

    Bearer-token gotcha — read before passing one:

    httpx (0.28.x as of 2026) ships ``BasicAuth``, ``DigestAuth``, ``NetRCAuth``,
    and the ``Auth`` base class — but **no ``BearerAuth``**. ``FunctionAuth`` exists
    inside ``httpx._auth`` but is not exported in ``httpx.__all__``. Three supported
    paths for a bearer:

    1. Subclass ``httpx.Auth`` and set ``request.headers["Authorization"] = f"Bearer {token}"``
       in ``auth_flow`` (recommended for reusable handlers).
    2. Pass a callable ``(Request) -> Request`` as ``auth=`` — httpx wraps it in
       ``FunctionAuth`` internally (this is what ``BearerAuth.convert()`` returns).
    3. Set the ``Authorization`` header manually via ``headers={"Authorization": "Bearer …"}``.

    Auth-handler vs. header placement: **prefer the auth handler path, not raw headers**.
    Auth handlers run after header merging, so any ``Authorization`` value set via
    ``headers=`` will be **overwritten** by the auth handler on the request. If you
    need to override the client-level bearer for a single call, pass ``auth=`` on
    ``request()`` (httpx's per-request ``auth=`` overrides client-level — verified
    in ``httpx/_client.py::_build_request_auth``). Do not mix ``headers={"Authorization": …}``
    with an active auth handler — the handler wins.
    """

    _http2: ClassVar[bool] = True
    _limits: ClassVar[HX.Limits] = HX.Limits(max_connections=250, max_keepalive_connections=250, keepalive_expiry=30)
    _retry: ClassVar[Retry] = Retry(total=5, backoff_factor=0.5)

    base_url: str = field(default="", kw_only=True)
    auth: BasicAuth | BearerAuth | str | None = field(default=None, kw_only=True)
    bearer: str | None = field(default=None, kw_only=True)
    headers: dict[str, str] | None = field(default=None, kw_only=True)
    timeout_s: int | None = field(default=7, kw_only=True)

    def __post_init__(self) -> None:
        if self.bearer is not None:
            self.auth = BearerAuth(self.bearer)
        elif isinstance(self.auth, str):
            self.auth = BearerAuth(self.auth)

    @cached_property
    def httpx(self) -> HX.Client:
        return HX.Client(
            base_url=self.base_url,
            http2=self._http2,
            transport=RetryTransport(
                HX.HTTPTransport(http2=self._http2, limits=self._limits),
                retry=self._retry,
            ),
        )

    def request(
        self,
        method: HttpMethod | str,
        url: str,
        *,
        auth: BasicAuth | BearerAuth | str | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        body: dict | None = None,
        timeout_s: int | None = None,
    ) -> HttpResponse:
        if isinstance(auth, str):
            auth = BearerAuth(auth)
        if not self.base_url and not url.startswith(("http://", "https://")):
            host = url.split("/", 1)[0].split(":", 1)[0]
            scheme = "http" if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") else "https"
            url = f"{scheme}://{url}"

        all_headers = {**(self.headers or {}), **(headers or {})}
        auth_raw = auth if auth is not None else self.auth
        if isinstance(auth_raw, str):
            auth_raw = BearerAuth(auth_raw)
        effective_timeout = float(timeout_s if timeout_s is not None else (self.timeout_s or 7))
        res: HX.Response = self.httpx.request(
            method,
            url,
            auth=auth_raw.convert() if auth_raw else None,
            headers=all_headers or None,
            params=params,
            json=body,
            timeout=effective_timeout,
        )
        return HttpResponse(raw=res)

    def get(self, url: str, *, params: dict | None = None, **kwargs) -> HttpResponse:
        return self.request(method=HttpMethod.GET, url=url, params=params, **kwargs)

    def post(self, url: str, body: dict | None = None, **kwargs) -> HttpResponse:
        return self.request(method=HttpMethod.POST, url=url, body=body, **kwargs)

    def delete(self, url: str, **kwargs) -> HttpResponse:
        return self.request(method=HttpMethod.DELETE, url=url, **kwargs)

    def put(self, url: str, body: dict | None = None, **kwargs) -> HttpResponse:
        return self.request(method=HttpMethod.PUT, url=url, body=body, **kwargs)

    def patch(self, url: str, body: dict | None = None, **kwargs) -> HttpResponse:
        return self.request(method=HttpMethod.PATCH, url=url, body=body, **kwargs)

    def batch(
        self,
        method: HttpMethod | str,
        url: str,
        items: Iterable[BatchItemRequest],
        *,
        max_concurrent: int = 20,
        is_fatal: Callable[[object], bool] = is_auth_failure,
    ) -> BatchResults:
        """Run ``method`` against ``url`` concurrently for every item, capped at ``max_concurrent``.

        Each ``BatchItemRequest`` carries per-item ``params``, ``body``, and ``auth`` overrides.
        A shared ``AsyncClient`` is scoped to the batch duration for connection reuse.
        Returns bucketed ``BatchResults``; a 401/403 cancels all siblings by default.
        """
        op = HttpBatchRun(
            method=method,
            url=url,
            default_auth=self.auth,
            timeout_s=self.timeout_s,
            transport=RetryTransport(
                HX.AsyncHTTPTransport(http2=self._http2, limits=self._limits),
                retry=self._retry,
            ),
            base_url=self.base_url,
            http2=self._http2,
            max_concurrent=max_concurrent,
            pending=list(items),
            results=BatchResults(is_fatal=is_fatal),
        )
        asyncio.run(op.batch_and_run())
        return op.results


@dataclass
class HttpBatchRun(BatchRun):
    """``BatchRun`` for HTTP batch calls. Scopes one ``AsyncClient`` across all items for connection reuse.

    ``dispatch_task_group`` opens the client before the base schedules tasks.
    ``process`` owns execution under the concurrency cap, capture, classification, and recording.
    """

    method: HttpMethod | str
    url: str
    default_auth: BasicAuth | BearerAuth | str | None
    timeout_s: int | None
    transport: RetryTransport
    base_url: str
    http2: bool
    _ac: HX.AsyncClient | None = field(default=None, init=False, repr=False)

    async def batch_and_run(self) -> None:
        """Open a shared ``AsyncClient`` for the batch duration, then delegate to build."""
        async with HX.AsyncClient(base_url=self.base_url, http2=self.http2, transport=self.transport) as ac:
            self._ac = ac
            await super().batch_and_run()  # → build()

    async def process(self, item: BatchItemRequest, limiter: CapacityLimiter, abort: Callable[[], None]) -> None:
        auth = item.auth if item.auth is not None else self.default_auth
        if isinstance(auth, str):
            auth = BearerAuth(auth)
        async with limiter:
            try:
                res = await self._ac.request(  # type: ignore[union-attr]
                    self.method,
                    self.url,
                    auth=auth.convert() if auth else None,
                    params=item.params,
                    json=item.body,
                    timeout=float(self.timeout_s or 7),
                )
                result: HttpResponse | Exception = HttpResponse(raw=res)
            except Exception as exc:
                result = exc
        fatal = self.results.is_fatal(result)
        self.pending.remove(item)
        self.results.record(item, result, fatal=fatal)
        if fatal:
            abort()
