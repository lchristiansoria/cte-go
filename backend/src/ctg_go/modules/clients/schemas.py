from pydantic import BaseModel, Field
from uuid import UUID


class ClientCreateRequest(BaseModel):
    cuit: str = Field(min_length=11, max_length=11)
    business_name: str = Field(min_length=1, max_length=255)
    alias: str | None = Field(default=None, max_length=255)


class ClientResponse(BaseModel):
    id: UUID
    organization_id: UUID
    cuit: str
    business_name: str
    alias: str | None = None

    model_config = {"from_attributes": True}
