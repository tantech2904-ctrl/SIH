
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_effective_tenant_id
from app.db.session import get_db
from app.models.alert import Alert
from app.models.canonical import CanonicalEvent
from app.models.event import Event
from app.models.enrichment import EnrichmentResult
from app.models.quarantine import QuarantineEvent
from app.models.user import User

router = APIRouter()


@router.get("")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_id = get_effective_tenant_id(request, user)

    ev_q = db.query(Event)
    cse_q = db.query(CanonicalEvent)
    quarantine_q = db.query(QuarantineEvent)
    alert_q = db.query(Alert)

    if tenant_id != "*":
        ev_q = ev_q.filter(Event.tenant_id == tenant_id)
        cse_q = cse_q.filter(CanonicalEvent.tenant_id == tenant_id)
        quarantine_q = quarantine_q.filter(QuarantineEvent.tenant_id == tenant_id)
        alert_q = alert_q.filter(Alert.tenant_id == tenant_id)

    total_events = ev_q.with_entities(func.count(Event.event_id)).scalar() or 0
    total_cse = cse_q.with_entities(func.count(CanonicalEvent.cse_id)).scalar() or 0
    quarantined = quarantine_q.with_entities(func.count(QuarantineEvent.id)).scalar() or 0

    now = datetime.now(timezone.utc)
    one_min_ago = now - timedelta(minutes=1)
    events_last_min = ev_q.filter(Event.ingested_at >= one_min_ago).with_entities(func.count(Event.event_id)).scalar() or 0
    eps = round(events_last_min / 60.0, 3)

    status_counts = dict(
        ev_q.with_entities(Event.processing_status, func.count(Event.event_id))
        .group_by(Event.processing_status).all()
    )

    severity_counts = dict(
        cse_q.with_entities(CanonicalEvent.severity, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.severity).all()
    )

    category_counts = dict(
        cse_q.with_entities(CanonicalEvent.category, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.category).all()
    )

    format_counts = dict(
        ev_q.filter(Event.detected_format.isnot(None))
        .with_entities(Event.detected_format, func.count(Event.event_id))
        .group_by(Event.detected_format).all()
    )

    vendor_counts = dict(
        cse_q.filter(CanonicalEvent.vendor.isnot(None))
        .with_entities(CanonicalEvent.vendor, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.vendor).order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    )

    top_src = [
        {"ip": ip, "count": cnt}
        for ip, cnt in cse_q.filter(CanonicalEvent.source_ip.isnot(None))
        .with_entities(CanonicalEvent.source_ip, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.source_ip)
        .order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    ]
    top_dst = [
        {"ip": ip, "count": cnt}
        for ip, cnt in cse_q.filter(CanonicalEvent.destination_ip.isnot(None))
        .with_entities(CanonicalEvent.destination_ip, func.count(CanonicalEvent.cse_id))
        .group_by(CanonicalEvent.destination_ip)
        .order_by(desc(func.count(CanonicalEvent.cse_id))).limit(10).all()
    ]

    high_risk = cse_q.filter(CanonicalEvent.risk_score >= 70).with_entities(func.count(CanonicalEvent.cse_id)).scalar() or 0
    critical_alerts = alert_q.filter(Alert.severity == "CRITICAL").with_entities(func.count(Alert.alert_id)).scalar() or 0
    open_alerts = alert_q.filter(Alert.status == "OPEN").with_entities(func.count(Alert.alert_id)).scalar() or 0

    # Recent throughput (last 24 h buckets, hourly)
    since = now - timedelta(hours=24)
    if db.bind.dialect.name == "sqlite":
        hourly = (
            ev_q.filter(Event.ingested_at >= since)
            .with_entities(func.strftime("%Y-%m-%d %H:00:00", Event.ingested_at).label("h"), func.count(Event.event_id))
            .group_by("h").order_by("h").all()
        )
    else:
        hourly = (
            ev_q.filter(Event.ingested_at >= since)
            .with_entities(func.date_trunc("hour", Event.ingested_at).label("h"), func.count(Event.event_id))
            .group_by("h").order_by("h").all()
        )

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