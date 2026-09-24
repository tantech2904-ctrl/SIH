"""Backend restart orchestration.

Three modes:
  - docker:       we're in a container with restart=unless-stopped.
                  Schedule os._exit(0); Docker brings us back up.
  - orchestrator: same as docker (k8s, systemd, etc.).
  - manual:       local dev. Sync .env.live to .env for the next manual start.
                  No automatic restart.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.services.audit_service import record_audit

log = get_logger(__name__)


def detect_restart_mode() -> str:
    """Return 'docker' | 'orchestrator' | 'manual'."""
    forced = (settings.RESTART_MODE or "auto").lower()
    if forced == "docker":
        return "docker"
    if forced == "orchestrator":
        return "orchestrator"
    if forced == "manual":
        return "manual"
    # auto
    if os.environ.get("IN_DOCKER", "").lower() == "true":
        return "docker"
    if Path("/.dockerenv").exists():
        return "docker"
    return "manual"


def _sync_env_live_to_env() -> None:
    """In manual mode, ensure .env reflects .env.live so the next
    manual restart picks up the changes."""
    live = Path("/app/.env.live")
    target = Path(".env")
    if not live.exists():
        return
    try:
        shutil.copyfile(live, target)
        log.info("restart.env_synced", source=str(live), target=str(target))
    except Exception as e:
        log.warning("restart.env_sync_failed", error=str(e))


def trigger_restart(db: Session, *, actor: str) -> dict:
    mode = detect_restart_mode()

    record_audit(
        db,
        actor=actor,
        action="BACKEND_RESTART_REQUESTED",
        resource="system",
        new_state={"mode": mode},
    )
    db.commit()

    if mode == "manual":
        _sync_env_live_to_env()
        return {
            "restarted": False,
            "mode": "manual",
            "message": (
                "Manual restart required. Stop the backend process "
                "(Ctrl+C) and start it again. Then reload this page."
            ),
        }

    # docker / orchestrator: schedule the exit AFTER the response has
    # flushed. We use threading.Timer instead of asyncio.call_later
    # because this function is called from a synchronous FastAPI
    # endpoint, which runs in a thread pool with no asyncio event loop.
    import threading
    threading.Timer(2.5, os._exit, args=(0,)).start()

    return {
        "restarted": True,
        "mode": mode,
        "message": "Backend restarting now. This page will reconnect automatically.",
    }