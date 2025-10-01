from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel


class ShopifyResponseKind(str, Enum):
    OK = "OK"
    NO_CONTENT = "NO_CONTENT"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_ACCEPTABLE = "NOT_ACCEPTABLE"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    MULTI_STATUS = "MULTI_STATUS"
    SERVER_ERROR = "SERVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"


class ShopifyResponse(BaseModel):
    success: bool
    kind: ShopifyResponseKind
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    attempts: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "success": self.success,
            "kind": self.kind,
        }
        if self.message is not None:
            out["message"] = self.message
        if self.data is not None:
            out["data"] = self.data
        if self.attempts is not None:
            out["attempts"] = self.attempts
        return out


    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def Success(
        cls,
        *,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> "ShopifyResponse":
        return cls(
            success=True,
            kind=ShopifyResponseKind.OK,
            data=data,
            message=message,
        )

    @classmethod 
    def NoContent(
        cls,
        *,
        message: Optional[str] = "Query succeeded but returned no records",
        data: Optional[Dict[str, Any]] = None,
    ) -> "ShopifyResponse":
        return cls(
            success=True,
            kind=ShopifyResponseKind.NO_CONTENT,
            message=message,
            data=data,
        )

    @classmethod
    def Error(
        cls,
        *,
        kind: ShopifyResponseKind,
        errors: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> "ShopifyResponse":
    #TODO: parse the errors depending on the possible responses
        return cls(
            success=False,
            kind=kind,
            message=errors,
            data=data,
        )


