from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.schemas import CPEResponse
from ctg_go.modules.gestions.schemas import (
    GestionCreateRequest,
    GestionMessageCreateRequest,
    GestionMessageResponse,
    GestionResponse,
)
from ctg_go.modules.gestions.use_cases import (
    ApplyGestionSuggestionUseCase,
    CreateGestionMessageUseCase,
    CreateGestionUseCase,
    ListGestionMessagesUseCase,
    ListGestionsUseCase,
)
from ctg_go.modules.identity.models import User

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


@router.get("/{gestion_id}/messages", response_model=list[GestionMessageResponse])
def list_messages(
    gestion_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[GestionMessageResponse]:
    return ListGestionMessagesUseCase(db).execute(actor, gestion_id)


@router.post("/{gestion_id}/messages", response_model=list[GestionMessageResponse], status_code=201)
def create_message(
    gestion_id: UUID,
    payload: GestionMessageCreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[GestionMessageResponse]:
    return CreateGestionMessageUseCase(db).execute(actor, gestion_id, payload)


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
    cpe = ApplyGestionSuggestionUseCase(db, AuditService(db)).execute(
        actor,
        gestion_id,
        message_id,
        suggestion_index,
    )
    return CPEResponse.model_validate(cpe)
