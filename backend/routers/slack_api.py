"""
Slack API Router

FastAPI router for Slack API endpoints.
Delegates all business logic to SlackAPIController.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from modules.integrations.slack.controllers import SlackAPIController
from modules.integrations.slack.models import (
    SlackMessageRequest,
    SlackUserGroupRequest
)
from shared.api_models import APIResponse, ValidationAPIError

router = APIRouter(prefix="/slack", tags=["slack-api"])


def get_slack_controller() -> SlackAPIController:
    """Dependency to get Slack API controller."""
    return SlackAPIController()


@router.get("/users/{identifier}")
async def get_user(
    identifier: str,
    controller: SlackAPIController = Depends(get_slack_controller)
) -> APIResponse:
    """
    Get a Slack user by identifier (email or user ID).
    
    Args:
        identifier: User email or Slack user ID (e.g., U1234567890)
        
    Returns:
        User information including ID, name, email, and profile details
        
    Raises:
        400: Invalid identifier format
        404: User not found
        500: Internal server error
    """
    try:
        return await controller.get_user(identifier)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{identifier}")
async def get_group(
    identifier: str,
    controller: SlackAPIController = Depends(get_slack_controller)
) -> APIResponse:
    """
    Get a Slack group by identifier (group ID or name).
    
    Args:
        identifier: Group ID (e.g., S1234567890) or group name
        
    Returns:
        Group information including ID, name, description, and member count
        
    Raises:
        400: Invalid identifier format
        404: Group not found
        500: Internal server error
    """
    try:
        return await controller.get_group(identifier)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{identifier}")
async def get_channel(
    identifier: str,
    controller: SlackAPIController = Depends(get_slack_controller)
) -> APIResponse:
    """
    Get a Slack channel by identifier (channel ID or name).
    
    Args:
        identifier: Channel ID (e.g., C1234567890) or channel name (with or without #)
        
    Returns:
        Channel information including ID, name, topic, purpose, and member count
        
    Raises:
        400: Invalid identifier format
        404: Channel not found
        500: Internal server error
    """
    try:
        return await controller.get_channel(identifier)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages")
async def send_message(
    message_request: SlackMessageRequest,
    controller: SlackAPIController = Depends(get_slack_controller)
) -> APIResponse:
    """
    Send a message to a Slack channel.
    
    Args:
        message_request: Message details including channel, text, and optional thread_ts
        
    Returns:
        Message timestamp and channel information
        
    Raises:
        400: Invalid message format or channel identifier
        500: Internal server error
    """
    try:
        return await controller.send_message(message_request)
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups/{group_id}/members")
async def add_user_to_group(
    group_id: str,
    user_id: str,
    controller: SlackAPIController = Depends(get_slack_controller)
) -> APIResponse:
    """
    Add a user to a Slack group.
    
    Args:
        group_id: Group ID (e.g., S1234567890) or group name
        user_id: User ID (e.g., U1234567890) or user email
        
    Returns:
        Success confirmation
        
    Raises:
        400: Invalid identifier format
        404: Group or user not found
        500: Internal server error
    """
    try:
        user_group_request = SlackUserGroupRequest(user_id=user_id, group_id=group_id)
        # Note: This would need to be implemented in the controller
        # For now, return a placeholder response
        return APIResponse(
            success=True,
            message="User group operation not yet implemented",
            data={"user_id": user_id, "group_id": group_id}
        )
    except ValidationAPIError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for Slack API."""
    return {"status": "healthy", "service": "slack-api"}