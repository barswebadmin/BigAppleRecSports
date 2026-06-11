import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from routes import orders_router, reg_router
from service_errors import ServiceErrors
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

app = FastAPI(title="BARS Registrations API")


@app.exception_handler(ServiceErrors)
async def service_errors_handler(request: Request, exc: ServiceErrors) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "; ".join(e.message for e in exc.errors)},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bigapplerecsports.com", "https://admin.shopify.com"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(reg_router)
app.include_router(orders_router)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        reload=True,
        reload_dirs=[".", "../../lib/clients/shopify"],
    )
