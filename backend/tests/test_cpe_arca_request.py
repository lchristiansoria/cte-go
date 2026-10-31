import pytest

from ctg_go.api.errors import ApiError
from ctg_go.modules.cpe.arca_request import build_automotor_request


@pytest.fixture
def form():
    return {
        "requester_cuit": "20361814305",
        "branch": "1",
        "origin_mode": "producer",
        "origin_province": "4",
        "origin_locality": "12",
        "origin_renspa": "06.123.1.12345/06",
        "origin_latitude": "-32.625",
        "origin_longitude": "-62.6888889",
        "corresponds_producer_withdrawal": "false",
        "applicant_is_field": "false",
        "grain_code": "1",
        "harvest": "2526",
        "gross_weight": "45000",
        "tare_weight": "14500",
        "destination_cuit": "30709590894",
        "destination_is_field": "false",
        "destination_province": "4",
        "destination_locality": "12",
        "destination_plant": "19265",
        "recipient_cuit": "30700869918",
        "carrier_cuit": "20361814305",
        "domains": "ajv636\nGRP753",
        "departure": "2026-10-31T12:30",
        "distance_km": "220",
        "driver_cuit": "20361814305",
        "fare": "38000",
        "freight_payer_cuit": "20361814305",
        "freight_intermediary_cuit": "",
        "fumigated": "false",
        "observations": "KILOS ESTIMADOS",
    }


def test_maps_form_values_to_documented_automotor_request(form):
    request = build_automotor_request(form, nro_orden=17)

    assert request["cabecera"] == {
        "tipoCP": 74,
        "cuitSolicitante": 20361814305,
        "sucursal": 1,
        "nroOrden": 17,
    }
    assert request["origen"]["productor"]["coordenadasGPS"] == {
        "latitud": {"grados": -32, "minutos": 37, "segundos": 30},
        "longitud": {"grados": -62, "minutos": 41, "segundos": 20},
    }
    assert request["datosCarga"] == {
        "codGrano": 1,
        "cosecha": 2526,
        "pesoBruto": 45000,
        "pesoTara": 14500,
    }
    assert request["destino"] == {
        "cuit": 30709590894,
        "esDestinoCampo": False,
        "codProvincia": 4,
        "codLocalidad": 12,
        "planta": 19265,
    }
    assert request["destinatario"] == {"cuit": 30700869918}
    assert request["transporte"]["dominio"] == ["AJV636", "GRP753"]
    assert request["transporte"]["fechaHoraPartida"].isoformat() == "2026-10-31T12:30:00"
    assert request["transporte"]["mercaderiaFumigada"] is True
    assert request["observaciones"] == "KILOS ESTIMADOS"
    assert "pesoNeto" not in request["datosCarga"]


def test_optional_interveners_and_zero_values_preserve_contract_distinctions(form):
    form["gross_weight"] = "0"
    form["tare_weight"] = "0"
    form["corresponds_producer_withdrawal"] = "false"
    form["applicant_is_field"] = "false"
    form["fumigated"] = "true"

    request = build_automotor_request(form, nro_orden=1)

    assert request["datosCarga"]["pesoBruto"] == 0
    assert request["datosCarga"]["pesoTara"] == 0
    assert request["correspondeRetiroProductor"] is False
    assert request["esSolicitanteCampo"] is False
    assert request["transporte"]["mercaderiaFumigada"] is False
    assert "retiroProductor" not in request
    assert "intervinientes" not in request
    assert "tarifa" not in request
    assert "cuitIntermediarioFlete" not in request["transporte"]


def test_operator_origin_and_documented_intervener_names(form):
    form.update(
        origin_mode="operator",
        origin_plant="7",
        origin_renspa="",
        origin_latitude="",
        origin_longitude="",
        corresponds_producer_withdrawal="true",
        withdrawal_coe="12345",
        withdrawal_producer_cuit="20361814305",
        role_primary_seller="20361814305",
        role_receiving_representative="30709590894",
    )

    request = build_automotor_request(form, nro_orden=2)

    assert request["origen"] == {
        "operador": {"codProvincia": 4, "codLocalidad": 12, "planta": 7}
    }
    assert request["retiroProductor"] == {
        "certificadoCOE": 12345,
        "cuitRemitenteComercialProductor": 20361814305,
    }
    assert request["intervinientes"] == {
        "cuitRemitenteComercialVentaPrimaria": 20361814305,
        "cuitRepresentanteRecibidor": 30709590894,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requester_cuit", "20361814304"),
        ("harvest", "252"),
        ("gross_weight", "88001"),
        ("domains", "TOOLONG8"),
        ("distance_km", "0"),
        ("observations", "x" * 2001),
    ],
)
def test_rejects_values_outside_manual_contract(form, field, value):
    form[field] = value
    with pytest.raises(ApiError) as error:
        build_automotor_request(form, nro_orden=4)
    assert error.value.status_code == 422
    assert error.value.field_errors[0]["field"] == field


def test_requires_coe_for_producer_withdrawal(form):
    form["corresponds_producer_withdrawal"] = "true"
    form["withdrawal_coe"] = ""
    form["withdrawal_producer_cuit"] = ""
    with pytest.raises(ApiError) as error:
        build_automotor_request(form, nro_orden=4)
    assert error.value.field_errors[0]["field"] == "withdrawal_coe"


def test_clears_previous_origin_mode_data_by_omitting_inapplicable_branch(form):
    form["origin_mode"] = "operator"
    form["origin_plant"] = "9"
    request = build_automotor_request(form, nro_orden=4)
    assert "productor" not in request["origen"]
