from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    workspace_name: str | None = None
    role: str = "ADMIN"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: str | None = None
    tenant_name: str | None = None


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: list[str]
    tenant_id: str = "default"
    tenant_name: str = "Default Workspace"

class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_devices: bool = False  # reserved; not implemented yet