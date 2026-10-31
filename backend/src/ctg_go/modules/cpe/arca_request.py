from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from ctg_go.api.errors import ApiError


def _invalid(field: str, message: str) -> None:
    raise ApiError(
        status_code=422,
        code="validation_error",
        message="The Carta de Porte form contains invalid values.",
        field_errors=[{"field": field, "message": message}],
    )


def _required(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if value is None or not str(value).strip():
        _invalid(key, "This field is required.")
    return str(value).strip()


def _integer(values: dict[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    value = _required(values, key)
    if len(value) > 64 or not re.fullmatch(r"\d+", value):
        _invalid(key, "Enter a whole number.")
    number = int(value)
    if not minimum <= number <= maximum:
        _invalid(key, f"Value must be between {minimum} and {maximum}.")
    return number


def _cuit(values: dict[str, Any], key: str, *, required: bool = True) -> int | None:
    raw = values.get(key)
    if raw is None or not str(raw).strip():
        if required:
            _invalid(key, "Enter a CUIT.")
        return None
    digits = str(raw).strip()
    if not re.fullmatch(r"\d{11}", digits):
        _invalid(key, "CUIT must contain 11 digits.")
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    digit = 11 - sum(int(value) * weight for value, weight in zip(digits[:10], weights)) % 11
    expected = 0 if digit == 11 else 9 if digit == 10 else digit
    if expected != int(digits[10]):
        _invalid(key, "CUIT check digit is invalid.")
    return int(digits)


def _boolean(values: dict[str, Any], key: str) -> bool:
    value = _required(values, key)
    if value not in {"true", "false"}:
        _invalid(key, "Select yes or no.")
    return value == "true"


def _coordinate(value: str, key: str, maximum: int) -> dict[str, int]:
    try:
        coordinate = Decimal(value)
    except InvalidOperation:
        _invalid(key, "Enter a valid decimal coordinate.")
    if not coordinate.is_finite() or abs(coordinate) > maximum:
        _invalid(key, f"Coordinate must be between {-maximum} and {maximum}.")
    absolute = abs(coordinate)
    degrees = int(absolute)
    total_seconds = int((absolute - degrees) * 3600 + Decimal("0.5"))
    minutes, seconds = divmod(total_seconds, 60)
    if minutes == 60:
        degrees += 1
        minutes = 0
    if coordinate < 0:
        degrees *= -1
    return {"grados": degrees, "minutos": minutes, "segundos": seconds}


def build_automotor_request(values: dict[str, Any], nro_orden: int) -> dict[str, Any]:
    """Map human-facing draft fields to the documented WSCPE Automotor schema."""
    mode = _required(values, "origin_mode")
    if mode not in {"producer", "operator"}:
        _invalid("origin_mode", "Choose producer or operator origin.")
    province = _integer(values, "origin_province", minimum=1, maximum=99)
    locality = _integer(values, "origin_locality", minimum=1, maximum=999999)
    if nro_orden < 1:
        _invalid("branch", "ARCA did not return a usable last order number.")

    origin: dict[str, Any]
    if mode == "operator":
        origin = {
            "operador": {
                "codProvincia": province,
                "codLocalidad": locality,
                "planta": _integer(values, "origin_plant", minimum=1, maximum=999999),
            }
        }
    else:
        producer: dict[str, Any] = {
            "codProvincia": province,
            "codLocalidad": locality,
        }
        renspa = values.get("origin_renspa", "").strip()
        if renspa:
            if not re.fullmatch(r"\d{2}\.\d{3}\.\d\.\d{5}/\d{2}", renspa):
                _invalid("origin_renspa", "RENSPA format must be nn.nnn.n.nnnnn/nn.")
            producer["nroRenspa"] = renspa
        latitude = values.get("origin_latitude", "").strip()
        longitude = values.get("origin_longitude", "").strip()
        if bool(latitude) != bool(longitude):
            _invalid("origin_longitude", "Enter both latitude and longitude.")
        if latitude and longitude:
            producer["coordenadasGPS"] = {
                "latitud": _coordinate(latitude, "origin_latitude", 90),
                "longitud": _coordinate(longitude, "origin_longitude", 180),
            }
        origin = {"productor": producer}

    withdrawal = _boolean(values, "corresponds_producer_withdrawal")
    solicitud: dict[str, Any] = {
        "cabecera": {
            "tipoCP": 74,
            "cuitSolicitante": _cuit(values, "requester_cuit"),
            "sucursal": _integer(values, "branch", minimum=1, maximum=99999),
            "nroOrden": nro_orden,
        },
        "origen": origin,
        "correspondeRetiroProductor": withdrawal,
        "esSolicitanteCampo": _boolean(values, "applicant_is_field"),
        "datosCarga": {
            "codGrano": _integer(values, "grain_code", minimum=0, maximum=99),
            "cosecha": _integer(values, "harvest", minimum=1000, maximum=9999),
            "pesoBruto": _integer(values, "gross_weight", minimum=0, maximum=88000),
            "pesoTara": _integer(values, "tare_weight", minimum=0, maximum=88000),
        },
        "destino": {
            "cuit": _cuit(values, "destination_cuit"),
            "esDestinoCampo": _boolean(values, "destination_is_field"),
            "codProvincia": _integer(values, "destination_province", minimum=1, maximum=99),
            "codLocalidad": _integer(values, "destination_locality", minimum=1, maximum=999999),
        },
        "destinatario": {"cuit": _cuit(values, "recipient_cuit")},
        "transporte": {},
    }

    if solicitud["datosCarga"]["pesoBruto"] < solicitud["datosCarga"]["pesoTara"]:
        _invalid("gross_weight", "Gross weight cannot be less than tare weight.")
    if withdrawal:
        coe = _integer(values, "withdrawal_coe", minimum=1, maximum=999999999999999999)
        solicitud["retiroProductor"] = {
            "certificadoCOE": coe,
            "cuitRemitenteComercialProductor": _cuit(values, "withdrawal_producer_cuit"),
        }

    intervinientes: dict[str, int] = {}
    roles = {
        "role_primary_seller": "cuitRemitenteComercialVentaPrimaria",
        "role_secondary_seller": "cuitRemitenteComercialVentaSecundaria",
        "role_secondary_seller_2": "cuitRemitenteComercialVentaSecundaria2",
        "role_futures_market": "cuitMercadoATermino",
        "role_primary_broker": "cuitCorredorVentaPrimaria",
        "role_secondary_broker": "cuitCorredorVentaSecundaria",
        "role_delivery_representative": "cuitRepresentanteEntregador",
        "role_receiving_representative": "cuitRepresentanteRecibidor",
    }
    for form_key, contract_key in roles.items():
        cuit = _cuit(values, form_key, required=False)
        if cuit is not None:
            intervinientes[contract_key] = cuit
    if intervinientes:
        solicitud["intervinientes"] = intervinientes

    if str(values.get("destination_plant", "")).strip():
        solicitud["destino"]["planta"] = _integer(
            values, "destination_plant", minimum=1, maximum=999999
        )

    domains = [
        domain.strip().upper()
        for domain in re.split(r"[\n,;]+", str(values.get("domains", "")))
        if domain.strip()
    ]
    if not 1 <= len(domains) <= 3:
        _invalid("domains", "Enter between one and three vehicle domains.")
    if any(not re.fullmatch(r"[A-Z0-9]{6,7}", domain) for domain in domains):
        _invalid("domains", "Each domain must contain 6 or 7 alphanumeric characters.")
    departure_raw = _required(values, "departure")
    try:
        departure = datetime.fromisoformat(departure_raw)
    except ValueError:
        _invalid("departure", "Enter a valid Argentina local date and time.")
    if departure.tzinfo is not None:
        _invalid("departure", "Send local Argentina time without a UTC offset.")
    distance = _integer(values, "distance_km", minimum=1, maximum=99999)
    turn_code = values.get("turn_code", "").strip()
    if turn_code and not re.fullmatch(r"[A-Za-z0-9 _/-]{1,30}", turn_code):
        _invalid("turn_code", "Turn code contains unsupported characters or exceeds 30 characters.")
    fare_raw = values.get("fare", "").strip()
    transport: dict[str, Any] = {
        "cuitTransportista": _cuit(values, "carrier_cuit"),
        "dominio": domains,
        "fechaHoraPartida": departure,
        "kmRecorrer": distance,
        "cuitChofer": _cuit(values, "driver_cuit"),
        "cuitPagadorFlete": _cuit(values, "freight_payer_cuit"),
        "mercaderiaFumigada": not _boolean(values, "fumigated"),
    }
    if turn_code:
        transport["codigoTurno"] = turn_code
    if fare_raw:
        try:
            fare = Decimal(fare_raw)
        except InvalidOperation:
            _invalid("fare", "Enter a valid fare.")
        if not fare.is_finite() or fare < 0 or fare > Decimal("99999.99") or fare.as_tuple().exponent < -2:
            _invalid("fare", "Fare allows up to five integer digits and two decimals.")
        transport["tarifa"] = fare
    intermediary = _cuit(values, "freight_intermediary_cuit", required=False)
    if intermediary is not None:
        transport["cuitIntermediarioFlete"] = intermediary
    solicitud["transporte"] = transport

    observations = str(values.get("observations", ""))
    if len(observations) > 2000:
        _invalid("observations", "Observations cannot exceed 2,000 characters.")
    if observations:
        solicitud["observaciones"] = observations
    return solicitud
