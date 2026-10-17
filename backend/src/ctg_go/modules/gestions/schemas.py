from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GestionCreateRequest(BaseModel):
    client_id: UUID
    status: str = Field(default="open", min_length=1, max_length=32)


class GestionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    client_id: UUID
    code: str
    status: str
    created_by_user_id: UUID

    model_config = {"from_attributes": True}


class ChatAttachment(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(pattern=r"^image/(jpeg|png|webp)$")
    content_base64: str = Field(min_length=1, max_length=7_000_000)


class GestionMessageCreateRequest(BaseModel):
    content: str = Field(default="", max_length=8000)
    attachment: ChatAttachment | None = None


class CpeSuggestion(BaseModel):
    cpe_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    fields: dict[str, str]
    expected_version: int | None = None
    applied: bool = False
    applied_cpe_id: UUID | None = None


class GestionMessageResponse(BaseModel):
    id: UUID
    gestion_id: UUID
    role: str
    content: str
    attachment_name: str | None
    attachment_media_type: str | None
    suggestions: list[CpeSuggestion] = Field(default_factory=list)
    created_at: datetime
