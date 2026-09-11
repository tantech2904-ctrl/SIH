
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.parsers.registry import get_registry
from app.storage.minio_store import get_object_store

router = APIRouter()
_started_at = time.time()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "time": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - _started_at),
    }


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    checks = {}
    ok = True

    # DB
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as e:
        checks["database"] = {"ok": False, "error": str(e)[:200]}
        ok = False

    # Redis (optional)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = {"ok": True}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": str(e)[:200]}

    # Object store
    try:
        checks["object_store"] = get_object_store().health()
    except Exception as e:
        checks["object_store"] = {"ok": False, "error": str(e)[:200]}

    # Parsers
    try:
        reg = get_registry()
        checks["parsers"] = {"count": len(list(reg.all())), "ok": True}
    except Exception as e:
        checks["parsers"] = {"ok": False, "error": str(e)[:200]}
        ok = False

    return {"ready": ok, "checks": checks, "time": datetime.now(timezone.utc).isoformat()}


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    from app.models.event import Event
    from app.models.quarantine import QuarantineEvent
    total = db.query(Event).count()
    quarantined = db.query(QuarantineEvent).count()
    return {
        "events_total": total,
        "quarantined_total": quarantined,
        "uptime_seconds": int(time.time() - _started_at),
    }