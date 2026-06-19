"""Client auth: ``AuthType`` catalog, credential types, and httpx auth conversion at the boundary.

Coerce call-site inputs (credentials, bearer string, or ``(user, pass)`` tuple) here; convert to
``HX.Auth`` only via ``to_httpx_auth`` at the httpx boundary.
"""

import re
from abc import abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Any, Self

import httpx as HX
from autoregistry import Registry

from infrastructure.interaction.prompts import select_from_options
from utils.encoding_utils import b64_encode

# auth_type = Registry(suffix="_auth")

# @auth_type
# def basic_auth(username: str, password: str):
#     return username, password


@dataclass
class BasicAuth:
    username: str
    password: str
    
    def convert(self) -> tuple[str, str]:
        return self.username, self.password

@dataclass
class BearerAuth:
    bearer: str
    
    @staticmethod
    def modify_header(token: str, request: HX.Request):
        request.headers["Authorization"] = f"Bearer {token}"
        return request

    
    def convert(self) -> Callable[[HX.Request], HX.Request]:
        return partial(self.modify_header, self.bearer)

Auth = BasicAuth | BearerAuth

# @dataclass
# class AuthType(Registry):
#     """Auth type. Use AuthType.Bearer, AuthType.OAuth2, etc. Value is the string."""

#     # Bearer = "bearer"
#     # OAuth2 = "oauth2"
#     # Basic = "basic"
#     # ApiKey = "api_key"

#     @abstractmethod
#     def to_httpx(self) -> Any:
#         """Attack another Pokemon."""

# class BasicAuth(AuthType):
#     """Base64-encoded username:password."""

#     username: str
#     password: str

#     def to_httpx(self):
#         return self.username, self.password


# class FunctionAuth(AuthType):
#     """httpx auth that sets a precomputed ``Authorization`` header value (e.g. ``Bearer x``, ``Basic y``)."""

#     _auth_type: str

#     def add_auth_header(self, request: HX.Request, value: str):
#         request.headers["Authorization"] = f"{self._auth_type} {value}"

#     def to_httpx(self):
#         ...


# class BearerAuth(FunctionAuth):
#     _auth_type: str = "Bearer"
#     bearer: str

    

#     def to_httpx(self):
#         return FunctionAuth(self._auth_type, self.bearer)





# @dataclass(frozen=True)
# class ApiKeyCredentials:
#     """API key auth. Placement: custom header (default), Authorization header, or JSON body key."""

#     api_key: str
#     api_key_header: str | None = None
#     """Header name when using header placement (default X-API-Key). Ignored if use_authorization_header or api_key_body_key set."""
#     use_authorization_header: bool = False
#     """If True, set Authorization: {authorization_scheme} {api_key} instead of a custom header."""
#     authorization_scheme: str = "apikey"
#     """Scheme for Authorization header when use_authorization_header=True (e.g. 'apikey', 'xapikey')."""
#     api_key_body_key: str | None = None
#     """If set, do not set any header; inject api_key into JSON body under this key on JSON requests."""

#     def to_httpx(self) -> HX.Auth:
#         raise NotImplementedError("ApiKey auth is not yet wired to httpx")


# @dataclass(frozen=True)
# class OAuth2Credentials:
#     client_id: str
#     client_secret: str
#     token_endpoint: str | None = None
#     token: dict[str, Any] | None = None
#     token_endpoint_auth_method: str | None = None

#     def to_httpx(self) -> HX.Auth:
#         raise NotImplementedError("OAuth2 auth is not yet wired to httpx")


# Credentials = BearerCredentials | BasicCredentials | ApiKeyCredentials | OAuth2Credentials

# # Attached to AuthType (used by AuthType.credential_class). Defined after credential classes exist.
# _AUTH_CREDENTIAL_CLASS: dict[AuthType, type] = {
#     AuthType.Bearer: BearerCredentials,
#     AuthType.Basic: BasicCredentials,
#     AuthType.ApiKey: ApiKeyCredentials,
#     AuthType.OAuth2: OAuth2Credentials,
# }


# def credentials_for_auth(auth_type: AuthType) -> type:
#     """Return the credential type expected for the given AuthType."""
#     return auth_type.credential_class


# _CLI_AUTH_BUILDERS: dict[str, Callable[[str], Credentials]] = {
#     "bearer": BearerCredentials,
#     "basic": BasicCredentials.from_pair,
# }


# def credentials_from_cli(*, bearer: str | None = None, basic: str | None = None) -> Credentials | None:
#     """Build credentials from at most one CLI auth input (bearer token or ``user:pass``)."""
#     provided = [(scheme, raw) for scheme, raw in (("bearer", bearer), ("basic", basic)) if raw]
#     if not provided:
#         return None
#     if len(provided) > 1:
#         raise ValueError("Provide only one of bearer or basic")
#     scheme, raw = provided[0]
#     return _CLI_AUTH_BUILDERS[scheme](raw)


# def has_authorization_header(headers: Mapping[str, str] | None) -> bool:
#     """True if any header key is ``Authorization`` (case-insensitive)."""
#     return bool(headers) and any(name.lower() == "authorization" for name in headers)


# _BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/=]+")


# def _is_base64(s: str) -> bool:
#     """Check if string looks like valid base64 (no spaces/colons, only base64 chars)."""
#     return bool(_BASE64_PATTERN.fullmatch(s))


# def normalize_authorization_header(value: str) -> str:
#     """Auto-encode Basic auth if the credentials contain `:` or ` ` (i.e. not yet base64-encoded).

#     ``Basic user:pass`` → ``Basic <base64(user:pass)>``
#     ``Basic dXNlcjpwYXNz`` (already encoded) → unchanged
#     ``Bearer token`` → unchanged
#     """
#     if not value.lower().startswith("basic "):
#         return value
#     payload = value[6:].strip()
#     if ":" in payload or " " in payload or not _is_base64(payload):
#         return f"Basic {b64_encode(payload)}"
#     return value


# # Placeholder ``Authorization`` values for editor-fill guardrails: the user replaces the
# # ``__…__`` tokens with real credentials before the request is sent. Keys are the selectable schemes.
# AUTH_HEADER_PLACEHOLDERS: dict[str, str] = {
#     "basic": "Basic __username_here__:__password_here__",
#     "bearer": "Bearer __token_here__",
# }


# async def prompt_auth_header_placeholder() -> str | None:
#     """Guardrail prompt: ask for an auth pattern; return its placeholder ``Authorization`` value, or None for 'none'."""
#     choice = await select_from_options(
#         "Auth pattern (edit the placeholder before sending)",
#         options=["none", *AUTH_HEADER_PLACEHOLDERS],
#         default_value="none",
#         # Don't seed the buffer with "(1) none"; typing a number to pick another option would append
#         # to it (e.g. "(1) none2"). Empty Enter still resolves to the default.
#         preselect_default_in_input=False,
#     )
#     return AUTH_HEADER_PLACEHOLDERS.get(choice or "")


# type AuthCoerceInput = Credentials | str | tuple[str, str] | HX.Auth


# def _coerce_credentials(value: AuthCoerceInput) -> Credentials | None:
#     if value is None:
#         return None
#     if isinstance(value, (BearerCredentials, BasicCredentials, ApiKeyCredentials, OAuth2Credentials)):
#         return value
#     if isinstance(value, str):
#         return BearerCredentials(value)
#     if isinstance(value, tuple) and len(value) == 2:
#         return BasicCredentials.from_pair(f"{value[0]}:{value[1]}")
#     raise TypeError(f"Unsupported auth input: {type(value).__name__}")


# def to_httpx_auth(value: AuthCoerceInput) -> HX.Auth | None:
#     """Convert call-site auth to ``HX.Auth``; pass through legacy ``HX.Auth`` instances."""
#     if isinstance(value, HX.Auth):
#         return value
#     credentials = _coerce_credentials(value)
#     return credentials.to_httpx() if credentials is not None else None

# if __name__ == "__main__":
    