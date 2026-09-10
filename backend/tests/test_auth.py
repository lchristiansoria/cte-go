def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "op1@test.local", "password": "op1pass"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
