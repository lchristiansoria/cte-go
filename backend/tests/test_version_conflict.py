def test_patch_requires_expected_version(client, auth_header):
    cpe_id = client.app.state.seed_ids["cpe1"]

    conflict = client.patch(
        f"/api/v1/cpes/{cpe_id}",
        json={"expected_version": 1, "title": "Cambio"},
        headers=auth_header("op1"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "version_conflict"

    ok = client.patch(
        f"/api/v1/cpes/{cpe_id}",
        json={"expected_version": 2, "title": "Cambio válido"},
        headers=auth_header("op1"),
    )
    assert ok.status_code == 200
    assert ok.json()["version"] == 3
