from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from ctg_go.modules.arca.client import ArcaServiceError
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

    def consultar_plantas(self, cuit: str | None = None) -> dict[str, Any]:
        return self._query("plantas", cuit=cuit)

    def consultar_ultimo_nro_orden(self, sucursal: int, tipo_cpe: int) -> dict[str, Any]:
        return self._query("ultimo_nro_orden", sucursal=sucursal, tipo_cpe=tipo_cpe)

    def consultar_cpe_automotor(self, **kwargs: Any) -> dict[str, Any]:
        return self._query("cpe_automotor", **kwargs)


def test_arca_query_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/arca/provincias")

    assert response.status_code == 401


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
