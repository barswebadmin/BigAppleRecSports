from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import leadership, orders, refunds, slack, webhooks
from config import settings
from version import get_version_info
import logging
import json

app = FastAPI(
    title="Big Apple Rec Sports API",
    description="Backend API for Big Apple Rec Sports operations",
    version=get_version_info()["version"],
    docs_url="/docs"
    if settings.environment != "production"
    else None,  # Disable docs in production
    redoc_url="/redoc"
    if settings.environment != "production"
    else None,  # Disable redoc in production
)

# Configure CORS
allowed_origins = [
    "https://docs.google.com",  # For Google Apps Script
    "https://script.google.com",  # For Google Apps Script
    "http://localhost:3000",  # For local frontend development
    "http://localhost:8000",  # For local backend development
]

if settings.environment == "development":
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = logging.getLogger(__name__)

    # Log incoming request details
    if request.url.path.startswith("/refunds/"):
        logger.info("🌐 === INCOMING REQUEST ===")
        logger.info(f"🌐 Method: {request.method}")
        logger.info(f"🌐 URL: {request.url}")
        logger.info(f"🌐 Headers: {dict(request.headers)}")

        # Read and log the request body for POST requests
        if request.method == "POST":
            body = await request.body()
            if body:
                try:
                    body_json = json.loads(body.decode())
                    logger.info(
                        f"🌐 Request Body (JSON): {json.dumps(body_json, indent=2)}"
                    )
                except json.JSONDecodeError:
                    logger.info(f"🌐 Request Body (Raw): {body.decode()}")
            else:
                logger.info("🌐 Request Body: (empty)")

    response = await call_next(request)

    if request.url.path.startswith("/refunds/"):
        logger.info(f"🌐 Response Status: {response.status_code}")
        logger.info("🌐 === END REQUEST ===")

    return response


# Include routers (prefix is already defined in the router)
app.include_router(leadership.router)
app.include_router(orders.router)
app.include_router(refunds.router)
app.include_router(slack.router)
app.include_router(webhooks.router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    version_info = get_version_info()
    return {
        "message": "Big Apple Rec Sports API",
        "version": version_info["version"],
        "build": version_info["build"],
        "full_version": version_info["full_version"],
        "codename": version_info["codename"],
        "last_updated": version_info["last_updated"],
        "environment": settings.environment,
        "docs_url": "/docs"
        if settings.environment != "production"
        else "Contact admin for documentation",
        "health_check": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    version_info = get_version_info()
    return {
        "status": "healthy",
        "version": version_info["version"],
        "build": version_info["build"],
        "full_version": version_info["full_version"],
        "environment": settings.environment,
        "last_updated": version_info["last_updated"],
    }


@app.get("/version")
async def get_version():
    """Get detailed version information"""
    return get_version_info()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=8000, reload=settings.environment == "development"
    )
# Test change
