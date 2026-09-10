from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.models import CPEDraft, CPEReassignment
from ctg_go.modules.cpe.schemas import CPECreateRequest, CPEPatchRequest, CPEReassignRequest
from ctg_go.modules.cpe.services import (
    has_blocking_operation_query,
    scoped_cpes_query,
)
from ctg_go.modules.gestions.models import Gestion
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_operator_or_admin


class ScopedCPEMixin:
    def get_scoped_cpe(self, db: Session, actor: User, cpe_id: UUID) -> CPEDraft:
        cpe = db.scalar(scoped_cpes_query(actor.organization_id).where(CPEDraft.id == cpe_id))
        if cpe is None:
            raise ApiError(status_code=404, code="not_found", message="CPE not found.")
        return cpe


class ListGestionCPEsUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, gestion_id: UUID) -> list[CPEDraft]:
        assert_operator_or_admin(actor)
        gestion = self.db.scalar(
            select(Gestion).where(
                Gestion.id == gestion_id,
                Gestion.organization_id == actor.organization_id,
            )
        )
        if gestion is None:
            raise ApiError(status_code=404, code="not_found", message="Gestion not found.")
        return list(
            self.db.scalars(
                scoped_cpes_query(actor.organization_id).where(CPEDraft.gestion_id == gestion.id)
            ).all()
        )


class CreateCPEUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, gestion_id: UUID, payload: CPECreateRequest) -> CPEDraft:
        assert_operator_or_admin(actor)
        gestion = self.db.scalar(
            select(Gestion).where(
                Gestion.id == gestion_id,
                Gestion.organization_id == actor.organization_id,
            )
        )
        if gestion is None:
            raise ApiError(status_code=404, code="not_found", message="Gestion not found.")

        cpe = CPEDraft(
            organization_id=actor.organization_id,
            gestion_id=gestion.id,
            title=payload.title,
            payload_json=payload.payload_json,
            status=payload.status,
            created_by_user_id=actor.id,
            responsible_user_id=actor.id,
            version=1,
        )
        self.db.add(cpe)
        self.db.flush()
        self.audit.log(
            actor=actor,
            entity_type="cpe_draft",
            entity_id=str(cpe.id),
            action="cpe.created",
            details={"gestion_id": str(gestion.id)},
        )
        self.db.commit()
        self.db.refresh(cpe)
        return cpe


class GetCPEUseCase(ScopedCPEMixin):
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, cpe_id: UUID) -> CPEDraft:
        assert_operator_or_admin(actor)
        return self.get_scoped_cpe(self.db, actor, cpe_id)


class UpdateCPEUseCase(ScopedCPEMixin):
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, cpe_id: UUID, payload: CPEPatchRequest) -> CPEDraft:
        assert_operator_or_admin(actor)
        cpe = self.get_scoped_cpe(self.db, actor, cpe_id)
        if cpe.responsible_user_id != actor.id:
            raise ApiError(
                status_code=403,
                code="forbidden",
                message="Only responsible user can edit this CPE.",
            )
        if cpe.version != payload.expected_version:
            raise ApiError(
                status_code=409,
                code="version_conflict",
                message="Expected version does not match current version.",
            )

        if payload.title is not None:
            cpe.title = payload.title
        if payload.payload_json is not None:
            cpe.payload_json = payload.payload_json
        if payload.status is not None:
            cpe.status = payload.status
        cpe.version += 1

        self.audit.log(
            actor=actor,
            entity_type="cpe_draft",
            entity_id=str(cpe.id),
            action="cpe.updated",
            details={"version": cpe.version},
        )
        self.db.commit()
        self.db.refresh(cpe)
        return cpe


class ReassignCPEUseCase(ScopedCPEMixin):
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(self, actor: User, cpe_id: UUID, payload: CPEReassignRequest) -> CPEDraft:
        assert_operator_or_admin(actor)
        if actor.role != "admin":
            raise ApiError(status_code=403, code="forbidden", message="Only admin can reassign CPE.")

        cpe = self.get_scoped_cpe(self.db, actor, cpe_id)
        blocking_operation = self.db.scalar(
            has_blocking_operation_query(actor.organization_id, cpe.id)
        )
        if blocking_operation is not None:
            raise ApiError(
                status_code=409,
                code="reassignment_blocked",
                message="CPE has pending official operation.",
            )

        new_responsible = self.db.scalar(
            select(User).where(
                User.id == payload.new_responsible_user_id,
                User.organization_id == actor.organization_id,
                User.is_active.is_(True),
            )
        )
        if new_responsible is None:
            raise ApiError(
                status_code=422,
                code="validation_error",
                message="Invalid responsible user.",
                field_errors=[{"field": "new_responsible_user_id", "message": "invalid user"}],
            )

        reassignment = CPEReassignment(
            organization_id=actor.organization_id,
            cpe_draft_id=cpe.id,
            actor_user_id=actor.id,
            previous_responsible_user_id=cpe.responsible_user_id,
            new_responsible_user_id=new_responsible.id,
            reason=payload.reason,
        )
        self.db.add(reassignment)
        cpe.responsible_user_id = new_responsible.id

        self.audit.log(
            actor=actor,
            entity_type="cpe_draft",
            entity_id=str(cpe.id),
            action="cpe.reassigned",
            details={
                "previous_responsible_user_id": str(reassignment.previous_responsible_user_id),
                "new_responsible_user_id": str(reassignment.new_responsible_user_id),
                "reason": payload.reason,
            },
        )
        self.db.commit()
        self.db.refresh(cpe)
        return cpe


class ListOrganizationCPEsUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, organization_id: UUID) -> list[CPEDraft]:
        assert_operator_or_admin(actor)
        if actor.organization_id != organization_id:
            raise ApiError(status_code=404, code="not_found", message="Organization not found.")
        return list(self.db.scalars(scoped_cpes_query(actor.organization_id)).all())


class ListReassignmentsUseCase(ScopedCPEMixin):
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, cpe_id: UUID) -> list[CPEReassignment]:
        assert_operator_or_admin(actor)
        self.get_scoped_cpe(self.db, actor, cpe_id)
        return list(
            self.db.scalars(
                select(CPEReassignment)
                .where(
                    CPEReassignment.organization_id == actor.organization_id,
                    CPEReassignment.cpe_draft_id == cpe_id,
                )
                .order_by(CPEReassignment.created_at.asc())
            ).all()
        )
