"""
Admin API Router

FastAPI router for administrative operations.
Delegates all business logic to AdminController and GoogleController.
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request

from controllers.admin.admin_controller import AdminController
from modules.integrations.google.controllers import GoogleController

router = APIRouter(prefix="/admin", tags=["admin"])


def get_admin_controller() -> AdminController:
    """Dependency to get Admin controller."""
    return AdminController()


def get_google_controller() -> GoogleController:
    """Dependency to get Google controller."""
    return GoogleController()


# Google sub-routes
google_router = APIRouter(prefix="/google", tags=["admin-google"])

# TODO: Re-enable when GoogleUserIdentifierRequest model is implemented
# @google_router.get("/users/{identifier}")
# async def get_user(
#     identifier: str,
#     controller: GoogleController = Depends(get_google_controller)
# ) -> APIResponse:
#     """
#     Get a Google user by identifier (email or user ID).
#     
#     Args:
#         identifier: User email or Google user ID
#         
#     Returns:
#         User information including ID, email, name, and organizational details
#         
#     Raises:
#         400: Invalid identifier format
#         404: User not found
#         500: Internal server error
#     """
#     try:
#         return await controller.get_user(identifier)
#     except ValidationAPIError as e:
#         raise HTTPException(status_code=400, detail=e.to_dict()) from e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.get("/groups/{identifier}")
async def get_group(
    identifier: str,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.post("/groups")
async def create_group(
    group_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.post("/groups/{group_email}/members", status_code=201)
async def add_group_member(
    group_email: str,
    member_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """
    Add a member to a Google group.
    
    Args:
        group_email: Group email address
        member_request: Member details including member_email and optional role
        
    Returns:
        Success confirmation with member details
        
    Raises:
        200: Member already exists in group (idempotent operation)
        201: Member successfully added to group
        400: Invalid request format or email addresses
        404: Group not found
        500: Internal server error
    """
    try:
        result = await controller.add_group_member(group_email, member_request)
        
        # Check if this is a warning (member already exists)
        # If so, return 200 instead of 201
        if isinstance(result, dict) and result.get('data', {}).get('warning'):
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=result)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.delete("/groups/{group_email}/members/{member_email}")
async def remove_group_member(
    group_email: str,
    member_email: str,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """
    Remove a member from a Google group.
    
    Args:
        group_email: Group email address
        member_email: Member email address to remove
        
    Returns:
        Success confirmation
        
    Raises:
        400: Invalid email format
        404: Group or member not found
        500: Internal server error
    """
    try:
        return await controller.remove_group_member(group_email, member_email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Users endpoints
@google_router.get("/users/{identifier}")
async def get_user(
    identifier: str,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """Get a Google user by identifier (email or user ID)."""
    try:
        return await controller.get_user(identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.get("/users")
async def list_users(
    max_results: int = 500,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """List all users in the organization."""
    try:
        return await controller.list_users(max_results=max_results)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.post("/users", status_code=201)
async def create_user(
    user_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """Create a new Google user."""
    try:
        return await controller.create_user(user_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Sheets endpoints
@google_router.get("/sheets/{spreadsheet_id}")
async def get_sheet(
    spreadsheet_id: str,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """Get a Google Sheet by ID."""
    try:
        return await controller.get_sheet(spreadsheet_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.post("/sheets", status_code=201)
async def create_sheet(
    sheet_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """Create a new Google Sheet."""
    try:
        return await controller.create_sheet(sheet_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.put("/sheets/{spreadsheet_id}")
async def update_sheet(
    spreadsheet_id: str,
    sheet_request: dict,
    controller: GoogleController = Depends(get_google_controller)
) -> dict:
    """Update a Google Sheet."""
    try:
        return await controller.update_sheet(spreadsheet_id, sheet_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@google_router.post("/emails/aliases")
async def create_google_alias(
    request: Request,
    controller: AdminController = Depends(get_admin_controller)
) -> dict:
    """
    Create a Google email alias.
    
    Args:
        request: FastAPI request object containing JSON body
        
    Returns:
        Success response with alias creation details
        
    Raises:
        400: Invalid request format
        500: Internal server error
    """
    try:
        request_body = await request.json()
        return await controller.handle_create_google_alias(request_body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@google_router.get("/health")
async def google_health_check() -> dict:
    """Health check endpoint for Google admin operations."""
    return {"status": "healthy", "service": "admin-google"}


# Include the Google sub-router
router.include_router(google_router)