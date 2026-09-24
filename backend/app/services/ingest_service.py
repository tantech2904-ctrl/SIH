"""Core ingestion pipeline service.

Order of operations (invariant — never violated):
  INGEST → PRESERVE RAW → HASH → DETECT FORMAT → PARSE → MAP → NORMALIZE
  → VALIDATE → DETECT → RISK → STORE → (async) ENRICH
Failure at any stage → Quarantine (raw evidence already preserved).
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ParserError
from app.core.logging import get_logger
from app.models.event import Event
from app.models.canonical import CanonicalEvent
from app.models.processing import ProcessingRun
from app.models.parser import ParserRegistry
from app.normalization.cse import CSEMapper
from app.normalization.detector import detect_format
from app.normalization.schema_drift import detect_drift
from app.models.drift import SchemaDrift
from app.parsers.registry import get_registry
from app.services.evidence_service import preserve_evidence
from app.services.quarantine_service import quarantine_event
from app.validation.validator import validate_cse

log = get_logger(__name__)


def _stage_start(db: Session, event_id: str, stage: str, component: str = "") -> ProcessingRun:
    run = ProcessingRun(event_id=event_id, stage=stage, status="OK",
                        component=component or stage.lower())
    run.started_at = datetime.now(timezone.utc)
    db.add(run)
    db.flush()
    return run


def _stage_end(run: ProcessingRun, status: str = "OK", error: str | None = None) -> None:
    run.finished_at = datetime.now(timezone.utc)
    run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
    run.status = status
    run.error = error[:1024] if error else None


def _enabled_parser_ids(db: Session) -> set[str]:
    rows = db.query(ParserRegistry).filter(ParserRegistry.enabled.is_(True)).all()
    return {row.parser_id for row in rows}


def ingest_event(
    db: Session,
    *,
    raw_bytes: bytes,
    source: str,
    source_type: str,
    filename: str,
    content_type: str,
    correlation_id: str | None = None,
    ingestion_id: str | None = None,
) -> Event:
    """Synchronous ingestion of one event (raw bytes)."""
    correlation_id = correlation_id or str(uuid.uuid4())
    ingestion_id = ingestion_id or str(uuid.uuid4())

    event = Event(
        event_id=str(uuid.uuid4()),
        ingestion_id=ingestion_id,
        correlation_id=correlation_id,
        source=source,
        source_type=source_type,
        filename=filename,
        content_type=content_type,
        raw_size=len(raw_bytes),
        processing_status="RECEIVED",
    )
    db.add(event)
    db.flush()

    _stage_start(db, event.event_id, "INGESTED", component="api.ingest")

    # 1) Preserve raw evidence (always)
    try:
        evidence = preserve_evidence(
            db=db, event_id=event.event_id, raw_bytes=raw_bytes,
            source=source, content_type=content_type,
        )
        run = _stage_start(db, event.event_id, "PRESERVED", component="evidence")
        _stage_end(run)
        run = _stage_start(db, event.event_id, "HASHED", component="sha256")
        _stage_end(run)
    except Exception as e:
        log.exception("ingest.preserve_failed", error=str(e))
        event.processing_status = "FAILED"
        event.error_message = "Evidence preservation failed"
        db.flush()
        return event

    # 2) Detect format
    raw_text = raw_bytes.decode("utf-8", errors="replace")
    run = _stage_start(db, event.event_id, "DETECTED", component="detector")
    try:
        enabled_parser_ids = _enabled_parser_ids(db)
        detection = detect_format(raw_text, filename=filename, enabled_parser_ids=enabled_parser_ids)
        event.detected_format = detection.format
        event.detection_confidence = detection.confidence
        event.parser_id = detection.parser_id or None
        _stage_end(run)
    except Exception as e:
        _stage_end(run, "ERROR", str(e))
        quarantine_event(db, event=event, reason="DETECTION_FAILED", stage="DETECT",
                          detail=str(e), errors=[str(e)])
        db.commit()
        return event

    if not detection.parser_id or detection.confidence < settings.RISK_AUTO_QUARANTINE_BELOW_CONFIDENCE:
        quarantine_event(
            db, event=event, reason="UNKNOWN_FORMAT", stage="DETECT",
            detail=f"Best confidence {detection.confidence:.2f} below threshold",
            analysis={"reasons": detection.reasons, "format": detection.format},
        )
        db.commit()
        return event

    return _run_full_pipeline(db, event=event, raw_text=raw_text, detection=detection)


def process_existing_event(db: Session, *, event: Event, force_parser: str | None = None) -> Event:
    """Re-run pipeline on preserved raw evidence (used by replay)."""
    from app.services.evidence_service import compute_sha256  # noqa: F401
    from app.models.evidence import RawEvidence
    from app.storage.minio_store import get_object_store
    from app.services.integrity_service import _key_from_location

    evidence = db.query(RawEvidence).filter(RawEvidence.event_id == event.event_id).first()
    if not evidence:
        raise ParserError("No preserved evidence for replay")

    existing_cse = db.query(CanonicalEvent).filter(CanonicalEvent.event_id == event.event_id).first()
    if existing_cse:
        db.delete(existing_cse)
        db.flush()

    store = get_object_store()
    raw_bytes = store.get_bytes(_key_from_location(evidence.storage_location))
    raw_text = raw_bytes.decode("utf-8", errors="replace")

    if force_parser:
        parser = get_registry().get(force_parser)
        if not parser:
            raise ParserError(f"Parser not found: {force_parser}")
        from app.normalization.detector import FormatDetection
        detection = FormatDetection(format=parser.format_name, parser_id=parser.parser_id,
                                     confidence=1.0, reasons=["forced_by_operator"])
        event.detected_format = detection.format
        event.detection_confidence = 1.0
        event.parser_id = parser.parser_id
    else:
        enabled_parser_ids = _enabled_parser_ids(db)
        detection = detect_format(raw_text, filename=event.filename, enabled_parser_ids=enabled_parser_ids)
        event.detected_format = detection.format
        event.detection_confidence = detection.confidence
        event.parser_id = detection.parser_id or None

    # Reset per-event derived status
    event.processing_status = "REPROCESSING"
    event.error_message = None
    db.flush()

    return _run_full_pipeline(db, event=event, raw_text=raw_text, detection=detection)


def _run_full_pipeline(db: Session, *, event: Event, raw_text: str, detection) -> Event:
    parser = get_registry().get(detection.parser_id)
    if parser is None:
        quarantine_event(db, event=event, reason="PARSER_NOT_FOUND", stage="PARSE",
                          detail=f"No parser with id {detection.parser_id}")
        db.commit()
        return event

    # 3) Parse
    run = _stage_start(db, event.event_id, "PARSED", component=f"parser:{parser.parser_id}")
    try:
        parsed = parser.parse(raw_text)
        if not parsed.success:
            raise ParserError("; ".join(parsed.errors) or "Parser returned unsuccessful result")
        event.parser_version = parsed.parser_version
        _stage_end(run)
    except Exception as e:
        _stage_end(run, "ERROR", str(e))
        quarantine_event(db, event=event, reason="PARSER_FAILED", stage="PARSE",
                          detail=str(e), errors=[str(e)],
                          analysis={"parser_id": parser.parser_id})
        db.commit()
        return event

    # 4) Custom mappings from DB (analyst-approved overrides)
    custom = _load_custom_mappings(db, parser.parser_id)

    # 5) Map / Normalize
    run = _stage_start(db, event.event_id, "NORMALIZED", component="cse_mapper")
    mapper = CSEMapper(parser_id=parser.parser_id, parser_version=parsed.parser_version,
                       custom_mappings=custom)
    cse_result = mapper.map(parsed.fields)
    _stage_end(run)

    # 6) Validate
    run = _stage_start(db, event.event_id, "VALIDATED", component="validator")
    validation = validate_cse(cse_result.fields)
    _stage_end(run, status="WARNING" if validation.status == "WARNING" else ("ERROR" if validation.status == "INVALID" else "OK"))

    if validation.status == "INVALID":
        quarantine_event(
            db, event=event, reason="VALIDATION_FAILED", stage="VALIDATE",
            detail="; ".join(validation.notes), errors=validation.notes,
            analysis={"cse": _safe_json(cse_result.fields)},
        )
        db.commit()
        return event

    # 7) Detection + Risk
    run = _stage_start(db, event.event_id, "ANALYZED", component="detection_engine")
    from app.services.detection_service import run_detection
    detection_alerts, threat_ctx, risk_score, risk_factors = run_detection(
        db, event=event, cse=cse_result.fields,
    )
    _stage_end(run)

    # 8) Persist CSE
    cse_row = _persist_cse(
        db, event=event, cse=cse_result.fields, provenance=cse_result.provenance,
        validation=validation, risk_score=risk_score, risk_factors=risk_factors,
        detection={"alerts": [a["alert_id"] for a in detection_alerts], "count": len(detection_alerts)},
        threat_context=threat_ctx,
        evidence=event.raw_size,
    )

    event.risk_score = risk_score
    event.severity = cse_result.fields.get("severity")
    event.processing_status = "PROCESSED" if validation.status == "VALID" else "WARNING"

    # 9) Schema drift detection (vendor-aware)
    _maybe_record_drift(db, event=event, parser_id=parser.parser_id,
                        parser_version=parsed.parser_version,
                        observed_fields=list(parsed.fields.keys()),
                        sample_event_id=event.event_id)

    run = _stage_start(db, event.event_id, "ROUTED", component="router")
    _stage_end(run)

    db.flush()
    return event


def _load_custom_mappings(db: Session, parser_id: str) -> dict[str, dict]:
    from app.models.mapping import FieldMapping
    rows = db.query(FieldMapping).filter(
        FieldMapping.parser_id == parser_id,
        FieldMapping.approved.is_(True),
        FieldMapping.mapping_source.in_(["analyst", "analyzer"]),
    ).all()
    out: dict[str, dict] = {}
    for r in rows:
        out[r.original_field] = {
            "canonical": r.canonical_field,
            "confidence": r.confidence,
            "source": r.mapping_source,
        }
    return out


def _persist_cse(db: Session, *, event: Event, cse: dict, provenance: list,
                 validation, risk_score: int, risk_factors: list,
                 detection: dict, threat_context: dict, evidence) -> CanonicalEvent:
    from dateutil import parser as dtparser
    ts = None
    if cse.get("timestamp"):
        try:
            ts = dtparser.parse(str(cse["timestamp"]))
        except Exception:
            ts = None

    extensions = dict(cse.get("extensions") or {})
    if "user.email" in cse:
        extensions["user_email"] = cse["user.email"]

    row = CanonicalEvent(
        event_id=event.event_id,
        timestamp=ts or datetime.now(timezone.utc),
        event_type=str(cse.get("event_type") or "unknown")[:64],
        category=str(cse.get("category") or "other")[:64],
        severity=str(cse.get("severity") or "INFO")[:16],
        source_ip=cse.get("source.ip"),
        source_port=cse.get("source.port"),
        source_hostname=cse.get("source.hostname"),
        destination_ip=cse.get("destination.ip"),
        destination_port=cse.get("destination.port"),
        destination_hostname=cse.get("destination.hostname"),
        user_name=cse.get("user.name"),
        action=cse.get("action"),
        protocol=cse.get("protocol"),
        device=cse.get("device"),
        vendor=cse.get("vendor"),
        product=cse.get("product"),
        message=(cse.get("message") or "")[:4096] or None,
        status=cse.get("status"),
        raw_reference=f"/api/v1/events/{event.event_id}/raw",
        tags=[],
        enrichment={},
        threat_context=threat_context,
        detection=detection,
        processing_metadata={"parser_id": event.parser_id, "parser_version": event.parser_version,
                             "format": event.detected_format, "confidence": event.detection_confidence},
        extensions=extensions,
        risk_score=risk_score,
        risk_factors=risk_factors,
        validation_status=validation.status,
        validation_notes=validation.notes,
        mapping_provenance=[p.to_dict() for p in provenance],
    )
    db.add(row)
    db.flush()
    return row


def _maybe_record_drift(db: Session, *, event: Event, parser_id: str, parser_version: str,
                        observed_fields: list[str], sample_event_id: str) -> None:
    # Known fields are the ones in the mapping / alias vocabulary; observed fields not
    # mapping to a canonical are candidates for schema drift.
    from app.normalization.vocabulary import lookup_alias
    from app.models.mapping import FieldMapping

    known_rows = db.query(FieldMapping).filter(FieldMapping.parser_id == parser_id).all()
    known_fields = [r.original_field for r in known_rows]

    observed_canonical_map = {f: lookup_alias(f) for f in observed_fields}
    # Any observed field that aliases to a canonical we already know via another field
    # is a drift candidate.
    seen_canon = {}
    for f in observed_fields:
        c = observed_canonical_map.get(f)
        if c:
            seen_canon.setdefault(c, []).append(f)

    drift_vendor = None
    # We treat "vendor" as the parser's declared vendor (best-effort).
    parser_row = db.query(ParserRegistry).filter(ParserRegistry.parser_id == parser_id).first()
    if parser_row:
        drift_vendor = parser_row.vendor

    for canon, fields in seen_canon.items():
        if len(fields) > 1:
            # Multiple fields map to same canonical — potential drift
            for f in fields:
                if f not in known_fields:
                    existing = db.query(SchemaDrift).filter(
                        SchemaDrift.parser_id == parser_id,
                        SchemaDrift.observed_field == f,
                    ).first()
                    if existing:
                        existing.affected_events += 1
                        db.flush()
                        continue
                    d = SchemaDrift(
                        vendor=drift_vendor or "unknown",
                        parser_id=parser_id,
                        parser_version=parser_version,
                        expected_field=next((k for k in known_fields if lookup_alias(k) == canon), canon),
                        observed_field=f,
                        suggested_canonical=canon,
                        affected_events=1,
                        confidence=0.7,
                        reason=f"Multiple fields map to canonical '{canon}'; '{f}' is new.",
                        sample_event_id=sample_event_id,
                    )
                    db.add(d)
                    db.flush()


def _safe_json(obj) -> dict:
    import json
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return {}

def dispatch_enrichment_async(event_ids: list[str]) -> None:
    """Best-effort dispatch of the enrichment Celery task after ingestion commits.

    HARD INVARIANT: this MUST be called AFTER db.commit(), never before.
    The worker queries CanonicalEvent by event_id; if the transaction has
    not committed, the row is invisible and the task returns NOT_FOUND.

    Never raises. Enrichment is optional context; ingestion must succeed
    even if Redis/Celery is unreachable. Dispatch failures are logged and
    swallowed.
    """
    if not event_ids:
        return
    try:
        from app.workers.tasks import enrich_event_task
        for eid in event_ids:
            enrich_event_task.delay(eid)
    except Exception as e:
        log.warning(
            "enrich.dispatch_failed",
            count=len(event_ids),
            error=str(e)[:200],
        )