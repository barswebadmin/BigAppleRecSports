"""
Clean Request Models for API Operations

Direct request models that replace the builder pattern.
Each model validates inputs and provides a clean interface for API calls.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import Field, field_validator

from shared_utilities.model_config import ApiModel

logger = logging.getLogger(__name__)


class HTTPMethod(str, Enum):
    """HTTP methods supported by API requests"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class BaseAPIRequest(ApiModel):
    """Base class for all API requests with class attributes for HTTP details"""
    
    # Class attributes - override in subclasses
    method: Optional[HTTPMethod] = None
    endpoint: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None


# ============================================================================
# GOOGLE API REQUESTS
# ============================================================================

# Google API requests have been moved back to backend/modules/integrations/google/models/requests.py
# since everything will route through the backend. The CLI should import from there.


# ============================================================================
# SLACK API REQUESTS
# ============================================================================


# ============================================================================
# SLACK API REQUESTS
# ============================================================================

class GetSlackUserRequest(BaseAPIRequest):
    """Request to get a Slack user"""
    
    # HTTP request configuration
    method: HTTPMethod = HTTPMethod.GET
    headers: Dict[str, str] = {
        'Accept': 'application/json',
        'User-Agent': 'BARS-API-Client/1.0'
    }
    
    # Request data fields
    identifier: str = Field(..., description="User ID or email")

    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v):
        """Validate user identifier"""
        if not v or not v.strip():
            raise ValueError('User identifier cannot be empty')
        return v.strip()

    @property
    def endpoint(self) -> str:
        """Generate endpoint with identifier"""
        return f"/slack/users/{self.identifier}"


class ListSlackUsersRequest(BaseAPIRequest):
    """Request to list Slack users"""
    
    # HTTP request configuration
    method: HTTPMethod = HTTPMethod.GET
    endpoint: str = "/slack/users"
    headers: Dict[str, str] = {
        'Accept': 'application/json',
        'User-Agent': 'BARS-API-Client/1.0'
    }
    
    # Request data fields
    limit: Optional[int] = Field(default=50, ge=1, le=1000, description="Items per page")
    offset: Optional[int] = Field(default=0, ge=0, description="Offset for pagination")

    @property
    def params(self) -> Dict[str, str]:
        """Generate query parameters from instance data"""
        params_data = {}
        if self.limit is not None:
            params_data["limit"] = str(self.limit)
        if self.offset is not None:
            params_data["offset"] = str(self.offset)
        return params_data


class GetSlackGroupRequest(BaseAPIRequest):
    """Request to get a Slack group"""
    
    # HTTP request configuration
    method: HTTPMethod = HTTPMethod.GET
    headers: Dict[str, str] = {
        'Accept': 'application/json',
        'User-Agent': 'BARS-API-Client/1.0'
    }
    
    # Request data fields
    identifier: str = Field(..., description="Group ID or name")

    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v):
        """Validate group identifier"""
        if not v or not v.strip():
            raise ValueError('Group identifier cannot be empty')
        return v.strip()

    @property
    def endpoint(self) -> str:
        """Generate endpoint with identifier"""
        return f"/slack/groups/{self.identifier}"


class SendSlackMessageRequest(BaseAPIRequest):
    """Request to send a Slack message"""
    
    # HTTP request configuration
    method: HTTPMethod = HTTPMethod.POST
    endpoint: str = "/slack/messages"
    headers: Dict[str, str] = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'BARS-API-Client/1.0'
    }
    
    # Request data fields
    channel: str = Field(..., description="Channel ID or name")
    text: str = Field(..., min_length=1, description="Message text")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        """Validate message text"""
        if not v or not v.strip():
            raise ValueError('Message text cannot be empty')
        if len(v) > 4000:
            raise ValueError('Message text cannot exceed 4000 characters')
        return v.strip()

    @property
    def body(self) -> Dict[str, Any]:
        """Generate request body from instance data"""
        body_data = {
            "channel": self.channel,
            "text": self.text
        }
        if self.thread_ts:
            body_data["thread_ts"] = self.thread_ts
        return body_data


# ============================================================================
# REQUEST EXECUTION HELPER
# ============================================================================

class APIRequestExecutor:
    """Helper class to execute API requests using HTTPXClient"""
    
    def __init__(self, client):
        """Initialize with an HTTPXClient instance"""
        self.client = client
    
    async def execute_async(self, request: BaseAPIRequest) -> Dict[str, Any]:
        """Execute request asynchronously"""
        method = request.method.value
        endpoint = request.endpoint
        headers = request.headers
        params = getattr(request, 'params', None)
        body = getattr(request, 'body', None)
        
        if method == "GET":
            response = await self.client.get(endpoint, params=params, headers=headers)
            return response.json()
        if method == "POST":
            if body:
                response = await self.client.post(endpoint, json=body, headers=headers)
            else:
                response = await self.client.post(endpoint, params=params, headers=headers)
            return response.json()
        if method == "PUT":
            if body:
                response = await self.client.put(endpoint, json=body, headers=headers)
            else:
                response = await self.client.put(endpoint, params=params, headers=headers)
            return response.json()
        if method == "DELETE":
            response = await self.client.delete(endpoint, params=params, headers=headers)
            return response.json()
        
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    def execute_sync(self, request: BaseAPIRequest) -> Dict[str, Any]:
        """Execute request synchronously"""
        method = request.method.value
        endpoint = request.endpoint
        headers = request.headers
        params = getattr(request, 'params', None)
        body = getattr(request, 'body', None)
        
        if method == "GET":
            response = self.client.get(endpoint, params=params, headers=headers)
            return response.json()
        if method == "POST":
            if body:
                response = self.client.post(endpoint, json=body, headers=headers)
            else:
                response = self.client.post(endpoint, params=params, headers=headers)
            return response.json()
        if method == "PUT":
            if body:
                response = self.client.put(endpoint, json=body, headers=headers)
            else:
                response = self.client.put(endpoint, params=params, headers=headers)
            return response.json()
        if method == "DELETE":
            response = self.client.delete(endpoint, params=params, headers=headers)
            return response.json()
        
        raise ValueError(f"Unsupported HTTP method: {method}")