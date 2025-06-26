from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import leadership
from config import settings

app = FastAPI(
    title="Big Apple Rec Sports API",
    description="Backend API for Big Apple Rec Sports operations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leadership.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Big Apple Rec Sports API",
        "version": "1.0.0",
        "environment": settings.environment
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 