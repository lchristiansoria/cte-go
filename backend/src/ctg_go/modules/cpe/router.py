from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.schemas import (
    CPECreateRequest,
    CPEPatchRequest,
    CPEReassignmentResponse,
    CPEReassignRequest,
    CPEResponse,
)
from ctg_go.modules.cpe.use_cases import (
    CreateCPEUseCase,
    GetCPEUseCase,
    ListGestionCPEsUseCase,
    ListOrganizationCPEsUseCase,
    ListReassignmentsUseCase,
    ReassignCPEUseCase,
    UpdateCPEUseCase,
)
from ctg_go.modules.identity.models import User

router = APIRouter(tags=["cpes"])


@router.get("/api/v1/gestions/{gestion_id}/cpes", response_model=list[CPEResponse])
def list_gestion_cpes(
    gestion_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[CPEResponse]:
    cpes = ListGestionCPEsUseCase(db).execute(actor, gestion_id)
    return [CPEResponse.model_validate(item) for item in cpes]


@router.post("/api/v1/gestions/{gestion_id}/cpes", response_model=CPEResponse, status_code=201)
def create_cpe(
    gestion_id: UUID,
    payload: CPECreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CPEResponse:
    cpe = CreateCPEUseCase(db, AuditService(db)).execute(actor, gestion_id, payload)
    return CPEResponse.model_validate(cpe)


@router.get("/api/v1/cpes/{cpe_id}", response_model=CPEResponse)
def get_cpe(
    cpe_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CPEResponse:
    cpe = GetCPEUseCase(db).execute(actor, cpe_id)
    return CPEResponse.model_validate(cpe)


@router.patch("/api/v1/cpes/{cpe_id}", response_model=CPEResponse)
def patch_cpe(
    cpe_id: UUID,
    payload: CPEPatchRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CPEResponse:
    cpe = UpdateCPEUseCase(db, AuditService(db)).execute(actor, cpe_id, payload)
    return CPEResponse.model_validate(cpe)


@router.post("/api/v1/cpes/{cpe_id}/reassign", response_model=CPEResponse)
def reassign_cpe(
    cpe_id: UUID,
    payload: CPEReassignRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> CPEResponse:
    cpe = ReassignCPEUseCase(db, AuditService(db)).execute(actor, cpe_id, payload)
    return CPEResponse.model_validate(cpe)


@router.get("/api/v1/organizations/{organization_id}/cpes", response_model=list[CPEResponse])
def list_org_cpes(
    organization_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[CPEResponse]:
    cpes = ListOrganizationCPEsUseCase(db).execute(actor, organization_id)
    return [CPEResponse.model_validate(item) for item in cpes]


@router.get("/api/v1/cpes/{cpe_id}/reassignments", response_model=list[CPEReassignmentResponse])
def list_cpe_reassignments(
    cpe_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[CPEReassignmentResponse]:
    records = ListReassignmentsUseCase(db).execute(actor, cpe_id)
    return [CPEReassignmentResponse.model_validate(item) for item in records]
