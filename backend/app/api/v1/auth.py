from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, decode_token_unverified,
    hash_password, verify_password,
)
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User, Role
from app.schemas.auth import (
    LoginRequest, TokenResponse, MeResponse, RegisterRequest, LogoutRequest,
)
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
    tenant_id = getattr(user, "tenant_id", "default") or "default"
    tenant_name = getattr(user, "tenant_name", "Default Workspace") or "Default Workspace"
    access = create_access_token(user.email, roles, tenant_id=tenant_id)
    refresh, jti, expires_at = create_refresh_token(user.email)

    db.add(RefreshToken(
        jti=jti,
        user_email=user.email,
        expires_at=expires_at,
        source_ip=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
    ))
    user.last_login_at = datetime.now(timezone.utc)
    record_audit(db, actor=user.email, action="LOGIN_SUCCESS", resource="user",
                 resource_id=user.id,
                 source_ip=request.client.host if request.client else None,
                 user_agent=request.headers.get("user-agent"),
                 tenant_id=tenant_id)
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        tenant_id=tenant_id,
        tenant_name=tenant_name,
    )


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

    jti = payload.get("jti")
    if not jti:
        # Pre-3.11.7 refresh token — no jti, no DB row. Force re-login.
        raise HTTPException(status_code=401, detail="Refresh token needs re-authentication")

    row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown refresh token")

    if row.used_at is not None:
        # REUSE DETECTED. Revoke every active token for this user.
        now = datetime.now(timezone.utc)
        revoked = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_email == row.user_email,
                RefreshToken.revoked_at.is_(None),
            )
            .update({RefreshToken.revoked_at: now}, synchronize_session=False)
        )
        record_audit(
            db, actor=row.user_email, action="REFRESH_REUSE_DETECTED",
            resource="user", resource_id=row.user_email,
            source_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            new_state={"revoked_count": revoked, "reused_jti": jti},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    if row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user = db.query(User).filter(User.email == row.user_email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    roles = user.role_names()
    now = datetime.now(timezone.utc)

    new_refresh, new_jti, new_expires = create_refresh_token(user.email)
    row.used_at = now
    row.replaced_by_jti = new_jti

    db.add(RefreshToken(
        jti=new_jti,
        user_email=user.email,
        expires_at=new_expires,
        source_ip=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
    ))
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.email, roles),
        refresh_token=new_refresh,
        token_type="bearer",
    )


@router.post("/logout")
def logout(
    request: Request,
    body: LogoutRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    revoked_count = 0
    if body and body.refresh_token:
        try:
            payload = decode_token_unverified(body.refresh_token)
            jti = payload.get("jti")
            if jti and payload.get("sub") == user.email:
                now = datetime.now(timezone.utc)
                revoked_count = (
                    db.query(RefreshToken)
                    .filter(
                        RefreshToken.jti == jti,
                        RefreshToken.revoked_at.is_(None),
                    )
                    .update({RefreshToken.revoked_at: now}, synchronize_session=False)
                )
        except ValueError:
            # Idempotent logout — malformed or expired token, nothing to revoke.
            pass

    record_audit(db, actor=user.email, action="LOGOUT", resource="user",
                 resource_id=user.id,
                 new_state={"revoked_refresh_tokens": revoked_count})
    db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=user.role_names(),
        tenant_id=getattr(user, "tenant_id", "default") or "default",
        tenant_name=getattr(user, "tenant_name", "Default Workspace") or "Default Workspace",
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Self-service workspace registration.
    
    Creates a new user with an isolated tenant workspace and admin privileges
    scoped to that workspace.
    """
    import uuid
    from sqlalchemy import func

    existing = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    workspace_input = (body.workspace_name or "").strip()
    if workspace_input:
        # Check if an existing team workspace exists with this name or tenant_id
        existing_team = (
            db.query(User)
            .filter(
                (func.lower(User.tenant_name) == workspace_input.lower())
                | (User.tenant_id == workspace_input)
            )
            .first()
        )
        if existing_team:
            # Join the existing team workspace!
            tenant_id = existing_team.tenant_id
            workspace_title = existing_team.tenant_name
        else:
            # Create a brand new workspace
            tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
            workspace_title = workspace_input
    else:
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        workspace_title = f"{body.full_name or body.email.split('@')[0]}'s Workspace"

    desired_role = (body.role or "ADMIN").upper().strip()
    if desired_role not in ("ADMIN", "ANALYST", "AUDITOR"):
        desired_role = "ADMIN"

    role = db.query(Role).filter(Role.name == desired_role).first()
    if not role:
        role = Role(name=desired_role, description=f"{desired_role.title()} role")
        db.add(role)
        db.flush()

    u = User(
        email=body.email.lower().strip(),
        password_hash=hash_password(body.password),
        full_name=body.full_name or body.email.split("@")[0],
        tenant_id=tenant_id,
        tenant_name=workspace_title,
        is_active=True,
    )
    u.roles = [role]
    db.add(u)
    db.flush()

    roles = [role.name]
    access = create_access_token(u.email, roles, tenant_id=tenant_id)
    refresh, jti, expires_at = create_refresh_token(u.email)

    db.add(RefreshToken(
        jti=jti,
        user_email=u.email,
        expires_at=expires_at,
        source_ip=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
    ))
    record_audit(
        db,
        actor=u.email,
        action="WORKSPACE_REGISTERED",
        resource="user",
        resource_id=u.id,
        tenant_id=tenant_id,
        new_state={"roles": roles, "workspace": workspace_title, "tenant_id": tenant_id},
    )
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        tenant_id=tenant_id,
        tenant_name=workspace_title,
    )