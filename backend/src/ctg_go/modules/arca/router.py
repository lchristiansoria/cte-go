from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.api.errors import ApiError
from ctg_go.modules.arca import services as arca_services
from ctg_go.modules.arca.client import (
    ArcaCPEClient,
    ArcaConfigurationError,
    ArcaServiceError,
    ArcaSettings,
)
from ctg_go.modules.arca.models import (
    ArcaCatalog,
    ArcaCuit,
    ArcaCuitDataset,
    ArcaCuitGrant,
)
from ctg_go.modules.arca.schemas import (
    ArcaCuitCreateRequest,
    ArcaCuitGrantsRequest,
    ArcaCuitResponse,
    ArcaCuitSyncRequest,
)
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_admin, assert_operator_or_admin

router = APIRouter(prefix="/api/v1/arca", tags=["arca"])


def get_arca_client(request: Request) -> ArcaCPEClient:
    client = getattr(request.app.state, "arca_client", None)
    if client is not None:
        return client
    try:
        client = ArcaCPEClient(ArcaSettings.from_env())
    except ArcaConfigurationError as exc:
        raise ApiError(
            status_code=503,
            code="arca_not_configured",
            message="ARCA integration is not configured.",
        ) from exc
    request.app.state.arca_client = client
    return client


def _query(actor: User, client: ArcaCPEClient, method: str, **kwargs: Any) -> Any:
    assert_operator_or_admin(actor)
    try:
        return getattr(client, method)(**kwargs)
    except ArcaServiceError as exc:
        raise ApiError(
            status_code=502,
            code="arca_query_failed",
            message="ARCA query failed.",
        ) from exc


@router.get("/provincias")
def provincias(
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_provincias")


@router.get("/configuracion")
def configuracion(
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, int | None]:
    assert_operator_or_admin(actor)
    settings = getattr(client, "settings", None)
    return {"sucursal": getattr(settings, "default_branch", None)}


@router.get("/localidades")
def localidades(
    cod_provincia: int,
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_localidades", cod_provincia=cod_provincia)


@router.get("/tipos-grano")
def tipos_grano(
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_tipos_grano")


@router.get("/tipos-embalaje")
def tipos_embalaje(
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_tipos_embalaje")


@router.get("/unidades-medida")
def unidades_medida(
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_unidades_medida")


@router.get("/plantas")
def plantas(
    cuit: str | None = Query(default=None, pattern=r"^\d{11}$"),
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(actor, client, "consultar_plantas", cuit=cuit)


@router.get("/ultimo-nro-orden")
def ultimo_nro_orden(
    sucursal: int,
    tipo_cpe: int,
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    return _query(
        actor,
        client,
        "consultar_ultimo_nro_orden",
        sucursal=sucursal,
        tipo_cpe=tipo_cpe,
    )


@router.get("/cpes/automotor")
def consultar_cpe_automotor(
    cuit_solicitante: str | None = Query(default=None, pattern=r"^\d{11}$"),
    tipo_cpe: int | None = None,
    sucursal: int | None = None,
    nro_orden: int | None = None,
    nro_ctg: int | None = None,
    actor: User = Depends(get_current_actor),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> Any:
    order_values = (tipo_cpe, sucursal, nro_orden)
    if any(value is not None for value in order_values) and not all(
        value is not None for value in order_values
    ):
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="tipo_cpe, sucursal, and nro_orden must be provided together.",
        )
    if not cuit_solicitante and all(value is None for value in order_values) and nro_ctg is None:
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="Provide a CPE identifier or cuit_solicitante.",
        )
    return _query(
        actor,
        client,
        "consultar_cpe_automotor",
        cuit_solicitante=cuit_solicitante,
        tipo_cpe=tipo_cpe,
        sucursal=sucursal,
        nro_orden=nro_orden,
        nro_ctg=nro_ctg,
    )


# --- Delegated CUITs: registry, verification and per-CUIT synchronization ---


def _environment(client: ArcaCPEClient) -> str:
    return client.settings.environment


def _cuit_response(record: ArcaCuit, user_ids: list | None = None) -> ArcaCuitResponse:
    return ArcaCuitResponse(
        id=record.id,
        cuit=record.cuit,
        label=record.label,
        environment=record.environment,
        delegation_status=record.delegation_status,
        last_checked_at=record.last_checked_at,
        last_verified_at=record.last_verified_at,
        last_error_kind=record.last_error_kind,
        last_errors=record.last_errors_json or [],
        user_ids=user_ids,
    )


def _scoped_cuit(
    db: Session, actor: User, cuit_id: UUID, client: ArcaCPEClient
) -> ArcaCuit:
    assert_operator_or_admin(actor)
    return arca_services.get_accessible_cuit(db, actor, cuit_id, _environment(client))


@router.get("/cuits", response_model=list[ArcaCuitResponse])
def list_cuits(
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> list[ArcaCuitResponse]:
    assert_operator_or_admin(actor)
    rows = db.scalars(
        arca_services.accessible_cuits_query(actor)
        .where(ArcaCuit.environment == _environment(client))
        .order_by(ArcaCuit.cuit)
    ).all()
    return [_cuit_response(row) for row in rows]


@router.post("/cuits", response_model=ArcaCuitResponse, status_code=201)
def register_cuit(
    payload: ArcaCuitCreateRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> ArcaCuitResponse:
    assert_admin(actor)
    if not arca_services.is_valid_cuit(payload.cuit):
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="Invalid request.",
            field_errors=[{"field": "cuit", "message": "CUIT check digit is invalid."}],
        )
    environment = _environment(client)
    exists = db.scalar(
        select(ArcaCuit.id).where(
            ArcaCuit.organization_id == actor.organization_id,
            ArcaCuit.cuit == payload.cuit,
            ArcaCuit.environment == environment,
        )
    )
    if exists is not None:
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="CUIT already registered.",
            field_errors=[{"field": "cuit", "message": "already exists"}],
        )
    record = ArcaCuit(
        organization_id=actor.organization_id,
        cuit=payload.cuit,
        label=payload.label,
        environment=environment,
        delegation_status="unverified",
        last_errors_json=[],
        created_by_user_id=actor.id,
    )
    db.add(record)
    db.flush()
    AuditService(db).log(
        actor=actor,
        entity_type="arca_cuit",
        entity_id=str(record.id),
        action="arca_cuit.registered",
        details={"cuit": record.cuit, "environment": environment},
    )
    db.commit()
    return _cuit_response(record)


@router.delete("/cuits/{cuit_id}", status_code=204)
def delete_cuit(
    cuit_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> None:
    assert_admin(actor)
    record = arca_services.get_accessible_cuit(db, actor, cuit_id, _environment(client))
    for model in (ArcaCuitDataset, ArcaCuitGrant):
        for row in db.scalars(select(model).where(model.arca_cuit_id == record.id)):
            db.delete(row)
    AuditService(db).log(
        actor=actor,
        entity_type="arca_cuit",
        entity_id=str(record.id),
        action="arca_cuit.removed",
        details={"cuit": record.cuit},
    )
    db.delete(record)
    db.commit()


@router.put("/cuits/{cuit_id}/grants", response_model=ArcaCuitResponse)
def set_cuit_grants(
    cuit_id: UUID,
    payload: ArcaCuitGrantsRequest,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> ArcaCuitResponse:
    assert_admin(actor)
    record = arca_services.get_accessible_cuit(db, actor, cuit_id, _environment(client))
    requested = set(payload.user_ids)
    valid = set(
        db.scalars(
            select(User.id).where(
                User.organization_id == actor.organization_id, User.id.in_(requested)
            )
        )
    )
    if valid != requested:
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="Invalid request.",
            field_errors=[{"field": "user_ids", "message": "unknown user"}],
        )
    current = {
        row.user_id: row
        for row in db.scalars(select(ArcaCuitGrant).where(ArcaCuitGrant.arca_cuit_id == record.id))
    }
    for user_id, row in current.items():
        if user_id not in requested:
            db.delete(row)
    for user_id in requested - set(current):
        db.add(
            ArcaCuitGrant(
                organization_id=record.organization_id,
                arca_cuit_id=record.id,
                user_id=user_id,
            )
        )
    AuditService(db).log(
        actor=actor,
        entity_type="arca_cuit",
        entity_id=str(record.id),
        action="arca_cuit.grants_updated",
        details={"cuit": record.cuit, "user_ids": sorted(str(u) for u in requested)},
    )
    db.commit()
    return _cuit_response(record, sorted(requested, key=str))


@router.get("/cuits/{cuit_id}", response_model=ArcaCuitResponse)
def get_cuit(
    cuit_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> ArcaCuitResponse:
    record = _scoped_cuit(db, actor, cuit_id, client)
    user_ids = None
    if actor.role == "admin":
        user_ids = list(
            db.scalars(select(ArcaCuitGrant.user_id).where(ArcaCuitGrant.arca_cuit_id == record.id))
        )
    return _cuit_response(record, user_ids)


@router.post("/cuits/{cuit_id}/verify", response_model=ArcaCuitResponse)
def verify_cuit(
    cuit_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> ArcaCuitResponse:
    record = _scoped_cuit(db, actor, cuit_id, client)
    arca_services.verify_delegation(db, record, client)
    AuditService(db).log(
        actor=actor,
        entity_type="arca_cuit",
        entity_id=str(record.id),
        action="arca_cuit.verified",
        details={"cuit": record.cuit, "status": record.delegation_status},
    )
    db.commit()
    return _cuit_response(record)


@router.post("/cuits/{cuit_id}/sync")
def sync_cuit(
    cuit_id: UUID,
    payload: ArcaCuitSyncRequest | None = None,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    record = _scoped_cuit(db, actor, cuit_id, client)
    names = payload.datasets if payload else None
    unknown = [name for name in names or [] if name not in arca_services.CUIT_DATASETS]
    if unknown:
        raise ApiError(
            status_code=422,
            code="validation_error",
            message="Invalid request.",
            field_errors=[{"field": "datasets", "message": f"unknown dataset: {name}"} for name in unknown],
        )
    result = arca_services.sync_cuit(db, record, client, names)
    AuditService(db).log(
        actor=actor,
        entity_type="arca_cuit",
        entity_id=str(record.id),
        action="arca_cuit.synced",
        details={"cuit": record.cuit, **result},
    )
    db.commit()
    return {**result, "cuit": _cuit_response(record).model_dump(mode="json")}


@router.get("/cuits/{cuit_id}/datasets/{dataset}")
def get_cuit_dataset(
    cuit_id: UUID,
    dataset: str,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    record = _scoped_cuit(db, actor, cuit_id, client)
    if dataset not in arca_services.CUIT_DATASETS:
        raise ApiError(status_code=404, code="not_found", message="Dataset not found.")
    row = db.scalar(
        select(ArcaCuitDataset).where(
            ArcaCuitDataset.arca_cuit_id == record.id,
            ArcaCuitDataset.dataset == dataset,
            ArcaCuitDataset.scope_key == "",
        )
    )
    info = arca_services.freshness(row.synced_at if row else None)
    return {
        "cuit": record.cuit,
        "dataset": dataset,
        **info,
        "last_attempt_at": row.last_attempt_at if row else None,
        "errors": row.last_errors_json if row else [],
        "items": row.payload_json if row else [],
    }


@router.get("/cuits/{cuit_id}/renspa")
def get_cuit_renspa(
    cuit_id: UUID,
    cod_provincia: int,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    record = _scoped_cuit(db, actor, cuit_id, client)
    try:
        response = client.for_cuit(record.cuit).consultar_renspa(cod_provincia)
    except ArcaServiceError as exc:
        raise ApiError(status_code=502, code="arca_query_failed", message="ARCA query failed.") from exc
    return {"cuit": record.cuit, "items": arca_services.extract_items(response)}


@router.get("/cuits/{cuit_id}/emission-context")
def get_emission_context(
    cuit_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    record = _scoped_cuit(db, actor, cuit_id, client)
    return arca_services.emission_context(db, record)


@router.get("/catalogs/{dataset}")
def get_catalog(
    dataset: str,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    assert_operator_or_admin(actor)
    if dataset not in arca_services.CATALOGS:
        raise ApiError(status_code=404, code="not_found", message="Catalog not found.")
    row = db.scalar(
        select(ArcaCatalog).where(
            ArcaCatalog.environment == _environment(client),
            ArcaCatalog.dataset == dataset,
            ArcaCatalog.scope_key == "",
        )
    )
    info = arca_services.freshness(row.synced_at if row else None)
    return {
        "dataset": dataset,
        "environment": _environment(client),
        **info,
        "errors": row.last_errors_json if row else [],
        "items": row.payload_json if row else [],
    }


@router.post("/catalogs/sync")
def sync_catalogs(
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, str]:
    assert_operator_or_admin(actor)
    return arca_services.sync_catalogs(db, client, _environment(client))
