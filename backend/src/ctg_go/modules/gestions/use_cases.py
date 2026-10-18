from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.models import Client
from ctg_go.modules.cpe.models import CPEDraft
from ctg_go.modules.gestions.assistant import CPE_FIELDS, request_assistant_reply
from ctg_go.modules.gestions.models import Gestion, GestionMessage
from ctg_go.modules.gestions.schemas import (
    CpeSuggestion,
    GestionCreateRequest,
    GestionMessageCreateRequest,
    GestionMessageResponse,
)
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


def _get_gestion(db: Session, actor: User, gestion_id: UUID) -> Gestion:
    assert_operator_or_admin(actor)
    gestion = db.scalar(
        select(Gestion).where(
            Gestion.id == gestion_id,
            Gestion.organization_id == actor.organization_id,
        )
    )
    if gestion is None:
        raise ApiError(status_code=404, code="not_found", message="Gestion not found.")
    return gestion


def _message_response(message: GestionMessage) -> GestionMessageResponse:
    return GestionMessageResponse(
        id=message.id,
        gestion_id=message.gestion_id,
        role=message.role,
        content=message.content,
        attachment_name=message.attachment_name,
        attachment_media_type=message.attachment_media_type,
        suggestions=message.suggestions_json,
        created_at=message.created_at,
    )


class ListGestionMessagesUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, actor: User, gestion_id: UUID) -> list[GestionMessageResponse]:
        gestion = _get_gestion(self.db, actor, gestion_id)
        messages = self.db.scalars(
            select(GestionMessage)
            .where(
                GestionMessage.organization_id == actor.organization_id,
                GestionMessage.gestion_id == gestion.id,
            )
            .order_by(GestionMessage.created_at.desc(), GestionMessage.id.desc())
            .limit(100)
        ).all()
        messages.reverse()
        return [_message_response(message) for message in messages]


class CreateGestionMessageUseCase:
    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        actor: User,
        gestion_id: UUID,
        payload: GestionMessageCreateRequest,
    ) -> list[GestionMessageResponse]:
        gestion = _get_gestion(self.db, actor, gestion_id)
        cpes = self.db.scalars(
            select(CPEDraft)
            .where(
                CPEDraft.organization_id == actor.organization_id,
                CPEDraft.gestion_id == gestion.id,
                CPEDraft.responsible_user_id == actor.id,
                CPEDraft.status == "draft",
            )
            .limit(50)
        ).all()
        cpe_context = [
            {
                "id": str(cpe.id),
                "title": cpe.title,
                "status": cpe.status,
                "version": cpe.version,
                "fields": cpe.payload_json.get("cpe", {}),
            }
            for cpe in cpes
        ]
        history = self.db.scalars(
            select(GestionMessage)
            .where(
                GestionMessage.organization_id == actor.organization_id,
                GestionMessage.gestion_id == gestion.id,
            )
            .order_by(GestionMessage.created_at.desc(), GestionMessage.id.desc())
            .limit(12)
        ).all()
        history.reverse()
        conversation = [{"role": item.role, "content": item.content} for item in history]
        reply, suggestions = request_assistant_reply(payload, messages=conversation, cpes=cpe_context)

        created_at = datetime.now(timezone.utc)
        user_message = GestionMessage(
            organization_id=actor.organization_id,
            gestion_id=gestion.id,
            actor_user_id=actor.id,
            role="user",
            content=payload.content.strip(),
            attachment_name=payload.attachment.filename if payload.attachment else None,
            attachment_media_type=payload.attachment.media_type if payload.attachment else None,
            created_at=created_at,
        )
        assistant_message = GestionMessage(
            organization_id=actor.organization_id,
            gestion_id=gestion.id,
            actor_user_id=None,
            role="assistant",
            content=reply,
            suggestions_json=suggestions,
            created_at=created_at + timedelta(microseconds=1),
        )
        self.db.add_all([user_message, assistant_message])
        self.db.commit()
        self.db.refresh(user_message)
        self.db.refresh(assistant_message)
        return [_message_response(user_message), _message_response(assistant_message)]


class ApplyGestionSuggestionUseCase:
    def __init__(self, db: Session, audit: AuditService) -> None:
        self.db = db
        self.audit = audit

    def execute(
        self,
        actor: User,
        gestion_id: UUID,
        message_id: UUID,
        suggestion_index: int,
    ) -> CPEDraft:
        gestion = _get_gestion(self.db, actor, gestion_id)
        message = self.db.scalar(
            select(GestionMessage)
            .where(
                GestionMessage.id == message_id,
                GestionMessage.organization_id == actor.organization_id,
                GestionMessage.gestion_id == gestion.id,
                GestionMessage.role == "assistant",
            )
            .with_for_update()
        )
        if message is None or suggestion_index < 0 or suggestion_index >= len(message.suggestions_json):
            raise ApiError(status_code=404, code="not_found", message="Suggestion not found.")
        suggestions = [dict(item) for item in message.suggestions_json]
        suggestion = CpeSuggestion.model_validate(suggestions[suggestion_index])

        if suggestion.applied:
            cpe = self.db.scalar(
                select(CPEDraft).where(
                    CPEDraft.id == suggestion.applied_cpe_id,
                    CPEDraft.organization_id == actor.organization_id,
                    CPEDraft.gestion_id == gestion.id,
                )
            )
            if cpe is not None:
                return cpe
            raise ApiError(status_code=409, code="suggestion_already_applied", message="Suggestion was already applied.")

        fields = suggestion.fields
        if not fields or any(key not in CPE_FIELDS for key in fields):
            raise ApiError(status_code=422, code="validation_error", message="Suggestion contains invalid CPE fields.")
        if suggestion.cpe_id:
            cpe = self.db.scalar(
                select(CPEDraft)
                .where(
                    CPEDraft.id == suggestion.cpe_id,
                    CPEDraft.organization_id == actor.organization_id,
                    CPEDraft.gestion_id == gestion.id,
                )
                .with_for_update()
            )
            if cpe is None:
                raise ApiError(status_code=404, code="not_found", message="Draft CPE not found.")
            if cpe.status != "draft" or cpe.responsible_user_id != actor.id:
                raise ApiError(status_code=409, code="draft_not_editable", message="Draft CPE is not editable by this user.")
            if cpe.version != suggestion.expected_version:
                raise ApiError(
                    status_code=409,
                    code="version_conflict",
                    message="Draft changed since the assistant prepared this suggestion. Review it again before applying.",
                )
            payload = dict(cpe.payload_json)
            values = dict(payload.get("cpe", {}))
            values.update(fields)
            field_status = dict(payload.get("field_status", {}))
            field_status.update({key: "ai" for key in fields})
            payload.update({"cpe": values, "field_status": field_status})
            cpe.payload_json = payload
            cpe.version += 1
            action = "cpe.assistant_suggestion_applied"
        else:
            cpe = CPEDraft(
                organization_id=actor.organization_id,
                gestion_id=gestion.id,
                title=suggestion.title,
                payload_json={
                    "cpe": fields,
                    "field_status": {key: "ai" for key in fields},
                },
                status="draft",
                created_by_user_id=actor.id,
                responsible_user_id=actor.id,
                version=1,
            )
            self.db.add(cpe)
            self.db.flush()
            action = "cpe.created_from_assistant_suggestion"

        suggestions[suggestion_index].update({"applied": True, "applied_cpe_id": str(cpe.id)})
        message.suggestions_json = suggestions
        self.audit.log(
            actor=actor,
            entity_type="cpe_draft",
            entity_id=str(cpe.id),
            action=action,
            details={"gestion_id": str(gestion.id), "fields": sorted(fields)},
        )
        self.db.commit()
        self.db.refresh(cpe)
        return cpe
