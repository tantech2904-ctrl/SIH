from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User
from app.schemas.settings import (
    RestartResponse, SettingsListResponse, SettingsUpdateRequest,
    SettingsUpdateResponse,
)
from app.services.restart_service import trigger_restart
from app.settings.service import get_settings_for_ui, update_settings

router = APIRouter()


@router.get("", response_model=SettingsListResponse)
def get_settings(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    return get_settings_for_ui()


@router.post("", response_model=SettingsUpdateResponse)
def post_settings(
    body: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    return update_settings(db, actor=user.email, updates=body.updates)


@router.post("/restart", response_model=RestartResponse)
def post_restart(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    return trigger_restart(db, actor=user.email)