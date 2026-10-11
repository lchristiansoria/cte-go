from uuid import UUID

from pydantic import BaseModel, Field


class GestionCreateRequest(BaseModel):
    client_id: UUID
    code: str = Field(min_length=1, max_length=64)
    status: str = Field(default="open", min_length=1, max_length=32)


class GestionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    client_id: UUID
    code: str
    status: str
    created_by_user_id: UUID

    model_config = {"from_attributes": True}
