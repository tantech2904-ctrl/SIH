"""Syslog ingestion front doors.

Each listener is a thin adapter: it receives bytes, wraps them with source
metadata, and calls the existing ingest_event() pipeline. No pipeline logic
is ever duplicated here — see app/services/ingest_service.py for the
invariant.
"""
from app.syslog.udp_listener import SyslogUdpListener  # noqa: F401

__all__ = ["SyslogUdpListener"]