"""Celery tasks — enrichment and maintenance work only.

The CORE pipeline runs synchronously so that ingestion never depends on the
worker being up. Enrichment is dispatched asynchronously and its failure is
non-fatal.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.enrichment.orchestrator import enrich_cse
from app.enrichment.cache import purge_expired
from app.models.canonical import CanonicalEvent
from app.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="ulpf.enrich_event", bind=True, max_retries=2, default_retry_delay=15)
def enrich_event_task(self, event_id: str):
    db = SessionLocal()
    try:
        c = db.query(CanonicalEvent).filter(CanonicalEvent.event_id == event_id).first()
        if not c:
            return {"event_id": event_id, "status": "NOT_FOUND"}
        cse = {
            "source.ip": c.source_ip,
            "destination.ip": c.destination_ip,
            "extensions": c.extensions or {},
        }
        summary = enrich_cse(db, cse=cse, event_id=event_id)
        c.enrichment = summary
        c.threat_context = {
            "malicious": summary.get("threat_malicious", False),
            "suspicious": summary.get("threat_suspicious", False),
        }
        db.commit()
        return {"event_id": event_id, "status": "OK", "providers": list(summary.get("providers", {}).keys())}
    except Exception as e:
        db.rollback()
        log.exception("enrich.task_failed", event_id=event_id, error=str(e))
        try:
            raise self.retry(exc=e)
        except Exception:
            return {"event_id": event_id, "status": "FAILED", "error": str(e)[:500]}
    finally:
        db.close()


@celery_app.task(name="ulpf.purge_cache")
def purge_cache_task():
    db = SessionLocal()
    try:
        n = purge_expired(db)
        db.commit()
        return {"purged": n}
    finally:
        db.close()