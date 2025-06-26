from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import leadership
from config import settings

app = FastAPI(
    title="Big Apple Rec Sports API",
    description="Backend API for Big Apple Rec Sports operations",
    version="1.0.2",
    docs_url="/docs" if settings.environment != "production" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.environment != "production" else None,  # Disable redoc in production
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

# Include routers (prefix is already defined in the router)
app.include_router(leadership.router)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Big Apple Rec Sports API",
        "version": "1.0.2",
        "environment": settings.environment,
        "docs_url": "/docs" if settings.environment != "production" else "Contact admin for documentation",
        "health_check": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": "1.0.2",
        "environment": settings.environment
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=settings.environment == "development"
    ) 