from ctg_go.modules.cpe.models import CPEOperation
import uuid


def test_admin_reassigns_with_reason_and_history(client, auth_header):
    cpe_id = client.app.state.seed_ids["cpe1"]
    op2_id = client.app.state.seed_ids["op2"]

    response = client.post(
        f"/api/v1/cpes/{cpe_id}/reassign",
        json={"new_responsible_user_id": op2_id, "reason": "Cobertura"},
        headers=auth_header("admin1"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["responsible_user_id"] == op2_id

    history = client.get(
        f"/api/v1/cpes/{cpe_id}/reassignments",
        headers=auth_header("op1"),
    )
    assert history.status_code == 200
    records = history.json()
    assert len(records) == 1
    assert records[0]["reason"] == "Cobertura"


def test_reassignment_blocked_by_official_operation(client, auth_header):
    cpe_id = client.app.state.seed_ids["cpe1"]

    session = client.app.state.session_factory()
    try:
        session.add(
            CPEOperation(
                organization_id=uuid.UUID(client.app.state.seed_ids["org1"]),
                cpe_draft_id=uuid.UUID(cpe_id),
                status="pending",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post(
        f"/api/v1/cpes/{cpe_id}/reassign",
        json={"new_responsible_user_id": client.app.state.seed_ids["op2"], "reason": "Cambio"},
        headers=auth_header("admin1"),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "reassignment_blocked"
