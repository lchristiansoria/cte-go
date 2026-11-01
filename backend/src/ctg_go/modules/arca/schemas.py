from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArcaCuitCreateRequest(BaseModel):
    cuit: str = Field(pattern=r"^\d{11}$")
    label: str | None = Field(default=None, max_length=255)


class ArcaCuitGrantsRequest(BaseModel):
    user_ids: list[UUID]


class ArcaCuitSyncRequest(BaseModel):
    datasets: list[str] | None = None


class ArcaCuitResponse(BaseModel):
    id: UUID
    cuit: str
    label: str | None
    environment: str
    delegation_status: str
    last_checked_at: datetime | None
    last_verified_at: datetime | None
    last_error_kind: str | None
    last_errors: list[dict[str, Any]]
    user_ids: list[UUID] | None = None
