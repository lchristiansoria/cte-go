from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.clients.schemas import ClientCreateRequest, ClientResponse
from ctg_go.modules.clients.use_cases import CreateClientUseCase, ListClientsUseCase
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
