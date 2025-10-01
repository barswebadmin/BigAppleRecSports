#!/usr/bin/env python3
"""
Run script for Big Apple Rec Sports API server
"""

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Set to False in production
        log_level="info"
    ) 