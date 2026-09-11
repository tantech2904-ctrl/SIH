from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.db.session import get_db
from app.models.user import User, Role
from app.schemas.auth import LoginRequest, TokenResponse, MeResponse, RegisterRequest
from app.services.audit_service import record_audit

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        record_audit(db, actor=body.email, action="LOGIN_FAILED", resource="user",
                     resource_id=body.email,
                     source_ip=request.client.host if request.client else None,
                     user_agent=request.headers.get("user-agent"))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    roles = user.role_names()
    access = create_access_token(user.email, roles)
    refresh = create_refresh_token(user.email)
    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, actor=user.email, action="LOGIN_SUCCESS", resource="user",
                 resource_id=user.id, source_ip=request.client.host if request.client else None,
                 user_agent=request.headers.get("user-agent"))
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, token_type="bearer")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def refresh(request: Request, body: dict, db: Session = Depends(get_db)):
    token = body.get("refresh_token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Missing refresh_token")
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")
    roles = user.role_names()
    return TokenResponse(
        access_token=create_access_token(user.email, roles),
        refresh_token=create_refresh_token(user.email),
        token_type="bearer",
    )


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record_audit(db, actor=user.email, action="LOGOUT", resource="user", resource_id=user.id)
    db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id, email=user.email, full_name=user.full_name, roles=user.role_names(),
    )


@router.post("/register", response_model=MeResponse, status_code=201)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Registration is restricted — only allowed if no users exist (bootstrap)
    or by an ADMIN. We default to bootstrap-only to avoid open registration."""
    count = db.query(User).count()
    if count > 0:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    role = db.query(Role).filter(Role.name == "ADMIN").first()
    if not role:
        role = Role(name="ADMIN", description="Administrator")
        db.add(role)
        db.flush()
    u = User(email=body.email, password_hash=hash_password(body.password),
             full_name=body.full_name or body.email.split("@")[0], is_active=True)
    u.roles = [role]
    db.add(u)
    record_audit(db, actor=body.email, action="USER_CREATED", resource="user",
                 resource_id=body.email, new_state={"roles": ["ADMIN"]})
    db.commit()
    return MeResponse(id=u.id, email=u.email, full_name=u.full_name, roles=[role.name])