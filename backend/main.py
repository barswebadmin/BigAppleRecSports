"""
BARS Backend API - Main FastAPI Application

Local dev:    just start
Render prod:  uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api_errors import handle_unhandled_exception
from core.clients import lifespan
from core.config import settings
from routes import router_main

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Big Apple Rec Sports API",
    description="Backend API for BARS operations",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

allowed_origins = [
    "https://docs.google.com",
    "https://script.google.com",
    "http://localhost:3000",
    "http://localhost:8000",
]

if settings.environment == "development":
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/")
async def health():
    return {"name": "BARS backend", "status": "healthy"}


app.include_router(router_main)

app.add_exception_handler(Exception, handle_unhandled_exception)
