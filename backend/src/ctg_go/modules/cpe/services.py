from __future__ import annotations

from sqlalchemy import Select, select

from ctg_go.modules.cpe.models import CPEDraft, CPEOperation


def scoped_cpes_query(organization_id) -> Select[tuple[CPEDraft]]:
    return select(CPEDraft).where(CPEDraft.organization_id == organization_id)


def has_blocking_operation_query(organization_id, cpe_draft_id) -> Select[tuple[CPEOperation]]:
    return (
        select(CPEOperation)
        .where(
            CPEOperation.organization_id == organization_id,
            CPEOperation.cpe_draft_id == cpe_draft_id,
            CPEOperation.status.in_(["pending", "in_progress", "uncertain"]),
        )
        .limit(1)
    )
