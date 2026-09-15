import uuid
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_analyst, require_admin
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.evidence import RawEvidence
from app.models.user import User
from app.schemas.ingest import IngestJsonRequest, IngestResponse, BatchIngestResponse
from app.parsers.windows_evtx import extract_windows_event_records
from app.services.audit_service import record_audit
from app.services.ingest_service import ingest_event

router = APIRouter()


def _evidence_hash(db: Session, event_id: str) -> str | None:
    row = db.query(RawEvidence).filter(RawEvidence.event_id == event_id).first()
    return row.sha256 if row else None


def _response(event, db: Session) -> IngestResponse:
    return IngestResponse(
        event_id=event.event_id,
        ingestion_id=event.ingestion_id,
        correlation_id=event.correlation_id,
        processing_status=event.processing_status,
        detected_format=event.detected_format,
        detection_confidence=event.detection_confidence,
        parser_id=event.parser_id,
        sha256=_evidence_hash(db, event.event_id),
        message=event.error_message,
    )


@router.post("", response_model=IngestResponse)
@limiter.limit(settings.RATE_LIMIT_INGEST)
def ingest_json(
    request: Request,
    body: IngestJsonRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    if body.raw is not None:
        raw_bytes = body.raw.encode("utf-8")
    elif body.payload is not None:
        import json
        raw_bytes = json.dumps(body.payload).encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Must provide 'raw' or 'payload'")

    if len(raw_bytes) > settings.MAX_EVENT_BYTES:
        raise HTTPException(status_code=413, detail="Event exceeds MAX_EVENT_BYTES")

    event = ingest_event(
        db, raw_bytes=raw_bytes,
        source=body.source, source_type=body.source_type,
        filename=body.filename, content_type=body.content_type,
    )
    record_audit(db, actor=user.email, action="INGEST", resource="event",
                 resource_id=event.event_id,
                 source_ip=request.client.host if request.client else None,
                 new_state={"status": event.processing_status,
                            "format": event.detected_format})
    db.commit()
    return _response(event, db)


@router.post("/raw", response_model=IngestResponse)
@limiter.limit(settings.RATE_LIMIT_INGEST)
async def ingest_raw(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
    source: str = Form("api"),
    source_type: str = Form("api"),
    filename: str = Form("upload.log"),
    content_type: str = Form("text/plain"),
    file: UploadFile | None = File(None),
):
    if file is None:
        raw_bytes = await request.body()
    else:
        raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty body")
    if len(raw_bytes) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds MAX_UPLOAD_BYTES")

    payloads = [raw_bytes]
    if filename.lower().endswith((".evtx", ".evt")):
        payloads = extract_windows_event_records(raw_bytes)
        if not payloads:
            raise HTTPException(status_code=400, detail="Could not extract Windows event records from EVTX/EVT payload")

    created_events = []
    ingestion_id = str(uuid.uuid4())
    for idx, payload in enumerate(payloads):
        event = ingest_event(
            db,
            raw_bytes=payload.encode("utf-8") if isinstance(payload, str) else payload,
            source=source,
            source_type=source_type,
            filename=filename,
            content_type=content_type,
            ingestion_id=ingestion_id,
        )
        created_events.append(event)
        record_audit(db, actor=user.email, action="INGEST_RAW", resource="event",
                     resource_id=event.event_id,
                     new_state={"record_index": idx, "filename": filename})

    db.commit()
    return _response(created_events[0], db) if created_events else _response(
        ingest_event(db, raw_bytes=raw_bytes, source=source, source_type=source_type,
                     filename=filename, content_type=content_type, ingestion_id=ingestion_id),
        db,
    )


@router.post("/batch", response_model=BatchIngestResponse)
@limiter.limit(settings.RATE_LIMIT_INGEST)
async def ingest_batch(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
    source: str = Form("api"),
    source_type: str = Form("batch"),
    file: UploadFile = File(...),
):
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds MAX_UPLOAD_BYTES")

    text = data.decode("utf-8", errors="replace")
    filename = file.filename or "batch.log"

    if filename.lower().endswith((".evtx", ".evt")):
        payloads = [item.encode("utf-8") for item in extract_windows_event_records(data)]
        if not payloads:
            raise HTTPException(status_code=400, detail="Could not extract Windows event records from EVTX/EVT payload")
        lines = payloads
    else:
        # Split rules by extension
        if filename.endswith(".jsonl"):
            lines = [ln for ln in text.splitlines() if ln.strip()]
        elif filename.endswith(".csv"):
            lines = text.splitlines()
            if lines:
                lines = [",".join(lines[0].split(","))] if False else lines  # CSV handled per-row below
        else:
            # Split on blank lines, but treat each non-empty line as its own event
            # if the file is line-oriented log (default behavior).
            lines = [ln for ln in text.splitlines() if ln.strip()]

    ingestion_id = str(uuid.uuid4())
    accepted = 0
    rejected = 0
    events_out: list[IngestResponse] = []

    for ln in lines[:10000]:  # bounded batch
        raw_bytes = ln if isinstance(ln, bytes) else ln.encode("utf-8")
        if not raw_bytes:
            continue
        try:
            ev = ingest_event(
                db, raw_bytes=raw_bytes, source=source, source_type=source_type,
                filename=filename, content_type="application/xml" if filename.lower().endswith((".evtx", ".evt")) else "text/plain",
                ingestion_id=ingestion_id,
            )
            events_out.append(_response(ev, db))
            if ev.processing_status in ("PROCESSED", "WARNING"):
                accepted += 1
            else:
                rejected += 1
        except Exception:
            rejected += 1

    record_audit(db, actor=user.email, action="INGEST_BATCH", resource="batch",
                 resource_id=ingestion_id, new_state={"accepted": accepted, "rejected": rejected})
    db.commit()
    return BatchIngestResponse(
        ingestion_id=ingestion_id, total=len(lines), accepted=accepted,
        rejected=rejected, events=events_out,
    )