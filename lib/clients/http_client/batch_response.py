"""Batch response container for concurrent HTTP requests."""

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class BatchResults(BaseModel):
    """Container for batch request results."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    successes: list[Any] = Field(default_factory=list)
    http_errors: list[Any] = Field(default_factory=list)
    network_errors: list[httpx.TimeoutException | httpx.NetworkError] = Field(default_factory=list)
    other_errors: list[dict[str, Any]] = Field(default_factory=list)
    
    def parse_response(self, response: Any) -> None:
        """Add a response or exception to the appropriate list."""
        # Check for HttpResponse-like objects (multiple classes exist with this name)
        if type(response).__name__ == "HttpResponse":
            if response.ok:
                self.successes.append(response)
            else:
                self.http_errors.append(response)
        elif isinstance(response, httpx.Response):
            if response.is_success:
                self.successes.append(response)
            else:
                self.http_errors.append(response)
        elif isinstance(response, httpx.HTTPStatusError):
            self.http_errors.append(response.response)
        elif isinstance(response, (httpx.TimeoutException, httpx.NetworkError)):
            self.network_errors.append(response)
        elif isinstance(response, dict):
            self.other_errors.append(response)
        else:
            self.other_errors.append({
                "type": type(response).__name__,
                "message": str(response),
            })
    
    @property
    def failures(self) -> list | None:
        res = []
        res.extend(self.http_errors)
        res.extend(self.network_errors)
        res.extend(self.other_errors)
        return res
