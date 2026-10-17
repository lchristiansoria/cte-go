from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.models import CPEDraft
from ctg_go.modules.gestions.assistant import request_assistant_reply
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
        .order_by(GestionMessage.created_at.asc(), GestionMessage.id.asc())
    ).all()
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
        )
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

    user_message = GestionMessage(
        organization_id=actor.organization_id,
        gestion_id=gestion.id,
        actor_user_id=actor.id,
        role="user",
        content=payload.content.strip(),
        attachment_name=payload.attachment.filename if payload.attachment else None,
        attachment_media_type=payload.attachment.media_type if payload.attachment else None,
    )
    assistant_message = GestionMessage(
        organization_id=actor.organization_id,
        gestion_id=gestion.id,
        actor_user_id=None,
        role="assistant",
        content=reply,
        suggestions_json=suggestions,
    )
    db.add_all([user_message, assistant_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return [_message_response(user_message), _message_response(assistant_message)]
