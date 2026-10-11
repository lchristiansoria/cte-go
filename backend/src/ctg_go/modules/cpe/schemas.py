from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CPECreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    payload_json: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", min_length=1, max_length=24)


class CPEPatchRequest(BaseModel):
    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    payload_json: dict[str, Any] | None = None
    status: str | None = Field(default=None, min_length=1, max_length=24)


class CPEReassignRequest(BaseModel):
    new_responsible_user_id: UUID
    reason: str = Field(min_length=3, max_length=512)


class CPEResponse(BaseModel):
    id: UUID
    organization_id: UUID
    gestion_id: UUID
    title: str
    payload_json: dict[str, Any]
    status: str
    created_by_user_id: UUID
    responsible_user_id: UUID
    version: int

    model_config = {"from_attributes": True}


class CPEReassignmentResponse(BaseModel):
    id: UUID
    cpe_draft_id: UUID
    actor_user_id: UUID
    previous_responsible_user_id: UUID
    new_responsible_user_id: UUID
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
