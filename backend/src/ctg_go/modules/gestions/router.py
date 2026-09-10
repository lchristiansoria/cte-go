from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.gestions.schemas import GestionCreateRequest, GestionResponse
from ctg_go.modules.gestions.use_cases import CreateGestionUseCase, ListGestionsUseCase
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
