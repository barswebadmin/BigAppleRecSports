from typing import Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel


class ShopifyResponseKind(str, Enum):
    OK = "OK"
    NO_CONTENT = "NO_CONTENT"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    NOT_FOUND = "NOT_FOUND"
    SERVER_ERROR = "SERVER_ERROR"


class ShopifyResponse(BaseModel):
    status_code: int
    success: bool
    kind: ShopifyResponseKind
    message: Optional[str] = None
    order: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None
    attempts: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "status_code": self.status_code,
            "success": self.success,
            "kind": self.kind,
        }
        if self.message is not None:
            out["message"] = self.message
        if self.order is not None:
            out["order"] = self.order
        if self.raw is not None:
            out["raw"] = self.raw
        if self.attempts is not None:
            out["attempts"] = self.attempts
        return out

    @classmethod
    def from_graphql(cls, data: Dict[str, Any], http_status: int) -> "ShopifyResponse":
        if http_status == 401:
            return cls.Error(message=str(data.get("errors")), status_code=401, raw=data)
        if data.get("errors"):
            return cls.Error(message=str(data.get("errors")), status_code=400, raw=data)
        edges = data.get("data", {}).get("orders", {}).get("edges", [])
        if edges:
            order_node = edges[0].get("node", {})
            return cls.Success(order=order_node, raw=data, status_code=http_status)
        return cls.NoContent(message="Order not found", raw=data)

    @classmethod
    def from_error(cls, message: str, status_code: int) -> "ShopifyResponse":
        return cls.Error(message=message, status_code=status_code)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------
    @classmethod
    def Success(
        cls,
        *,
        order: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
        status_code: int = 200,
        raw: Optional[Dict[str, Any]] = None,
    ) -> "ShopifyResponse":
        return cls(
            status_code=status_code,
            success=True,
            kind=ShopifyResponseKind.OK if status_code == 200 else ShopifyResponseKind.NO_CONTENT,
            message=message,
            order=order,
            raw=raw,
        )

    @classmethod
    def NoContent(
        cls,
        *,
        message: Optional[str] = "Order not found",
        raw: Optional[Dict[str, Any]] = None,
    ) -> "ShopifyResponse":
        return cls(
            status_code=204,
            success=True,
            kind=ShopifyResponseKind.NO_CONTENT,
            message=message,
            order=None,
            raw=raw,
        )

    @classmethod
    def Error(
        cls,
        *,
        message: str,
        status_code: int = 500,
        raw: Optional[Dict[str, Any]] = None,
    ) -> "ShopifyResponse":
        if status_code == 401:
            kind = ShopifyResponseKind.UNAUTHORIZED
        elif status_code == 404:
            kind = ShopifyResponseKind.NOT_FOUND
        elif status_code == 400:
            kind = ShopifyResponseKind.BAD_REQUEST
        elif status_code == 204:
            # Treat as no-content success if used mistakenly
            return cls.NoContent(message=message, raw=raw)
        else:
            kind = ShopifyResponseKind.SERVER_ERROR
        return cls(
            status_code=status_code,
            success=False,
            kind=kind,
            message=message,
            raw=raw,
        )


