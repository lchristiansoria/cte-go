def test_client_abm_flow(client, auth_header):
    h = auth_header("op1")
    created = client.post(
        "/api/v1/clients",
        json={"cuit": "30111111111", "business_name": "Nuevo SA", "alias": "N"},
        headers=h,
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    updated = client.put(
        f"/api/v1/clients/{cid}",
        json={"cuit": "30111111111", "business_name": "Nuevo SRL", "alias": None},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["business_name"] == "Nuevo SRL"
    assert client.get(f"/api/v1/clients/{cid}", headers=h).json()["alias"] is None

    assert client.delete(f"/api/v1/clients/{cid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/clients/{cid}", headers=h).status_code == 404


def test_update_rejects_duplicate_cuit(client, auth_header):
    h = auth_header("op1")
    other = client.post(
        "/api/v1/clients", json={"cuit": "30111111111", "business_name": "Otro"}, headers=h
    ).json()
    resp = client.put(
        f"/api/v1/clients/{other['id']}",
        json={"cuit": "20123456789", "business_name": "Otro"},
        headers=h,
    )
    assert resp.status_code == 422


def test_delete_client_with_gestions_conflicts(client, auth_header):
    cid = client.app.state.seed_ids["client1"]
    resp = client.delete(f"/api/v1/clients/{cid}", headers=auth_header("admin1"))
    assert resp.status_code == 409


def test_client_cpes_and_cross_org_isolation(client, auth_header):
    cid = client.app.state.seed_ids["client1"]
    resp = client.get(f"/api/v1/clients/{cid}/cpes", headers=auth_header("op1"))
    assert resp.status_code == 200
    body = resp.json()
    assert [c["id"] for c in body] == [client.app.state.seed_ids["cpe1"]]
    assert body[0]["gestion_code"] == "G-001"

    for method, url in (("get", f"/api/v1/clients/{cid}"), ("get", f"/api/v1/clients/{cid}/cpes")):
        assert getattr(client, method)(url, headers=auth_header("admin2")).status_code == 404
    assert client.delete(f"/api/v1/clients/{cid}", headers=auth_header("admin2")).status_code == 404
