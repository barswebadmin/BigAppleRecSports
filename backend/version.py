# Backend Version Management
# This file tracks the current version of the BARS backend API

__version__ = "2.0.0"
__build__ = 4
__last_updated__ = "2025-06-26"
__codename__ = "Render Ready"

# Version history for reference
VERSION_HISTORY = [
    {
        "version": "1.0.0",
        "date": "2024-06-25",
        "description": "Initial FastAPI backend with leadership processing"
    },
    {
        "version": "1.0.1", 
        "date": "2024-06-25",
        "description": "Added CSV processing and display text generation"
    },
    {
        "version": "1.0.2",
        "date": "2025-06-26", 
        "description": "Production-ready with security, CORS, and monitoring"
    }
]

def get_version():
    """Return the current version string"""
    return __version__

def get_full_version():
    """Return version with build number"""
    return f"{__version__}.{__build__}"

def get_version_info():
    """Return complete version information"""
    return {
        "version": __version__,
        "build": __build__,
        "full_version": get_full_version(),
        "last_updated": __last_updated__,
        "codename": __codename__
    }

def get_latest_changes():
    """Get the most recent version changes"""
    if VERSION_HISTORY:
        return VERSION_HISTORY[-1] 