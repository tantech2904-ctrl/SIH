
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.models.canonical import CanonicalEvent
from app.models.event import Event
from app.models.enrichment import EnrichmentResult
from app.models.quarantine import QuarantineEvent
from app.models.user import User

router = APIRouter()


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_events = db.query(func.count(Event.event_id)).scalar() or 0
    total_cse = db.query(func.count(CanonicalEvent.cse_id)).scalar() or 0
    quarantined = db.query(func.count(QuarantineEvent.id)).scalar() or 0

    now = datetime.now(timezone.utc)
    one_min_ago = now - timedelta(minutes=1)
    events_last_min = db.query(func.count(Event.event_id)).filter(Event.ingested_at >= one_min_ago).scalar() or 0
    eps = round(events_last_min / 60.0, 3)

    status_counts = dict(
        db.query(Event.processing_status, func.count(Event.event_id))
        .group_by(Event.processing_status).all()
    )

    severity_counts = dict(
        db.query(CanonicalEvent.severity, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.severity).all()
    )

    category_counts = dict(
        db.query(CanonicalEvent.category, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.category).all()
    )

    format_counts = dict(
        db.query(Event.detected_format, func.count(Event.event_id))
        .filter(Event.detected_format.isnot(None))
        .group_by(Event.detected_format).all()
    )

    vendor_counts = dict(
        db.query(CanonicalEvent.vendor, func.count(CanonicalEvent.cse_id))
        .filter(CanonicalEvent.vendor.isnot(None))
        .group_by(CanonicalEvent.vendor).order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    )

    top_src = [
        {"ip": ip, "count": cnt}
        for ip, cnt in db.query(CanonicalEvent.source_ip, func.count(CanonicalEvent.cse_id))
        .filter(CanonicalEvent.source_ip.isnot(None))
        .group_by(CanonicalEvent.source_ip)
        .order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    ]
    top_dst = [
        {"ip": ip, "count": cnt}
        for ip, cnt in db.query(CanonicalEvent.destination_ip, func.count(CanonicalEvent.cse_id))
        .filter(CanonicalEvent.destination_ip.isnot(None))
        .group_by(CanonicalEvent.destination_ip)
        .order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    ]

    high_risk = db.query(func.count(CanonicalEvent.cse_id)).filter(CanonicalEvent.risk_score >= 70).scalar() or 0
    critical_alerts = db.query(func.count(Alert.alert_id)).filter(Alert.severity == "CRITICAL").scalar() or 0
    open_alerts = db.query(func.count(Alert.alert_id)).filter(Alert.status == "OPEN").scalar() or 0

    # Recent throughput (last 24 h buckets, hourly)
    since = now - timedelta(hours=24)
    hourly = (
        db.query(func.date_trunc("hour", Event.ingested_at).label("h"), func.count(Event.event_id))
        .filter(Event.ingested_at >= since)
        .group_by("h").order_by("h").all()
    ) if not db.bind.dialect.name == "sqlite" else []

    return {
        "totals": {
            "events": total_events,
            "canonical_events": total_cse,
            "quarantined": quarantined,
            "high_risk_events": high_risk,
            "critical_alerts": critical_alerts,
            "open_alerts": open_alerts,
        },
        "throughput": {"events_last_minute": events_last_min, "events_per_second": eps},
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "format_counts": format_counts,
        "top_vendors": vendor_counts,
        "top_source_ips": top_src,
        "top_destination_ips": top_dst,
        "hourly_throughput": [{"hour": str(h), "count": c} for h, c in hourly],
    }