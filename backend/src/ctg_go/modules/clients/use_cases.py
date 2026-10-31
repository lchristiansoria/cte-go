from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.models import Client
from ctg_go.modules.clients.schemas import ClientCpeResponse, ClientCreateRequest, ClientUpdateRequest
from ctg_go.modules.clients.services import get_scoped_client, scoped_clients_query
from ctg_go.modules.cpe.models import CPEDraft
from ctg_go.modules.gestions.models import Gestion
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


def _assert_cuit_available(db: Session, organization_id, cuit: str, exclude_id=None) -> None:
    query = scoped_clients_query(organization_id).where(Client.cuit == cuit)
    if exclude_id is not None:
        query = query.where(Client.id != exclude_id)
    if db.scalar(query.limit(1)) is not None:
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="Client CUIT already exists.",
            field_errors=[{"field": "cuit", "message": "already exists"}],
        )


class GetClientUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, client_id) -> Client:
        assert_operator_or_admin(actor)
        return get_scoped_client(self.db, actor.organization_id, client_id)


class UpdateClientUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, client_id, payload: ClientUpdateRequest) -> Client:
        assert_operator_or_admin(actor)
        client = get_scoped_client(self.db, actor.organization_id, client_id)
        _assert_cuit_available(self.db, actor.organization_id, payload.cuit, exclude_id=client.id)

        client.cuit = payload.cuit
        client.business_name = payload.business_name
        client.alias = payload.alias
        self.audit.log(
            actor=actor,
            entity_type="client",
            entity_id=str(client.id),
            action="client.updated",
            details={"cuit": payload.cuit},
        )
        self.db.commit()
        self.db.refresh(client)
        return client


class DeleteClientUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, client_id) -> None:
        assert_operator_or_admin(actor)
        client = get_scoped_client(self.db, actor.organization_id, client_id)
        has_gestions = self.db.scalar(
            select(Gestion.id)
            .where(Gestion.organization_id == actor.organization_id, Gestion.client_id == client.id)
            .limit(1)
        )
        if has_gestions is not None:
            raise ApiError(
                status_code=409,
                code="conflict",
                message="Client has gestiones and cannot be deleted.",
            )

        self.audit.log(
            actor=actor,
            entity_type="client",
            entity_id=str(client.id),
            action="client.deleted",
            details={"cuit": client.cuit},
        )
        self.db.delete(client)
        self.db.commit()


class ListClientCpesUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, client_id) -> list[ClientCpeResponse]:
        assert_operator_or_admin(actor)
        client = get_scoped_client(self.db, actor.organization_id, client_id)
        rows = self.db.execute(
            select(CPEDraft, Gestion.code)
            .join(
                Gestion,
                (Gestion.organization_id == CPEDraft.organization_id) & (Gestion.id == CPEDraft.gestion_id),
            )
            .where(Gestion.organization_id == actor.organization_id, Gestion.client_id == client.id)
            .order_by(CPEDraft.created_at.desc(), CPEDraft.id)
        ).all()
        return [
            ClientCpeResponse(
                id=cpe.id,
                gestion_id=cpe.gestion_id,
                gestion_code=code,
                title=cpe.title,
                status=cpe.status,
                version=cpe.version,
                responsible_user_id=cpe.responsible_user_id,
                payload_json=cpe.payload_json,
            )
            for cpe, code in rows
        ]
