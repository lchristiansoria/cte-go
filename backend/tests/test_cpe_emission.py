import base64
from uuid import UUID

from fastapi.testclient import TestClient

from ctg_go.modules.arca.client import ArcaServiceError
from ctg_go.modules.arca.router import get_arca_client
from ctg_go.modules.cpe.models import CPEDraft


FORM = {
    "requester_cuit": "20361814305",
    "branch": "1",
    "origin_mode": "producer",
    "origin_province": "4",
    "origin_locality": "12",
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
    "domains": "AJV636\nGRP753",
    "departure": "2026-10-31T12:30",
    "distance_km": "220",
    "driver_cuit": "20361814305",
    "freight_payer_cuit": "20361814305",
    "fumigated": "false",
}


class FakeArca:
    def __init__(self, *, uncertain=False):
        self.uncertain = uncertain
        self.authorization_calls = []
        self.lookups = []

    def consultar_ultimo_nro_orden(self, branch, type_cpe):
        assert (branch, type_cpe) == (1, 74)
        return {"respuesta": {"nroOrden": 16}}

    def autorizar_cpe_automotor(self, solicitud):
        self.authorization_calls.append(solicitud)
        if self.uncertain:
            raise ArcaServiceError("timeout", uncertain=True)
        return {
            "respuesta": {
                "cabecera": {"nroOrden": 17, "nroCTG": 123456789, "estado": "AC"},
                "pdf": base64.b64encode(b"%PDF-test").decode(),
            }
        }

    def consultar_cpe_automotor(self, **kwargs):
        self.lookups.append(kwargs)
        return {"respuesta": {"errores": {"error": [{"codigo": "1302", "descripcion": "No existe"}]}}}


def _set_form(client: TestClient) -> str:
    cpe_id = client.app.state.seed_ids["cpe1"]
    session = client.app.state.session_factory()
    try:
        cpe = session.get(CPEDraft, UUID(cpe_id))
        assert cpe is not None
        cpe.payload_json = {"cpe": FORM}
        session.commit()
    finally:
        session.close()
    return cpe_id


def test_emit_persists_response_pdf_and_does_not_send_twice(client, auth_header):
    arca = FakeArca()
    client.app.dependency_overrides[get_arca_client] = lambda: arca
    cpe_id = _set_form(client)

    first = client.post(f"/api/v1/cpes/{cpe_id}/emit", headers=auth_header("op1"))
    second = client.post(f"/api/v1/cpes/{cpe_id}/emit", headers=auth_header("op1"))

    assert first.status_code == 200
    assert first.json()["emission"]["nroCTG"] == 123456789
    assert second.status_code == 200
    assert len(arca.authorization_calls) == 1
    assert arca.authorization_calls[0]["cabecera"]["nroOrden"] == 17
    pdf = client.get(f"/api/v1/cpes/{cpe_id}/pdf", headers=auth_header("op1"))
    assert pdf.status_code == 200
    assert pdf.content == b"%PDF-test"


def test_uncertain_emission_is_looked_up_and_never_resent(client, auth_header):
    arca = FakeArca(uncertain=True)
    client.app.dependency_overrides[get_arca_client] = lambda: arca
    cpe_id = _set_form(client)

    first = client.post(f"/api/v1/cpes/{cpe_id}/emit", headers=auth_header("op1"))
    second = client.post(f"/api/v1/cpes/{cpe_id}/emit", headers=auth_header("op1"))

    assert first.status_code == 502
    assert first.json()["code"] == "emission_uncertain"
    assert second.status_code == 409
    assert second.json()["code"] == "emission_uncertain"
    assert len(arca.authorization_calls) == 1
    assert len(arca.lookups) == 1
    assert arca.lookups[0]["nro_orden"] == 17
