"""Gmail SendAs settings model for signature retrieval."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class SecurityMode(Enum):
    """SMTP security protocol."""
    
    security_mode_unspecified = "securityModeUnspecified"
    none = "none"
    ssl = "ssl"
    starttls = "starttls"


class VerificationStatus(Enum):
    """Send-as alias verification state."""
    
    verification_status_unspecified = "verificationStatusUnspecified"
    accepted = "accepted"
    pending = "pending"


class SmtpMsa(BaseModel):
    """Optional SMTP relay configuration for custom send-as aliases."""
    
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    security_mode: Annotated[SecurityMode | None, Field(alias="securityMode")] = None


class SendAs(BaseModel):
    """Gmail send-as alias settings."""
    
    send_as_email: Annotated[str | None, Field(alias="sendAsEmail")] = None
    display_name: Annotated[str | None, Field(alias="displayName")] = None
    reply_to_address: Annotated[str | None, Field(alias="replyToAddress")] = None
    signature: str | None = None
    is_primary: Annotated[bool | None, Field(alias="isPrimary")] = None
    is_default: Annotated[bool | None, Field(alias="isDefault")] = None
    treat_as_alias: Annotated[bool | None, Field(alias="treatAsAlias")] = None
    smtp_msa: Annotated[SmtpMsa | None, Field(alias="smtpMsa")] = None
    verification_status: Annotated[VerificationStatus | None, Field(alias="verificationStatus")] = None
