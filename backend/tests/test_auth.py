from app.schemas.auth import LoginRequest


def test_login_request_accepts_local_email_domain():
    payload = {"email": "admin@ulpf.local", "password": "ChangeMe_Admin123!"}
    req = LoginRequest.model_validate(payload)
    assert req.email == payload["email"]
    assert req.password == payload["password"]


def test_bootstrap_admin_can_login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "AdminTestPass123!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
