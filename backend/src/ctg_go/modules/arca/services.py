from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.arca.client import ArcaCPEClient, ArcaServiceError
from ctg_go.modules.arca.models import (
    ArcaCatalog,
    ArcaCuit,
    ArcaCuitDataset,
    ArcaCuitGrant,
)
from ctg_go.modules.identity.models import User

STALE_AFTER = timedelta(hours=24)

# dataset name -> client method. Every one is queried on behalf of one CUIT.
CUIT_DATASETS: dict[str, str] = {
    "domicilios": "consultar_domicilios_por_cuit",
    "plantas": "consultar_plantas",
    "localidades_productor": "consultar_localidades_productor",
}

# Catalogs that ARCA returns independently of the represented CUIT.
CATALOGS: dict[str, str] = {
    "provincias": "consultar_provincias",
    "tipos_grano": "consultar_tipos_grano",
    "tipos_embalaje": "consultar_tipos_embalaje",
    "unidades_medida": "consultar_unidades_medida",
}
REQUIRED_CATALOGS = ("provincias", "tipos_grano")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def is_valid_cuit(value: str) -> bool:
    if len(value) != 11 or not value.isdigit():
        return False
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    digit = 11 - sum(int(v) * w for v, w in zip(value[:10], weights)) % 11
    expected = 0 if digit == 11 else 9 if digit == 10 else digit
    return expected == int(value[10])


def valid_harvests(today: date | None = None) -> list[dict[str, Any]]:
    """Harvest codes ARCA accepts, derived locally.

    The manual defines ``Cosecha`` as four digits (e.g. 2324) and states that
    the last 10 are valid; ARCA publishes no query for them. The campaign
    rollover month (July) is an assumption that homologation must confirm.
    """
    today = today or utcnow().date()
    current = today.year if today.month >= 7 else today.year - 1
    return [
        {"code": int(f"{start % 100:02d}{(start + 1) % 100:02d}"), "label": f"{start}/{(start + 1) % 100:02d}"}
        for start in range(current, current - 10, -1)
    ]


def extract_items(response: Any) -> list[Any]:
    """Return the repeated element of a WSCPE response, without errors/metadata."""
    if not isinstance(response, dict):
        return []
    for key, value in response.items():
        if key in {"errores", "metadata"} or value is None:
            continue
        if isinstance(value, list):
            return json.loads(json.dumps(value, default=str))
        if isinstance(value, dict):
            return [json.loads(json.dumps(value, default=str))]
    return []


def _safe_errors(exc: ArcaServiceError) -> list[dict[str, str]]:
    if exc.errors:
        return exc.errors
    if exc.kind == "uncertain":
        return [{"code": "", "description": "No response from ARCA."}]
    return [{"code": "", "description": "ARCA rejected the query."}]


def access_error() -> ApiError:
    return ApiError(status_code=404, code="not_found", message="CUIT not found.")


def accessible_cuits_query(actor: User):
    query = select(ArcaCuit).where(ArcaCuit.organization_id == actor.organization_id)
    if actor.role != "admin":
        query = query.join(
            ArcaCuitGrant,
            (ArcaCuitGrant.arca_cuit_id == ArcaCuit.id)
            & (ArcaCuitGrant.organization_id == ArcaCuit.organization_id),
        ).where(ArcaCuitGrant.user_id == actor.id)
    return query


def get_accessible_cuit(db: Session, actor: User, cuit_id: UUID, environment: str) -> ArcaCuit:
    record = db.scalar(
        accessible_cuits_query(actor).where(
            ArcaCuit.id == cuit_id, ArcaCuit.environment == environment
        )
    )
    if record is None:
        raise access_error()
    return record


@dataclass
class VerificationResult:
    status: str
    response: Any = None
    errors: list[dict[str, str]] | None = None


def verify_delegation(db: Session, record: ArcaCuit, client: ArcaCPEClient) -> VerificationResult:
    """Probe ARCA on behalf of the CUIT.

    No WSCPE operation lists delegations; a successful authenticated query with
    cuitRepresentada=<cuit> is the only available evidence that it is usable.
    """
    now = utcnow()
    record.last_checked_at = now
    try:
        response = client.for_cuit(record.cuit).consultar_domicilios_por_cuit()
    except ArcaServiceError as exc:
        record.last_error_kind = exc.kind
        record.last_errors_json = _safe_errors(exc)
        if exc.kind == "uncertain":
            return VerificationResult("uncertain", errors=record.last_errors_json)
        record.delegation_status = "rejected"
        return VerificationResult("rejected", errors=record.last_errors_json)
    record.delegation_status = "verified"
    record.last_verified_at = now
    record.last_error_kind = None
    record.last_errors_json = []
    return VerificationResult("verified", response=response)


def _upsert_dataset(
    db: Session,
    record: ArcaCuit,
    dataset: str,
    scope_key: str,
    *,
    items: list[Any] | None,
    errors: list[dict[str, str]] | None,
) -> ArcaCuitDataset:
    row = db.scalar(
        select(ArcaCuitDataset).where(
            ArcaCuitDataset.arca_cuit_id == record.id,
            ArcaCuitDataset.dataset == dataset,
            ArcaCuitDataset.scope_key == scope_key,
        )
    )
    if row is None:
        row = ArcaCuitDataset(
            organization_id=record.organization_id,
            arca_cuit_id=record.id,
            dataset=dataset,
            scope_key=scope_key,
            payload_json=[],
            item_count=0,
            last_errors_json=[],
        )
        db.add(row)
    now = utcnow()
    row.last_attempt_at = now
    if errors is None:
        row.payload_json = items or []
        row.item_count = len(items or [])
        row.synced_at = now
        row.last_errors_json = []
    else:
        row.last_errors_json = errors
    return row


def sync_cuit(
    db: Session,
    record: ArcaCuit,
    client: ArcaCPEClient,
    datasets: list[str] | None = None,
) -> dict[str, Any]:
    names = datasets or list(CUIT_DATASETS)
    verification = verify_delegation(db, record, client)
    outcome: dict[str, str] = {}
    if verification.status != "verified":
        db.commit()
        return {"delegation": verification.status, "datasets": outcome}

    scoped = client.for_cuit(record.cuit)
    for name in names:
        try:
            if name == "domicilios":
                response = verification.response
            else:
                response = getattr(scoped, CUIT_DATASETS[name])()
        except ArcaServiceError as exc:
            _upsert_dataset(db, record, name, "", items=None, errors=_safe_errors(exc))
            outcome[name] = "error"
            continue
        _upsert_dataset(db, record, name, "", items=extract_items(response), errors=None)
        outcome[name] = "ok"
    db.commit()
    return {"delegation": "verified", "datasets": outcome}


def sync_catalogs(
    db: Session, client: ArcaCPEClient, environment: str, names: list[str] | None = None
) -> dict[str, str]:
    outcome: dict[str, str] = {}
    for name in names or list(CATALOGS):
        row = db.scalar(
            select(ArcaCatalog).where(
                ArcaCatalog.environment == environment,
                ArcaCatalog.dataset == name,
                ArcaCatalog.scope_key == "",
            )
        )
        if row is None:
            row = ArcaCatalog(
                environment=environment,
                dataset=name,
                scope_key="",
                payload_json=[],
                item_count=0,
                last_errors_json=[],
            )
            db.add(row)
        now = utcnow()
        row.last_attempt_at = now
        try:
            items = extract_items(getattr(client, CATALOGS[name])())
        except ArcaServiceError as exc:
            row.last_errors_json = _safe_errors(exc)
            outcome[name] = "error"
            continue
        row.payload_json = items
        row.item_count = len(items)
        row.synced_at = now
        row.last_errors_json = []
        outcome[name] = "ok"
    db.commit()
    return outcome


def freshness(synced_at: datetime | None, now: datetime | None = None) -> dict[str, Any]:
    synced = _aware(synced_at)
    return {
        "synced_at": synced,
        "stale": synced is None or (now or utcnow()) - synced > STALE_AFTER,
    }


# Values of tipoCPE for the automotor forms in the ARCA portal screenshots
# (74 / 274); both are in the WSCPE manual's allowed values for tipoCPE.
CPE_TYPES = [
    {"code": 74, "description": "Automotor - Grano", "flow": "flete_largo"},
    {"code": 274, "description": "Automotor Flete Corto - Grano", "flow": "flete_corto"},
]

# Where each field of the portal wizard (Datos de solicitud / carga / destino)
# comes from. "unconfirmed" = no WSCPE operation found in the manual or WSDL.
FIELD_SOURCES = {
    "solicitante.cuit": "arca_cuit",
    "solicitante.razon_social": "unconfirmed",
    "solicitante.situacion_sisa": "unconfirmed",
    "origen.localidades": "dataset:localidades_productor",
    "origen.coordenadas_gps": "dataset:localidades_productor",
    "origen.renspa": "live:renspa",
    "intervinientes.razon_social": "unconfirmed",
    "destino.provincia": "catalog:provincias",
    "destino.localidad": "live:localidadesPorProvincia",
    "destino.planta_domicilio": "dataset:plantas",
    "carga.grano": "catalog:tipos_grano",
    "carga.campana": "derived_locally",
    "transporte.transportista_razon_social": "response:razonSocialTransportista",
    "transporte.codigo_turno": "unconfirmed",
}


def emission_context(db: Session, record: ArcaCuit) -> dict[str, Any]:
    """Readiness summary for preparing a Carta de Porte for this CUIT only."""
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if record.delegation_status != "verified":
        blockers.append(
            {
                "code": "delegation_not_verified",
                "message": "Verify the ARCA delegation of the wscpe service for this CUIT.",
            }
        )

    dataset_rows = {
        row.dataset: row
        for row in db.scalars(
            select(ArcaCuitDataset).where(ArcaCuitDataset.arca_cuit_id == record.id)
        )
    }
    datasets: dict[str, Any] = {}
    for name in CUIT_DATASETS:
        row = dataset_rows.get(name)
        info = freshness(row.synced_at if row else None)
        info["item_count"] = row.item_count if row else 0
        info["errors"] = row.last_errors_json if row else []
        datasets[name] = info
        if info["synced_at"] is None:
            warnings.append({"code": f"{name}_not_synced", "message": f"{name} has not been synchronized."})
        elif info["stale"]:
            warnings.append({"code": f"{name}_stale", "message": f"{name} is older than 24 hours."})

    catalog_rows = {
        row.dataset: row
        for row in db.scalars(
            select(ArcaCatalog).where(ArcaCatalog.environment == record.environment)
        )
    }
    catalogs: dict[str, Any] = {}
    for name in CATALOGS:
        row = catalog_rows.get(name)
        info = freshness(row.synced_at if row else None)
        info["item_count"] = row.item_count if row else 0
        catalogs[name] = info
        if name in REQUIRED_CATALOGS and info["synced_at"] is None:
            blockers.append({"code": f"{name}_missing", "message": f"Catalog {name} has not been synchronized."})

    return {
        "cuit": record.cuit,
        "environment": record.environment,
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "datasets": datasets,
        "catalogs": catalogs,
        "harvests": {"source": "derived_locally", "confirmed_by_arca": False, "items": valid_harvests()},
        "cpe_types": CPE_TYPES,
        "field_sources": FIELD_SOURCES,
    }
