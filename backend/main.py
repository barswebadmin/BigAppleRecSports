from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import leadership
from config import settings

app = FastAPI(
    title="Big Apple Rec Sports API",
    description="API for processing leadership discounts and managing recreational sports data",
    version="1.0.1"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leadership.router, prefix="/leadership", tags=["leadership"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Big Apple Rec Sports API",
        "version": "1.0.1",
        "environment": settings.environment
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 