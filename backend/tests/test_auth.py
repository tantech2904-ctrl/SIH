from app.schemas.auth import LoginRequest


def test_login_request_accepts_local_email_domain():
    payload = {"email": "admin@ulpf.local", "password": "ChangeMe_Admin123!"}
    req = LoginRequest.model_validate(payload)
    assert req.email == payload["email"]
    assert req.password == payload["password"]
