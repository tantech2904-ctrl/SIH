from typing import Any
from pydantic import BaseModel, Field


class IngestJsonRequest(BaseModel):
    """Ingest a single event via JSON body. If `raw` is provided it is used
    verbatim; otherwise the whole payload (minus this field) is serialized."""
    raw: str | None = None
    source: str = "api"
    source_type: str = "api"
    filename: str = "inline.json"
    content_type: str = "application/json"
    payload: dict[str, Any] | None = None


class IngestResponse(BaseModel):
    event_id: str
    ingestion_id: str
    correlation_id: str
    processing_status: str
    detected_format: str | None = None
    detection_confidence: float | None = None
    parser_id: str | None = None
    sha256: str | None = None
    message: str | None = None


class BatchIngestResponse(BaseModel):
    ingestion_id: str
    total: int
    accepted: int
    rejected: int
    events: list[IngestResponse]