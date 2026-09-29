from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.evidence import RawEvidence
from app.services.evidence_service import compute_sha256
from app.storage.minio_store import get_object_store


def _key_from_location(location: str, bucket: str | None = None) -> str:
    """Extract the object-store key from a location descriptor."""
    if location.startswith("minio://"):
        # minio://bucket/key
        parts = location.split("/", 3)
        return parts[3] if len(parts) > 3 else ""
    if location.startswith("local://"):
        base = "./data/raw"
        path = location[len("local://"):]
        return path.replace(f"{base}/", "", 1)
    return location


def verify_integrity(db: Session, evidence: RawEvidence) -> dict:
    store = get_object_store()
    key = _key_from_location(evidence.storage_location)
    result = {
        "evidence_id": evidence.evidence_id,
        "original_hash": evidence.sha256,
        "recalculated_hash": None,
        "integrity_status": "UNAVAILABLE",
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        data = store.get_bytes(key)
    except Exception:
        return result

    recalc = compute_sha256(data)
    result["recalculated_hash"] = recalc
    result["integrity_status"] = "VERIFIED" if recalc == evidence.sha256 else "MISMATCH"

    evidence.accessed_count += 1
    evidence.last_accessed_at = datetime.now(timezone.utc)
    db.flush()
    return result