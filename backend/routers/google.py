"""
Google API Router

FastAPI router for Google API endpoints.
Delegates all business logic to GoogleController.
"""

from fastapi import APIRouter, HTTPException, Depends

from backend.modules.integrations.google.controllers import GoogleController
from backend.modules.integrations.google.models import GoogleGroupMemberRequest
from backend.shared.api_models import APIResponse, ValidationAPIError

router = APIRouter(prefix="/google", tags=["google"])


def get_google_controller() -> GoogleController:
    """Dependency to get Google controller."""
    return GoogleController()


@router.get("/users/{identifier}")
async def get_user(
    identifier: str,
    controller: GoogleController = Depends(get_google_controller)
) -> APIResponse:
    """
    Get a Google user by identifier (email or user ID).
    
    Args:
        identifier: User email or Google user ID
        
    Returns:
        User information including ID, email, name, and organizational details
        
    Raises:
        400: Invalid identifier format
        404: User not found
        500: Internal server error
    """
    try:
        return await controller.get_user(identifier)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/groups/{identifier}")
async def get_group(
    identifier: str,
    controller: GoogleController = Depends(get_google_controller)
) -> APIResponse:
    """
    Get a Google group by identifier (email or group ID).
    
    Args:
        identifier: Group email or Google group ID
        
    Returns:
        Group information including ID, email, name, description, and member count
        
    Raises:
        400: Invalid identifier format
        404: Group not found
        500: Internal server error
    """
    try:
        return await controller.get_group(identifier)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/groups")
async def create_group(
    group_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> APIResponse:
    """
    Create a new Google group.
    
    Args:
        group_request: Group details including email, name, and description
        
    Returns:
        Success confirmation with group details
        
    Raises:
        400: Invalid request format
        500: Internal server error
    """
    try:
        return await controller.create_group(group_request)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/groups/{group_email}/members")
async def add_group_member(
    group_email: str,
    member_request: GoogleGroupMemberRequest,
    controller: GoogleController = Depends(get_google_controller)
) -> APIResponse:
    """
    Add a member to a Google group.
    
    Args:
        group_email: Group email address
        member_request: Member details including email and role
        
    Returns:
        Success confirmation with member details
        
    Raises:
        400: Invalid request format or email addresses
        404: Group not found
        500: Internal server error
    """
    try:
        # Override group_email from URL path
        member_request.group_email = group_email
        return await controller.add_group_member(member_request)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for Google API."""
    return {"status": "healthy", "service": "google"}