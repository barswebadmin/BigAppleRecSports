from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(Exception):
    """Resource lookup returned no match."""


class UnprocessableError(Exception):
    """Input was well-formed but cannot be processed (e.g., unsupported value)."""


STATUS_MAP: dict[type[Exception], int] = {
    ValueError: 400,
    UnprocessableError: 422,
    NotFoundError: 404,
}


async def handle_known_exception(request: Request, exc: Exception) -> JSONResponse:
    status = STATUS_MAP[type(exc)]
    return JSONResponse(status_code=status, content={"detail": str(exc)})


def install(app: FastAPI) -> None:
    for exc_type in STATUS_MAP:
        app.add_exception_handler(exc_type, handle_known_exception)
