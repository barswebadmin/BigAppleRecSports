from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class ApiResponse(ApiBaseModel):
    type: HTTPStatus
    data: Any | None = None
    errors: list[str | dict] | None = None

    def to_http_response(self) -> JSONResponse:
        status_code = self.type.value if isinstance(self.type, HTTPStatus) else int(self.type)
        return JSONResponse(
            status_code=status_code,
            content=self.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
