from fastapi import Request
from fastapi.responses import JSONResponse


def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Map unhandled exceptions to HTTP responses.

    Registered as a global exception handler in main.py.
    Routes should raise domain exceptions; this converts them
    to appropriate status codes without try/except in every route.
    """
    if isinstance(exc, KeyError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    if isinstance(exc, ModuleNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, PermissionError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    if isinstance(exc, FileNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, ConnectionError):
        return JSONResponse(status_code=502, content={"detail": f"External service error: {exc}"})
    if isinstance(exc, TimeoutError):
        return JSONResponse(status_code=504, content={"detail": f"Request timeout: {exc}"})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
