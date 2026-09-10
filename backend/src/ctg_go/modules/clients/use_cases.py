from __future__ import annotations

from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.models import Client
from ctg_go.modules.clients.schemas import ClientCreateRequest
from ctg_go.modules.clients.services import scoped_clients_query
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_operator_or_admin


class ListClientsUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User) -> list[Client]:
        assert_operator_or_admin(actor)
        return list(self.db.scalars(scoped_clients_query(actor.organization_id)).all())


class CreateClientUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, payload: ClientCreateRequest) -> Client:
        assert_operator_or_admin(actor)
        exists = self.db.scalar(
            scoped_clients_query(actor.organization_id).where(Client.cuit == payload.cuit).limit(1)
        )
        if exists is not None:
            raise ApiError(
                status_code=422,
                code="validation_error",
                message="Client CUIT already exists.",
                field_errors=[{"field": "cuit", "message": "already exists"}],
            )

        client = Client(
            organization_id=actor.organization_id,
            cuit=payload.cuit,
            business_name=payload.business_name,
            alias=payload.alias,
        )
        self.db.add(client)
        self.db.flush()

        self.audit.log(
            actor=actor,
            entity_type="client",
            entity_id=str(client.id),
            action="client.created",
            details={"cuit": payload.cuit},
        )
        self.db.commit()
        self.db.refresh(client)
        return client
