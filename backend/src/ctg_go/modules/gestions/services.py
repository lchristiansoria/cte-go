from __future__ import annotations

from sqlalchemy import Select, select

from ctg_go.modules.gestions.models import Gestion


def scoped_gestions_query(organization_id) -> Select[tuple[Gestion]]:
    return select(Gestion).where(Gestion.organization_id == organization_id)
