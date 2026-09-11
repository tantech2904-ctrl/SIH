"""Defensive detection engine + risk scoring.

Rules are stored in DB (DetectionRule). This service loads active rules and
evaluates them against a normalized CSE. It is deterministic — no ML,
no black-box scoring.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import parser as dtparser
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.event import Event
from app.models.rule import DetectionRule
from app.models.canonical import CanonicalEvent
from app.models.attck import ATTACKMapping
from app.detection.attck_map import map_to_attck

log = get_logger(__name__)


_SEVERITY_WEIGHT = {"INFO": 5, "LOW": 15, "MEDIUM": 35, "HIGH": 60, "CRITICAL": 85}
_RULE_SEVERITY_WEIGHT = {"LOW": 10, "MEDIUM": 25, "HIGH": 45, "CRITICAL": 70}


def _recent_events(db: Session, *, source_ip: str | None, user_name: str | None,
                   window_seconds: int, reference_time: datetime | None = None) -> list[CanonicalEvent]:
    reference = reference_time or datetime.now(timezone.utc)
    since = reference - timedelta(seconds=window_seconds)
    q = db.query(CanonicalEvent).filter(CanonicalEvent.timestamp >= since, CanonicalEvent.timestamp <= reference)
    if source_ip:
        q = q.filter(CanonicalEvent.source_ip == source_ip)
    elif user_name:
        q = q.filter(CanonicalEvent.user_name == user_name)
    return q.order_by(desc(CanonicalEvent.timestamp)).limit(500).all()


def _eval_rule(rule: DetectionRule, *, cse: dict, recent: list[CanonicalEvent]) -> tuple[bool, dict]:
    cond = rule.conditions or {}
    details: dict = {"rule_id": rule.rule_id}

    if "event_type" in cond and str(cse.get("event_type", "")).lower() != str(cond["event_type"]).lower():
        return False, details
    if "status" in cond and str(cse.get("status", "")).lower() != str(cond["status"]).lower():
        return False, details
    if "event_category" in cond and str(cse.get("category", "")).lower() != str(cond["event_category"]).lower():
        return False, details
    if "threat_malicious" in cond and bool(cond["threat_malicious"]) and not cse.get("_threat_malicious", False):
        return False, details
    if "unusual_port" in cond and bool(cond["unusual_port"]):
        dp = cse.get("destination.port")
        if dp is None:
            return False, details
        common = {22, 80, 443, 53, 25, 110, 143, 993, 995, 3389, 8080, 8443}
        if int(dp) in common:
            return False, details

    # Frequency / threshold rules
    if "threshold" in cond:
        thr = int(cond["threshold"])
        # For authentication failures, count recent matching events
        matches = [e for e in recent
                   if (e.event_type or "").lower() == str(cond.get("event_type", "authentication")).lower()
                   and (e.status or "").lower() == str(cond.get("status", "failure")).lower()]
        details["observed"] = len(matches)
        if len(matches) + 1 < thr:
            return False, details
        details["threshold"] = thr

    if "distinct_ports_threshold" in cond:
        thr = int(cond["distinct_ports_threshold"])
        ports = {e.destination_port for e in recent if e.destination_port}
        details["distinct_ports"] = len(ports)
        if len(ports) < thr:
            return False, details

    if "preceded_by_failures" in cond:
        thr = int(cond["preceded_by_failures"])
        window = int(cond.get("window_seconds", 600))
        fails = [e for e in recent
                 if (e.event_type or "").lower() == "authentication"
                 and (e.status or "").lower() == "failure"]
        details["preceded_failures"] = len(fails)
        if len(fails) < thr:
            return False, details

    return True, details


def run_detection(db: Session, *, event: Event, cse: dict) -> tuple[list[dict], dict, int, list[dict]]:
    # Threat context may already be set on cse by enrichment step; not here.
    threat_context = {
        "malicious": False,
        "suspicious": False,
        "providers": [],
    }
    cse["_threat_malicious"] = threat_context["malicious"]

    rules = db.query(DetectionRule).filter(DetectionRule.enabled.is_(True)).all()
    alerts_created: list[dict] = []

    source_ip = cse.get("source.ip")
    user_name = cse.get("user.name")

    # Prefetch recent events once (bounded) using the event timestamp as the reference point.
    try:
        reference_time = dtparser.parse(str(cse.get("timestamp", ""))) if cse.get("timestamp") else None
        if reference_time and reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
    except Exception:
        reference_time = None

    recent = _recent_events(
        db,
        source_ip=source_ip,
        user_name=user_name if not source_ip else None,
        window_seconds=settings.CORRELATION_WINDOW_SECONDS,
        reference_time=reference_time,
    )

    for r in rules:
        try:
            fired, details = _eval_rule(r, cse=cse, recent=recent)
        except Exception as e:
            log.warning("rule.eval_error", rule=r.rule_id, error=str(e))
            continue
        if not fired:
            continue

        risk = _SEVERITY_WEIGHT.get(cse.get("severity", "INFO"), 5)
        rule_weight = _RULE_SEVERITY_WEIGHT.get(r.severity, 20)
        score = min(100, risk + rule_weight)

        mitre = list(r.mitre or [])
        alert = Alert(
            event_id=event.event_id,
            rule_id=r.rule_id,
            rule_name=r.name,
            severity=r.severity,
            risk_score=score,
            description=r.description,
            mitre=mitre,
            details=details,
        )
        db.add(alert)
        db.flush()
        alerts_created.append({"alert_id": alert.alert_id, "rule_id": r.rule_id, "severity": r.severity,
                                "name": r.name, "score": score, "mitre": mitre})

        # ATT&CK mapping for this alert
        for tid in mitre:
            tech = map_to_attck(tid)
            if tech:
                db.add(ATTACKMapping(
                    event_id=event.event_id,
                    technique_id=tech["technique_id"],
                    technique_name=tech["technique_name"],
                    tactic=tech["tactic"],
                    confidence=0.7,
                    reason=f"Rule {r.rule_id} mapped to {tid}",
                    source="rule",
                ))

        r.fire_count += 1
        r.last_fired_at = datetime.now(timezone.utc)

    # Deterministic risk scoring
    risk_score, risk_factors = _score_risk(cse, alerts_created, recent)
    db.flush()
    return alerts_created, threat_context, risk_score, risk_factors


def _score_risk(cse: dict, alerts: list[dict], recent: list[CanonicalEvent]) -> tuple[int, list[dict]]:
    factors: list[dict] = []
    score = _SEVERITY_WEIGHT.get(cse.get("severity", "INFO"), 5)
    factors.append({"name": "severity_base", "value": score,
                    "reason": f"Base score from event severity '{cse.get('severity')}'"})

    # Repeated activity
    if len(recent) >= 20:
        score += 10
        factors.append({"name": "frequency_20plus", "value": 10,
                        "reason": f"{len(recent)} related events in correlation window"})

    # Alerts
    for a in alerts:
        delta = _RULE_SEVERITY_WEIGHT.get(a["severity"], 15)
        score += delta
        factors.append({"name": f"alert_{a['rule_id']}", "value": delta,
                        "reason": f"Rule '{a['name']}' fired ({a['severity']})"})

    # Suspicious ports
    dp = cse.get("destination.port")
    if dp is not None and int(dp) in {4444, 5555, 6666, 31337, 1337}:
        score += 20
        factors.append({"name": "suspicious_port", "value": 20,
                        "reason": f"Destination port {dp} is commonly abused"})

    # External source
    sip = cse.get("source.ip")
    if sip:
        try:
            import ipaddress
            ip = ipaddress.ip_address(sip)
            if not ip.is_private and not ip.is_loopback:
                score += 5
                factors.append({"name": "external_source", "value": 5,
                                "reason": "Source is a public IP address"})
        except Exception:
            pass

    score = max(0, min(100, int(score)))
    return score, factors