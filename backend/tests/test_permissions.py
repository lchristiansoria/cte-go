def test_operator_can_read_but_not_edit_if_not_responsible(client, auth_header):
    cpe_id = client.app.state.seed_ids["cpe1"]

    read = client.get(f"/api/v1/cpes/{cpe_id}", headers=auth_header("op2"))
    assert read.status_code == 200

    edit = client.patch(
        f"/api/v1/cpes/{cpe_id}",
        json={"expected_version": 2, "title": "Nuevo"},
        headers=auth_header("op2"),
    )
    assert edit.status_code == 403
    assert edit.json()["code"] == "forbidden"


def test_cross_org_cpe_hidden_as_not_found(client, auth_header):
    cpe_id = client.app.state.seed_ids["cpe1"]
    response = client.get(f"/api/v1/cpes/{cpe_id}", headers=auth_header("admin2"))
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
