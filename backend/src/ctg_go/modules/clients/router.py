from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.schemas import (
    ClientCpeResponse,
    ClientCreateRequest,
    ClientResponse,
    ClientUpdateRequest,
)
from ctg_go.modules.clients.use_cases import (
    CreateClientUseCase,
    DeleteClientUseCase,
    GetClientUseCase,
    ListClientCpesUseCase,
    ListClientsUseCase,
    UpdateClientUseCase,
)
from ctg_go.modules.identity.models import User

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
def list_clients(
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[ClientResponse]:
    clients = ListClientsUseCase(db).execute(actor)
    return [ClientResponse.model_validate(client) for client in clients]


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ClientResponse:
    client = CreateClientUseCase(db, AuditService(db)).execute(actor, payload)
    return ClientResponse.model_validate(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ClientResponse:
    return ClientResponse.model_validate(GetClientUseCase(db).execute(actor, client_id))


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> ClientResponse:
    client = UpdateClientUseCase(db, AuditService(db)).execute(actor, client_id, payload)
    return ClientResponse.model_validate(client)


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> Response:
    DeleteClientUseCase(db, AuditService(db)).execute(actor, client_id)
    return Response(status_code=204)


@router.get("/{client_id}/cpes", response_model=list[ClientCpeResponse])
def list_client_cpes(
    client_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> list[ClientCpeResponse]:
    return ListClientCpesUseCase(db).execute(actor, client_id)
