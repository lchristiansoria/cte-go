from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
import pytest

from ctg_go.modules.arca import client as arca_client_module
from ctg_go.modules.arca.client import (
    ArcaCPEClient,
    ArcaConfigurationError,
    ArcaServiceError,
    ArcaSettings,
)
from ctg_go.modules.arca.router import get_arca_client


class FakeArcaClient:
    def __init__(self) -> None:
        self.last_query: tuple[str, dict[str, Any]] | None = None
        self.fail = False

    def _query(self, method: str, **kwargs: Any) -> dict[str, Any]:
        self.last_query = (method, kwargs)
        if self.fail:
            raise ArcaServiceError("sensitive provider detail")
        return {"result": "ok"}

    def consultar_provincias(self) -> dict[str, Any]:
        return self._query("provincias")

    def consultar_localidades(self, cod_provincia: int) -> dict[str, Any]:
        return self._query("localidades", cod_provincia=cod_provincia)

    def consultar_tipos_grano(self) -> dict[str, Any]:
        return self._query("tipos_grano")

    def consultar_tipos_embalaje(self) -> dict[str, Any]:
        return self._query("tipos_embalaje")

    def consultar_unidades_medida(self) -> dict[str, Any]:
        return self._query("unidades_medida")

    def consultar_plantas(self, cuit: str | None = None) -> dict[str, Any]:
        return self._query("plantas", cuit=cuit)

    def consultar_ultimo_nro_orden(self, sucursal: int, tipo_cpe: int) -> dict[str, Any]:
        return self._query("ultimo_nro_orden", sucursal=sucursal, tipo_cpe=tipo_cpe)

    def consultar_cpe_automotor(self, **kwargs: Any) -> dict[str, Any]:
        return self._query("cpe_automotor", **kwargs)


def test_arca_query_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/arca/provincias")

    assert response.status_code == 401


def test_settings_reject_insecure_wsdl_urls(monkeypatch) -> None:
    for name, value in {
        "URL_ARCA_WSAA": "http://arca.test/wsaa?wsdl",
        "URL_ARCA_WS": "https://arca.test/wscpe?wsdl",
        "CUIT_ARCA": "20123456789",
        "CERT_ARCA_BASE64": "certificate",
        "KEY_ARCA_BASE64": "private-key",
    }.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ArcaConfigurationError, match="HTTPS"):
        ArcaSettings.from_env()


def test_settings_accept_optional_default_branch(monkeypatch) -> None:
    for name, value in {
        "URL_ARCA_WSAA": "https://arca.test/wsaa?wsdl",
        "URL_ARCA_WS": "https://arca.test/wscpe?wsdl",
        "CUIT_ARCA": "20123456789",
        "CERT_ARCA_BASE64": "certificate",
        "KEY_ARCA_BASE64": "private-key",
        "SUCURSAL_ARCA": "123",
    }.items():
        monkeypatch.setenv(name, value)

    assert ArcaSettings.from_env().default_branch == 123


def test_arca_provincias_query(client: TestClient, auth_header) -> None:
    fake = FakeArcaClient()
    client.app.dependency_overrides[get_arca_client] = lambda: fake

    response = client.get(
        "/api/v1/arca/provincias", headers=auth_header("op1")
    )

    assert response.status_code == 200
    assert response.json() == {"result": "ok"}
    assert fake.last_query == ("provincias", {})


def test_arca_cpe_query_requires_complete_order_identifier(
    client: TestClient, auth_header
) -> None:
    fake = FakeArcaClient()
    client.app.dependency_overrides[get_arca_client] = lambda: fake

    response = client.get(
        "/api/v1/arca/cpes/automotor?tipo_cpe=1",
        headers=auth_header("op1"),
    )

    assert response.status_code == 422
    assert fake.last_query is None


def test_arca_cpe_query_passes_ctg(client: TestClient, auth_header) -> None:
    fake = FakeArcaClient()
    client.app.dependency_overrides[get_arca_client] = lambda: fake

    response = client.get(
        "/api/v1/arca/cpes/automotor?nro_ctg=123456789",
        headers=auth_header("op1"),
    )

    assert response.status_code == 200
    assert fake.last_query == (
        "cpe_automotor",
        {
            "cuit_solicitante": None,
            "tipo_cpe": None,
            "sucursal": None,
            "nro_orden": None,
            "nro_ctg": 123456789,
        },
    )


def test_arca_provider_errors_are_not_returned_to_client(
    client: TestClient, auth_header
) -> None:
    fake = FakeArcaClient()
    fake.fail = True
    client.app.dependency_overrides[get_arca_client] = lambda: fake

    response = client.get(
        "/api/v1/arca/provincias", headers=auth_header("op1")
    )

    assert response.status_code == 502
    assert response.json()["message"] == "ARCA query failed."
    assert "sensitive provider detail" not in response.text


def test_client_authenticates_and_queries_wscpe(monkeypatch) -> None:
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
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    private_key_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    settings = ArcaSettings(
        wsaa_wsdl="wsaa-test",
        wscpe_wsdl="wscpe-test",
        cuit="20123456789",
        certificate_base64=base64.b64encode(certificate_pem).decode("ascii"),
        private_key_base64=base64.b64encode(private_key_pem).decode("ascii"),
    )
    calls: list[tuple[str, dict[str, Any]]] = []

    class WsaaService:
        def loginCms(self, cms: str) -> str:
            assert base64.b64decode(cms)
            expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            return (
                "<loginTicketResponse><credentials><token>token</token>"
                f"<sign>sign</sign></credentials><expirationTime>{expires}</expirationTime>"
                "</loginTicketResponse>"
            )

    class WscpeService:
        def consultarLocalidadesPorProvincia(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("consultarLocalidadesPorProvincia", kwargs))
            return {"localidades": ["localidad"]}

    def fake_soap_client(*, wsdl: str, transport: Any) -> Any:
        service = WsaaService() if wsdl == "wsaa-test" else WscpeService()
        return SimpleNamespace(service=service)

    monkeypatch.setattr(arca_client_module, "Client", fake_soap_client)
    client = ArcaCPEClient(settings)

    result = client.consultar_localidades(6)

    assert result == {"localidades": ["localidad"]}
    assert calls == [
        (
            "consultarLocalidadesPorProvincia",
            {
                "auth": {
                    "token": "token",
                    "sign": "sign",
                    "cuitRepresentada": 20123456789,
                },
                "solicitud": {"codProvincia": 6},
            },
        )
    ]
