from __future__ import annotations

import base64
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from sqlalchemy import select

from ctg_go.modules.arca import client as arca_client_module
from ctg_go.modules.arca.client import ArcaCPEClient, ArcaServiceError, ArcaSettings
from ctg_go.modules.arca.models import ArcaCuit, ArcaCuitDataset
from ctg_go.modules.arca.router import get_arca_client
from ctg_go.modules.arca.services import extract_items, is_valid_cuit, valid_harvests


def make_cuit(prefix: str) -> str:
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    digit = 11 - sum(int(v) * w for v, w in zip(prefix, weights)) % 11
    return prefix + str(0 if digit == 11 else 9 if digit == 10 else digit)


CUIT_A = make_cuit("2011111111")
CUIT_B = make_cuit("3022222222")


class FakeScoped:
    def __init__(self, parent: FakeArca, cuit: str) -> None:
        self.parent = parent
        self.cuit = cuit

    def _fail_or(self, value: Any) -> Any:
        error = self.parent.errors.get(self.cuit)
        if error is not None:
            raise error
        return value

    def consultar_domicilios_por_cuit(self) -> dict[str, Any]:
        return self._fail_or({"domicilio": [{"tipo": 1, "orden": 1, "descripcion": f"dom {self.cuit}"}]})

    def consultar_plantas(self) -> dict[str, Any]:
        return self._fail_or({"planta": [{"nroPlanta": 1, "cuit": self.cuit}]})

    def consultar_localidades_productor(self) -> dict[str, Any]:
        if self.parent.fail_localidades:
            raise ArcaServiceError("x", kind="business", errors=[{"code": "9", "description": "boom"}])
        return {"localidad": [{"codigo": "1", "descripcion": "L", "coordenadas": None}]}

    def consultar_renspa(self, cod_provincia: int) -> dict[str, Any]:
        return {"renspa": [{"nroRenspa": f"{self.cuit}-{cod_provincia}", "descripcion": "x"}]}


class FakeArca:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(environment="homologacion", default_branch=None)
        self.errors: dict[str, ArcaServiceError] = {}
        self.fail_localidades = False
        self.scoped_calls: list[str] = []

    def for_cuit(self, cuit: str) -> FakeScoped:
        self.scoped_calls.append(cuit)
        return FakeScoped(self, cuit)

    def consultar_provincias(self) -> dict[str, Any]:
        return {"provincia": [{"codigo": 1, "descripcion": "BA"}]}

    def consultar_tipos_grano(self) -> dict[str, Any]:
        return {"grano": [{"codigo": 23, "descripcion": "Soja"}]}

    def consultar_tipos_embalaje(self) -> dict[str, Any]:
        return {"embalaje": []}

    def consultar_unidades_medida(self) -> dict[str, Any]:
        return {"unidad": []}


def _setup(client: TestClient) -> FakeArca:
    fake = FakeArca()
    client.app.dependency_overrides[get_arca_client] = lambda: fake
    return fake


def _register(client: TestClient, auth_header, cuit: str = CUIT_A, user: str = "admin1") -> dict:
    response = client.post(
        "/api/v1/arca/cuits", json={"cuit": cuit, "label": "Cliente"}, headers=auth_header(user)
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_requires_admin_and_valid_cuit(client: TestClient, auth_header) -> None:
    _setup(client)
    forbidden = client.post("/api/v1/arca/cuits", json={"cuit": CUIT_A}, headers=auth_header("op1"))
    assert forbidden.status_code == 403
    bad = client.post("/api/v1/arca/cuits", json={"cuit": "20111111111"}, headers=auth_header("admin1"))
    assert bad.status_code == 422
    created = _register(client, auth_header)
    assert created["delegation_status"] == "unverified"
    assert created["environment"] == "homologacion"
    duplicate = client.post("/api/v1/arca/cuits", json={"cuit": CUIT_A}, headers=auth_header("admin1"))
    assert duplicate.status_code == 422


def test_operator_only_sees_granted_cuits_and_other_org_sees_none(client: TestClient, auth_header) -> None:
    _setup(client)
    created = _register(client, auth_header)
    cuit_id = created["id"]
    seed = client.app.state.seed_ids

    assert client.get("/api/v1/arca/cuits", headers=auth_header("op1")).json() == []
    assert client.get(f"/api/v1/arca/cuits/{cuit_id}", headers=auth_header("op1")).status_code == 404

    granted = client.put(
        f"/api/v1/arca/cuits/{cuit_id}/grants",
        json={"user_ids": [seed["op1"]]},
        headers=auth_header("admin1"),
    )
    assert granted.status_code == 200
    assert [row["id"] for row in client.get("/api/v1/arca/cuits", headers=auth_header("op1")).json()] == [cuit_id]
    assert client.get(f"/api/v1/arca/cuits/{cuit_id}", headers=auth_header("op2")).status_code == 404
    assert client.get("/api/v1/arca/cuits", headers=auth_header("admin2")).json() == []
    assert client.get(f"/api/v1/arca/cuits/{cuit_id}", headers=auth_header("admin2")).status_code == 404

    unknown = client.put(
        f"/api/v1/arca/cuits/{cuit_id}/grants",
        json={"user_ids": [seed["admin2"]]},
        headers=auth_header("admin1"),
    )
    assert unknown.status_code == 422


def test_verify_marks_missing_delegation_with_arca_errors(client: TestClient, auth_header) -> None:
    fake = _setup(client)
    fake.errors[CUIT_B] = ArcaServiceError(
        "provider detail", kind="business", errors=[{"code": "1234", "description": "Sin autorizacion"}]
    )
    ok = _register(client, auth_header, CUIT_A)
    denied = _register(client, auth_header, CUIT_B)

    verified = client.post(f"/api/v1/arca/cuits/{ok['id']}/verify", headers=auth_header("admin1"))
    rejected = client.post(f"/api/v1/arca/cuits/{denied['id']}/verify", headers=auth_header("admin1"))

    assert verified.json()["delegation_status"] == "verified"
    assert rejected.json()["delegation_status"] == "rejected"
    assert rejected.json()["last_errors"] == [{"code": "1234", "description": "Sin autorizacion"}]
    assert "provider detail" not in rejected.text
    assert fake.scoped_calls == [CUIT_A, CUIT_B]


def test_uncertain_verification_keeps_previous_status(client: TestClient, auth_header) -> None:
    fake = _setup(client)
    record = _register(client, auth_header)
    client.post(f"/api/v1/arca/cuits/{record['id']}/verify", headers=auth_header("admin1"))
    fake.errors[CUIT_A] = ArcaServiceError("timeout", uncertain=True)

    body = client.post(f"/api/v1/arca/cuits/{record['id']}/verify", headers=auth_header("admin1")).json()

    assert body["delegation_status"] == "verified"
    assert body["last_error_kind"] == "uncertain"


def test_sync_stores_data_per_cuit_without_mixing(client: TestClient, auth_header) -> None:
    _setup(client)
    a = _register(client, auth_header, CUIT_A)
    b = _register(client, auth_header, CUIT_B)

    for record in (a, b):
        result = client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1"))
        assert result.status_code == 200
        assert result.json()["datasets"] == {
            "domicilios": "ok",
            "plantas": "ok",
            "localidades_productor": "ok",
        }

    plantas_a = client.get(f"/api/v1/arca/cuits/{a['id']}/datasets/plantas", headers=auth_header("admin1")).json()
    plantas_b = client.get(f"/api/v1/arca/cuits/{b['id']}/datasets/plantas", headers=auth_header("admin1")).json()
    assert plantas_a["items"] == [{"nroPlanta": 1, "cuit": CUIT_A}]
    assert plantas_b["items"] == [{"nroPlanta": 1, "cuit": CUIT_B}]
    assert plantas_a["stale"] is False


def test_sync_does_not_touch_data_when_delegation_is_rejected(client: TestClient, auth_header) -> None:
    fake = _setup(client)
    fake.errors[CUIT_A] = ArcaServiceError("x", kind="fault")
    record = _register(client, auth_header)

    result = client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1")).json()

    assert result["delegation"] == "rejected"
    assert result["datasets"] == {}


def test_failed_dataset_keeps_previous_payload(client: TestClient, auth_header) -> None:
    fake = _setup(client)
    record = _register(client, auth_header)
    client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1"))
    fake.fail_localidades = True

    result = client.post(
        f"/api/v1/arca/cuits/{record['id']}/sync",
        json={"datasets": ["localidades_productor"]},
        headers=auth_header("admin1"),
    ).json()
    data = client.get(
        f"/api/v1/arca/cuits/{record['id']}/datasets/localidades_productor", headers=auth_header("admin1")
    ).json()

    assert result["datasets"] == {"localidades_productor": "error"}
    assert data["errors"] == [{"code": "9", "description": "boom"}]
    assert len(data["items"]) == 1
    assert data["synced_at"] is not None


def test_sync_rejects_unknown_dataset(client: TestClient, auth_header) -> None:
    _setup(client)
    record = _register(client, auth_header)
    response = client.post(
        f"/api/v1/arca/cuits/{record['id']}/sync",
        json={"datasets": ["nope"]},
        headers=auth_header("admin1"),
    )
    assert response.status_code == 422


def test_stale_dataset_is_flagged(client: TestClient, auth_header) -> None:
    _setup(client)
    record = _register(client, auth_header)
    client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1"))
    session = client.app.state.session_factory()
    try:
        for row in session.scalars(select(ArcaCuitDataset)):
            row.synced_at = datetime.now(timezone.utc) - timedelta(days=2)
        session.commit()
    finally:
        session.close()

    data = client.get(f"/api/v1/arca/cuits/{record['id']}/datasets/plantas", headers=auth_header("admin1")).json()

    assert data["stale"] is True


def test_emission_context_blocks_until_verified_and_catalogs_synced(client: TestClient, auth_header) -> None:
    _setup(client)
    record = _register(client, auth_header)
    url = f"/api/v1/arca/cuits/{record['id']}/emission-context"

    before = client.get(url, headers=auth_header("admin1")).json()
    assert before["ready"] is False
    assert {b["code"] for b in before["blockers"]} == {
        "delegation_not_verified",
        "provincias_missing",
        "tipos_grano_missing",
    }

    client.post("/api/v1/arca/catalogs/sync", headers=auth_header("op1"))
    client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1"))
    after = client.get(url, headers=auth_header("admin1")).json()

    assert after["ready"] is True
    assert after["harvests"]["confirmed_by_arca"] is False
    assert len(after["harvests"]["items"]) == 10


def test_catalog_read_and_renspa_live(client: TestClient, auth_header) -> None:
    _setup(client)
    record = _register(client, auth_header)
    client.post("/api/v1/arca/catalogs/sync", headers=auth_header("op1"))

    catalog = client.get("/api/v1/arca/catalogs/provincias", headers=auth_header("op1")).json()
    renspa = client.get(
        f"/api/v1/arca/cuits/{record['id']}/renspa?cod_provincia=3", headers=auth_header("admin1")
    ).json()

    assert catalog["items"] == [{"codigo": 1, "descripcion": "BA"}]
    assert renspa["items"] == [{"nroRenspa": f"{CUIT_A}-3", "descripcion": "x"}]
    assert client.get("/api/v1/arca/catalogs/unknown", headers=auth_header("op1")).status_code == 404


def test_delete_cuit_removes_synced_data(client: TestClient, auth_header) -> None:
    _setup(client)
    record = _register(client, auth_header)
    client.post(f"/api/v1/arca/cuits/{record['id']}/sync", headers=auth_header("admin1"))

    assert client.delete(f"/api/v1/arca/cuits/{record['id']}", headers=auth_header("op1")).status_code == 403
    assert client.delete(f"/api/v1/arca/cuits/{record['id']}", headers=auth_header("admin1")).status_code == 204
    session = client.app.state.session_factory()
    try:
        assert session.scalars(select(ArcaCuit)).all() == []
        assert session.scalars(select(ArcaCuitDataset)).all() == []
    finally:
        session.close()


def test_pure_helpers() -> None:
    assert is_valid_cuit(CUIT_A) and not is_valid_cuit("20111111111")
    harvests = valid_harvests(date(2026, 11, 1))
    assert harvests[0]["code"] == 2627 and harvests[-1]["code"] == 1718
    assert valid_harvests(date(2026, 3, 1))[0]["code"] == 2526
    assert extract_items({"planta": None, "errores": None}) == []
    assert extract_items({"planta": {"a": 1}}) == [{"a": 1}]


def test_environment_detection_and_override() -> None:
    base = {"cuit": "20123456789", "certificate_base64": "", "private_key_base64": ""}
    qa = ArcaSettings(wsaa_wsdl="https://wsaahomo.afip.gov.ar/ws", wscpe_wsdl="https://cpea-ws-qaext.afip.gob.ar/x", **base)
    prod = ArcaSettings(wsaa_wsdl="https://wsaa.afip.gov.ar/ws", wscpe_wsdl="https://cpea-ws.afip.gob.ar/x", **base)
    forced = ArcaSettings(wsaa_wsdl="a", wscpe_wsdl="b", environment_override="homologacion", **base)
    assert (qa.environment, prod.environment, forced.environment) == ("homologacion", "produccion", "homologacion")


def test_real_client_scopes_cuit_representada_and_shares_ticket(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    settings = ArcaSettings(
        wsaa_wsdl="wsaa-test",
        wscpe_wsdl="wscpe-test",
        cuit="20123456789",
        certificate_base64=base64.b64encode(certificate.public_bytes(serialization.Encoding.PEM)).decode(),
        private_key_base64=base64.b64encode(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        ).decode(),
    )
    logins: list[str] = []
    calls: list[tuple[str, dict[str, Any]]] = []

    class Wsaa:
        def loginCms(self, cms: str) -> str:
            logins.append(cms)
            expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            return (
                "<r><token>t</token><sign>s</sign>"
                f"<expirationTime>{expires}</expirationTime></r>"
            )

    class Wscpe:
        def consultarDomiciliosPorCUIT(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("dom", kwargs))
            return {"domicilio": []}

        def consultarRenspa(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("renspa", kwargs))
            return {"renspa": []}

        def dummy(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("dummy", kwargs))
            return {"appserver": "OK"}

    monkeypatch.setattr(
        arca_client_module,
        "Client",
        lambda *, wsdl, transport: SimpleNamespace(service=Wsaa() if wsdl == "wsaa-test" else Wscpe()),
    )
    root = ArcaCPEClient(settings)

    root.for_cuit("20111111118").consultar_domicilios_por_cuit()
    root.for_cuit("30222222227").consultar_renspa(5)
    root.dummy()

    assert len(logins) == 1
    assert calls[0] == (
        "dom",
        {"auth": {"token": "t", "sign": "s", "cuitRepresentada": 20111111118}, "cuit": 20111111118},
    )
    assert calls[1][1]["auth"]["cuitRepresentada"] == 30222222227
    assert calls[1][1]["codProvincia"] == 5 and calls[1][1]["cuit"] == 30222222227
    assert calls[2] == ("dummy", {})
