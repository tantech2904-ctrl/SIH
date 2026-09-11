from typing import Any, Optional
from pydantic import BaseModel


class EventListItem(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    category: str
    severity: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    user_name: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    message: Optional[str] = None
    risk_score: Optional[int] = None
    processing_status: str
    detected_format: Optional[str] = None
    parser_id: Optional[str] = None


class EventDetail(BaseModel):
    event_id: str
    ingestion_id: str
    correlation_id: str
    ingested_at: Optional[str]
    source: str
    source_type: str
    filename: str
    content_type: str
    raw_size: int
    detected_format: Optional[str]
    detection_confidence: Optional[float]
    parser_id: Optional[str]
    parser_version: Optional[str]
    processing_status: str
    error_message: Optional[str]
    severity: Optional[str]
    risk_score: Optional[int]
    sha256: Optional[str]
    canonical: Optional[dict[str, Any]]


class EventRaw(BaseModel):
    event_id: str
    content_type: str
    raw_size: int
    sha256: str
    content: str


class EventNormalized(BaseModel):
    event_id: str
    canonical: dict[str, Any]


class EventTimeline(BaseModel):
    event_id: str
    stages: list[dict[str, Any]]