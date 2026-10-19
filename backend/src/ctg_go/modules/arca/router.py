from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ctg_go.api.dependencies import get_current_actor
from ctg_go.api.errors import ApiError
from ctg_go.modules.arca.client import (
    ArcaCPEClient,
    ArcaConfigurationError,
    ArcaServiceError,
    ArcaSettings,
)
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import assert_operator_or_admin

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
