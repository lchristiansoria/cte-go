import base64
import binascii
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_current_actor, get_db
from ctg_go.api.errors import ApiError
from ctg_go.modules.arca.client import ArcaCPEClient, ArcaServiceError
from ctg_go.modules.arca.router import get_arca_client
from ctg_go.modules.audit.services import AuditService
from ctg_go.modules.cpe.arca_request import build_automotor_request
from ctg_go.modules.cpe.models import CPEOperation, CPEOperationStatus, CPEDraft
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
from ctg_go.modules.identity.services import assert_operator_or_admin

router = APIRouter(tags=["cpes"])


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _response_body(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    body = response.get("respuesta", response)
    return body if isinstance(body, dict) else {}


def _emission_summary(response: dict[str, Any], cpe_id: UUID) -> dict[str, Any]:
    body = _response_body(response)
    header = body.get("cabecera")
    header = header if isinstance(header, dict) else {}
    summary = {
        key: header[key]
        for key in ("tipoCartaPorte", "sucursal", "nroOrden", "nroCTG", "fechaEmision", "estado", "fechaVencimiento")
        if key in header
    }
    if body.get("pdf") is not None:
        summary["pdf_url"] = f"/api/v1/cpes/{cpe_id}/pdf"
    return summary


def _response_errors(response: dict[str, Any]) -> list[dict[str, Any]]:
    errors = _response_body(response).get("errores")
    if not errors:
        return []
    if isinstance(errors, dict):
        errors = errors.get("error", errors)
    errors = errors if isinstance(errors, list) else [errors]
    return [error for error in errors if isinstance(error, dict)]


def _latest_emission(db: Session, actor: User, cpe_id: UUID) -> CPEOperation | None:
    return db.scalar(
        select(CPEOperation)
        .where(
            CPEOperation.organization_id == actor.organization_id,
            CPEOperation.cpe_draft_id == cpe_id,
        )
        .order_by(desc(CPEOperation.created_at))
        .limit(1)
    )


def _recover_emission(
    db: Session,
    actor: User,
    cpe: CPEDraft,
    operation: CPEOperation,
    client: ArcaCPEClient,
) -> dict[str, Any]:
    request_data = operation.request_json or {}
    header = request_data.get("cabecera", {})
    try:
        result = client.consultar_cpe_automotor(
            cuit_solicitante=str(header["cuitSolicitante"]),
            tipo_cpe=int(header["tipoCP"]),
            sucursal=int(header["sucursal"]),
            nro_orden=int(header["nroOrden"]),
        )
    except (ArcaServiceError, KeyError, TypeError, ValueError) as exc:
        operation.status = CPEOperationStatus.UNCERTAIN.value
        operation.error_message = "Emission outcome is uncertain; ARCA lookup did not resolve it."
        db.commit()
        raise ApiError(
            status_code=409,
            code="emission_uncertain",
            message="ARCA did not resolve the previous emission. It was not sent again; contact support before another attempt.",
        ) from exc

    safe_result = _json_safe(result)
    body = _response_body(result)
    header_result = body.get("cabecera")
    if isinstance(header_result, dict) and (
        header_result.get("nroCTG") is not None or header_result.get("estado") is not None
    ):
        operation.status = CPEOperationStatus.SUCCESS.value
        operation.response_json = safe_result
        operation.error_message = None
        cpe.status = "confirmed"
        cpe.version += 1
        cpe.payload_json = {
            **cpe.payload_json,
            "arca_emission": {
                "operation_id": str(operation.id),
                "status": "accepted",
                "response_summary": _emission_summary(safe_result, cpe.id),
            },
        }
        db.add(cpe)
        AuditService(db).log(
            actor=actor,
            entity_type="cpe_draft",
            entity_id=str(cpe.id),
            action="cpe.emission_recovered",
            details={"operation_id": str(operation.id)},
        )
        db.commit()
        db.refresh(cpe)
        return {
            "cpe": CPEResponse.model_validate(cpe).model_dump(mode="json"),
            "emission": _emission_summary(safe_result, cpe.id),
            "recovered": True,
        }

    operation.status = CPEOperationStatus.UNCERTAIN.value
    operation.response_json = safe_result
    operation.error_message = "ARCA lookup did not find a conclusive result; do not re-emit."
    db.commit()
    raise ApiError(
        status_code=409,
        code="emission_uncertain",
        message="ARCA did not return a conclusive result for the previous emission. The request was not sent again.",
    )


@router.post("/api/v1/cpes/{cpe_id}/emit")
def emit_cpe(
    cpe_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
    client: ArcaCPEClient = Depends(get_arca_client),
) -> dict[str, Any]:
    assert_operator_or_admin(actor)
    cpe = db.scalar(
        select(CPEDraft)
        .where(
            CPEDraft.id == cpe_id,
            CPEDraft.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if cpe is None:
        raise ApiError(status_code=404, code="not_found", message="CPE not found.")
    if cpe.responsible_user_id != actor.id:
        raise ApiError(status_code=403, code="forbidden", message="Only the responsible user can emit this CPE.")

    previous = _latest_emission(db, actor, cpe_id)
    if previous and previous.status == CPEOperationStatus.SUCCESS.value:
        return {
            "cpe": CPEResponse.model_validate(cpe).model_dump(mode="json"),
            "emission": _emission_summary(previous.response_json or {}, cpe.id),
            "recovered": False,
        }
    if previous and previous.status in {
        CPEOperationStatus.IN_PROGRESS.value,
        CPEOperationStatus.UNCERTAIN.value,
    }:
        return _recover_emission(db, actor, cpe, previous, client)
    if cpe.status != "draft":
        raise ApiError(status_code=409, code="invalid_cpe_state", message="Only a draft CPE can be emitted.")

    form = cpe.payload_json.get("cpe", {})
    if not isinstance(form, dict):
        raise ApiError(status_code=422, code="validation_error", message="CPE form data is missing.")
    validated_request = build_automotor_request(form, 1)
    branch = validated_request["cabecera"]["sucursal"]
    try:
        last_order_result = client.consultar_ultimo_nro_orden(branch, 74)
    except (ValueError, ArcaServiceError) as exc:
        raise ApiError(
            status_code=502,
            code="arca_order_lookup_failed",
            message="ARCA could not provide the last order number; the CPE was not emitted.",
        ) from exc

    last_order_body = _response_body(last_order_result)
    raw_last_order = last_order_body.get("nroOrden")
    if raw_last_order is None:
        raise ApiError(
            status_code=502,
            code="arca_order_lookup_incomplete",
            message="ARCA did not return the last order number; the CPE was not emitted.",
        )
    try:
        next_order = int(raw_last_order) + 1
    except (ValueError, TypeError) as exc:
        raise ApiError(status_code=502, code="arca_order_lookup_incomplete", message="ARCA returned an invalid last order number.") from exc
    if next_order > 99999999:
        raise ApiError(status_code=422, code="order_number_exhausted", message="The ARCA order number limit has been reached.")

    solicitud = build_automotor_request(form, next_order)
    operation = CPEOperation(
        organization_id=actor.organization_id,
        cpe_draft_id=cpe.id,
        status=CPEOperationStatus.IN_PROGRESS.value,
        request_json=_json_safe(solicitud),
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)

    try:
        response = client.autorizar_cpe_automotor(solicitud)
        safe_response = _json_safe(response)
    except ArcaServiceError as exc:
        if exc.response is not None:
            operation.response_json = _json_safe(exc.response)
        operation.status = (
            CPEOperationStatus.UNCERTAIN.value
            if exc.uncertain
            else CPEOperationStatus.FAILED.value
        )
        operation.error_message = str(exc)
        db.commit()
        if exc.uncertain:
            raise ApiError(
                status_code=502,
                code="emission_uncertain",
                message="ARCA may have received the request, but the response was not conclusive. Consultar ARCA antes de intentar nuevamente.",
            ) from exc
        raise ApiError(
            status_code=502,
            code="arca_emission_rejected",
            message="ARCA rejected the CPE request. The draft was preserved.",
        ) from exc

    business_errors = [error for error in _response_errors(safe_response) if str(error.get("codigo")) != "550"]
    operation.response_json = safe_response
    if business_errors:
        operation.status = CPEOperationStatus.FAILED.value
        operation.error_message = "; ".join(
            f"{error.get('codigo', '')}: {error.get('descripcion', '')}".strip(": ")
            for error in business_errors
        )
        db.commit()
        raise ApiError(
            status_code=422,
            code="arca_emission_rejected",
            message="ARCA returned validation errors. The draft and response were preserved.",
            field_errors=[{"field": "arca", "message": operation.error_message}],
        )

    response_header = _response_body(safe_response).get("cabecera")
    if not isinstance(response_header, dict) or not any(
        response_header.get(key) is not None
        for key in ("nroCTG", "estado", "nroOrden")
    ):
        operation.status = CPEOperationStatus.UNCERTAIN.value
        operation.error_message = "ARCA returned no conclusive CPE identifier."
        db.commit()
        raise ApiError(
            status_code=502,
            code="emission_uncertain",
            message="ARCA returned no conclusive CPE identifier. Consultar ARCA antes de intentar nuevamente.",
        )

    operation.status = CPEOperationStatus.SUCCESS.value
    summary = _emission_summary(safe_response, cpe.id)
    cpe.status = "confirmed"
    cpe.version += 1
    cpe.payload_json = {
        **cpe.payload_json,
        "arca_emission": {
            "operation_id": str(operation.id),
            "status": "accepted",
            "request": _json_safe(solicitud),
            "response_summary": summary,
        },
    }
    db.add(cpe)
    AuditService(db).log(
        actor=actor,
        entity_type="cpe_draft",
        entity_id=str(cpe.id),
        action="cpe.emitted",
        details={"operation_id": str(operation.id)},
    )
    db.commit()
    db.refresh(cpe)
    return {
        "cpe": CPEResponse.model_validate(cpe).model_dump(mode="json"),
        "emission": summary,
        "recovered": False,
    }


@router.get("/api/v1/cpes/{cpe_id}/pdf")
def get_emitted_pdf(
    cpe_id: UUID,
    actor: User = Depends(get_current_actor),
    db: Session = Depends(get_db),
) -> Response:
    assert_operator_or_admin(actor)
    cpe = GetCPEUseCase(db).execute(actor, cpe_id)
    operation = db.scalar(
        select(CPEOperation)
        .where(
            CPEOperation.organization_id == actor.organization_id,
            CPEOperation.cpe_draft_id == cpe.id,
            CPEOperation.status == CPEOperationStatus.SUCCESS.value,
        )
        .order_by(desc(CPEOperation.created_at))
        .limit(1)
    )
    body = _response_body(operation.response_json or {}) if operation else {}
    pdf = body.get("pdf")
    if not isinstance(pdf, (str, bytes)):
        raise ApiError(status_code=404, code="not_found", message="ARCA did not return a PDF.")
    try:
        pdf_bytes = base64.b64decode(pdf, validate=False) if isinstance(pdf, str) else pdf
    except (ValueError, binascii.Error) as exc:
        raise ApiError(status_code=502, code="invalid_arca_pdf", message="ARCA returned an invalid PDF.") from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cpe-{cpe.id}.pdf"'},
    )


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
