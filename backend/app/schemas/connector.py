from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    connector_id: str | None = None
    hostname: str
    os: str = "unknown"
    version: str = "0.0.0"
    adapters: list[str] = Field(default_factory=list)             
    available_adapters: list[str] = Field(default_factory=list)  
    events_total: int = 0
    last_event_at: datetime | None = None


class HeartbeatResponse(BaseModel):
    connector_id: str
    accepted: bool = True


class ConnectorItem(BaseModel):
    connector_id: str
    hostname: str
    os: str
    version: str
    adapters: list[str]                       # running
    available_adapters: list[str]             # NEW
    desired_adapters: list[str] | None        # NEW — null = no opinion
    config_poll_interval_s: int               # NEW
    first_seen: datetime
    last_heartbeat: datetime
    last_event_at: datetime | None = None
    events_total: int
    status: str

class ConnectorConfig(BaseModel):
    """Response to GET /connectors/{id}/config — what the connector polls."""
    desired_adapters: list[str] | None
    poll_interval_s: int

class ConnectorConfigUpdate(BaseModel):
    """Body for POST /connectors/{id}/config — what the UI sends."""
    desired_adapters: list[str] | None
    poll_interval_s: int | None = None
    
class ConnectorList(BaseModel):
    items: list[ConnectorItem]
    total: int