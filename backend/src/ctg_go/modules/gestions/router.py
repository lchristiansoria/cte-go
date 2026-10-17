from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.models import CPEDraft
from ctg_go.modules.cpe.schemas import CPEResponse
from ctg_go.modules.gestions.assistant import CPE_FIELDS, request_assistant_reply
from ctg_go.modules.gestions.models import Gestion, GestionMessage
from ctg_go.modules.gestions.schemas import (
    GestionCreateRequest,
    GestionMessageCreateRequest,
    GestionMessageResponse,
    GestionResponse,
)
from ctg_go.modules.gestions.use_cases import CreateGestionUseCase, ListGestionsUseCase
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_operator_or_admin

router = APIRouter(prefix="/api/v1/gestions", tags=["gestions"])


@router.get("", response_model=list[GestionResponse])
def list_gestions(
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[GestionResponse]:
    gestions = ListGestionsUseCase(db).execute(actor)
    return [GestionResponse.model_validate(gestion) for gestion in gestions]


@router.post("", response_model=GestionResponse, status_code=201)
def create_gestion(
    payload: GestionCreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> GestionResponse:
    gestion = CreateGestionUseCase(db, AuditService(db)).execute(actor, payload)
    return GestionResponse.model_validate(gestion)


def _get_gestion(db: Session, actor: User, gestion_id) -> Gestion:
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


@router.get("/{gestion_id}/messages", response_model=list[GestionMessageResponse])
def list_messages(
    gestion_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[GestionMessageResponse]:
    gestion = _get_gestion(db, actor, gestion_id)
    messages = db.scalars(
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


@router.post("/{gestion_id}/messages", response_model=list[GestionMessageResponse], status_code=201)
def create_message(
    gestion_id: UUID,
    payload: GestionMessageCreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[GestionMessageResponse]:
    gestion = _get_gestion(db, actor, gestion_id)
    cpes = db.scalars(
        select(CPEDraft).where(
            CPEDraft.organization_id == actor.organization_id,
            CPEDraft.gestion_id == gestion.id,
        ).where(CPEDraft.status == "draft")
    ).all()
    cpe_context = [
        {
            "id": str(cpe.id),
            "title": cpe.title,
            "status": cpe.status,
            "fields": cpe.payload_json.get("cpe", {}),
        }
        for cpe in cpes
    ]
    history = db.scalars(
        select(GestionMessage)
        .where(
            GestionMessage.organization_id == actor.organization_id,
            GestionMessage.gestion_id == gestion.id,
        )
        .order_by(GestionMessage.created_at.desc(), GestionMessage.id.desc())
        .limit(12)
    ).all()
    history.reverse()
    messages = [{"role": item.role, "content": item.content} for item in history]
    reply, suggestions = request_assistant_reply(payload, messages=messages, cpes=cpe_context)

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
    db.add_all([user_message, assistant_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return [_message_response(user_message), _message_response(assistant_message)]


@router.post(
    "/{gestion_id}/messages/{message_id}/suggestions/{suggestion_index}/apply",
    response_model=CPEResponse,
)
def apply_suggestion(
    gestion_id: UUID,
    message_id: UUID,
    suggestion_index: int,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CPEResponse:
    gestion = _get_gestion(db, actor, gestion_id)
    message = db.scalar(
        select(GestionMessage).where(
            GestionMessage.id == message_id,
            GestionMessage.organization_id == actor.organization_id,
            GestionMessage.gestion_id == gestion.id,
            GestionMessage.role == "assistant",
        ).with_for_update()
    )
    if message is None or suggestion_index < 0 or suggestion_index >= len(message.suggestions_json):
        raise ApiError(status_code=404, code="not_found", message="Suggestion not found.")
    suggestions = [dict(item) for item in message.suggestions_json]
    suggestion = suggestions[suggestion_index]

    if suggestion.get("applied"):
        cpe = db.scalar(
            select(CPEDraft).where(
                CPEDraft.id == UUID(suggestion["applied_cpe_id"]),
                CPEDraft.organization_id == actor.organization_id,
                CPEDraft.gestion_id == gestion.id,
            )
        )
        if cpe is not None:
            return CPEResponse.model_validate(cpe)
        raise ApiError(status_code=409, code="suggestion_already_applied", message="Suggestion was already applied.")

    fields = suggestion.get("fields", {})
    if not fields or any(key not in CPE_FIELDS for key in fields):
        raise ApiError(status_code=422, code="validation_error", message="Suggestion contains invalid CPE fields.")
    cpe_id = UUID(suggestion["cpe_id"]) if suggestion.get("cpe_id") else None
    if cpe_id:
        cpe = db.scalar(
            select(CPEDraft)
            .where(
                CPEDraft.id == cpe_id,
                CPEDraft.organization_id == actor.organization_id,
                CPEDraft.gestion_id == gestion.id,
            )
            .with_for_update()
        )
        if cpe is None:
            raise ApiError(status_code=404, code="not_found", message="Draft CPE not found.")
        if cpe.status != "draft" or cpe.responsible_user_id != actor.id:
            raise ApiError(status_code=409, code="draft_not_editable", message="Draft CPE is not editable by this user.")
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
            title=suggestion["title"],
            payload_json={
                "cpe": fields,
                "field_status": {key: "ai" for key in fields},
            },
            status="draft",
            created_by_user_id=actor.id,
            responsible_user_id=actor.id,
            version=1,
        )
        db.add(cpe)
        db.flush()
        action = "cpe.created_from_assistant_suggestion"

    suggestions[suggestion_index].update({"applied": True, "applied_cpe_id": str(cpe.id)})
    message.suggestions_json = suggestions
    AuditService(db).log(
        actor=actor,
        entity_type="cpe_draft",
        entity_id=str(cpe.id),
        action=action,
        details={"gestion_id": str(gestion.id), "fields": sorted(fields)},
    )
    db.commit()
    db.refresh(cpe)
    return CPEResponse.model_validate(cpe)
