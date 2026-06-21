"""The single definition of HTTP request methods used across the project.

Both the httpx client layer (uppercase wire form, e.g. ``HttpMethod.GET``) and the OpenAPI
spec loaders (lowercase ``paths`` operation keys) derive from this one enum — there is no
second list of verbs to keep in sync.
"""

from enum import StrEnum


class HttpMethod(StrEnum):
    """An HTTP request method, canonical uppercase wire form.

    ``_missing_`` accepts any-case input, so ``HttpMethod("get")`` and ``HttpMethod("Get")``
    both resolve to :attr:`HttpMethod.GET`.
    """

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

    @classmethod
    def _missing_(cls, value: object) -> "HttpMethod | None":
        target = str(value).upper()
        return next((member for member in cls if member.value == target), None)

