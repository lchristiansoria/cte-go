from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.clients.models import Client


def scoped_clients_query(organization_id) -> Select[tuple[Client]]:
    return select(Client).where(Client.organization_id == organization_id)


def get_scoped_client(db: Session, organization_id, client_id) -> Client:
    client = db.scalar(scoped_clients_query(organization_id).where(Client.id == client_id))
    if client is None:
        raise ApiError(status_code=404, code="not_found", message="Client not found.")
    return client
