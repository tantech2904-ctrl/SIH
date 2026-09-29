from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.evidence import RawEvidence
from app.storage.minio_store import get_object_store


def compute_sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def preserve_evidence(
    *,
    db: Session,
    event_id: str,
    raw_bytes: bytes,
    source: str,
    content_type: str,
    preview_bytes: int = 2048,
) -> RawEvidence:
    """Persist raw bytes to object storage + create evidence record.

    This MUST be called before any enrichment or external call.
    """
    store = get_object_store()
    digest = compute_sha256(raw_bytes)
    key = f"{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{event_id}/{digest[:16]}.bin"
    location = store.put_bytes(key, raw_bytes, content_type=content_type)

    preview = raw_bytes[:preview_bytes].decode("utf-8", errors="replace")

    evidence = RawEvidence(
        evidence_id=str(uuid.uuid4()),
        event_id=event_id,
        sha256=digest,
        raw_size=len(raw_bytes),
        source=source,
        storage_backend="minio" if location.startswith("minio://") else "local",
        storage_location=location,
        content_type=content_type,
        preservation_status="PRESERVED",
        preview=preview,
    )
    db.add(evidence)
    db.flush()
    return evidence