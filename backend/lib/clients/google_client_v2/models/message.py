"""Gmail Message models for send operations."""

from typing import Annotated

from pydantic import Base64Str, BaseModel, Field


class ClassificationLabelFieldValue(BaseModel):
    """Google Workspace classification label field value."""
    
    field_id: Annotated[str | None, Field(alias="fieldId")] = None
    selection: str | None = None


class ClassificationLabelValue(BaseModel):
    """Google Workspace classification label."""
    
    label_id: Annotated[str | None, Field(alias="labelId")] = None
    fields: list[ClassificationLabelFieldValue] | None = None


class MessagePartHeader(BaseModel):
    """Email header (name: value pair)."""
    
    name: str | None = None
    value: str | None = None


class MessagePartBody(BaseModel):
    """MIME message part body content."""
    
    attachment_id: Annotated[str | None, Field(alias="attachmentId")] = None
    size: int | None = None
    data: Base64Str | None = None


class MessagePart(BaseModel):
    """MIME message part structure."""
    
    part_id: Annotated[str | None, Field(alias="partId")] = None
    mime_type: Annotated[str | None, Field(alias="mimeType")] = None
    filename: str | None = None
    headers: list[MessagePartHeader] | None = None
    body: MessagePartBody | None = None
    parts: list["MessagePart"] | None = None


class Message(BaseModel):
    """Gmail message resource."""
    
    id: str | None = None
    thread_id: Annotated[str | None, Field(alias="threadId")] = None
    label_ids: Annotated[list[str] | None, Field(alias="labelIds")] = None
    snippet: str | None = None
    history_id: Annotated[str | None, Field(alias="historyId")] = None
    internal_date: Annotated[str | None, Field(alias="internalDate")] = None
    payload: MessagePart | None = None
    size_estimate: Annotated[int | None, Field(alias="sizeEstimate")] = None
    raw: Base64Str | None = None
    classification_label_values: Annotated[
        list[ClassificationLabelValue] | None, Field(alias="classificationLabelValues")
    ] = None
