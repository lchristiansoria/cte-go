from __future__ import annotations

from sqlalchemy import Select, select

from ctg_go.modules.clients.models import Client


def scoped_clients_query(organization_id) -> Select[tuple[Client]]:
    return select(Client).where(Client.organization_id == organization_id)
