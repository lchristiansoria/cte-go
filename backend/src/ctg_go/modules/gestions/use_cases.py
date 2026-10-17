from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.models import Client
from ctg_go.modules.gestions.models import Gestion
from ctg_go.modules.gestions.schemas import GestionCreateRequest
from ctg_go.modules.gestions.services import scoped_gestions_query
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_operator_or_admin


class ListGestionsUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User) -> list[Gestion]:
        assert_operator_or_admin(actor)
        return list(self.db.scalars(scoped_gestions_query(actor.organization_id)).all())


class CreateGestionUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, payload: GestionCreateRequest) -> Gestion:
        assert_operator_or_admin(actor)
        client = self.db.scalar(
            select(Client).where(
                Client.id == payload.client_id,
                Client.organization_id == actor.organization_id,
            )
        )
        if client is None:
            raise ApiError(status_code=404, code="not_found", message="Client not found.")

        code = f"GES-{uuid4().hex.upper()}"
        gestion = Gestion(
            organization_id=actor.organization_id,
            client_id=client.id,
            code=code,
            status=payload.status,
            created_by_user_id=actor.id,
        )
        self.db.add(gestion)
        self.db.flush()

        self.audit.log(
            actor=actor,
            entity_type="gestion",
            entity_id=str(gestion.id),
            action="gestion.created",
            details={"client_id": str(client.id), "code": code},
        )
        self.db.commit()
        self.db.refresh(gestion)
        return gestion
