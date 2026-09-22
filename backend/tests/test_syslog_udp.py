"""Tests for the Syslog UDP ingestion front door.

Two levels:
1. Handler-level: call handle_datagram() directly with a synthetic
   datagram — proves the adapter correctly calls ingest_event().
2. Socket-level: start the real UDP listener on an ephemeral port, send
   one datagram via socket.sendto(), poll the DB for the resulting Event
   row — proves the socket wiring and protocol adapter work.

The listener is only started when SYSLOG_UDP_ENABLED is set; tests set it
explicitly on the Settings object they construct, not via the process env,
so the rest of the suite is unaffected.
"""
from __future__ import annotations

import asyncio
import os
import socket
import time

import pytest
from sqlalchemy import desc

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.event import Event
from app.syslog.udp_listener import SyslogUdpListener


SAMPLE_RFC5424 = b"<34>1 2026-01-15T10:00:00Z host app 1 ID47 - test message"

SOCKET_SAMPLE_RFC5424 = (
    b"<34>1 2026-01-15T10:00:01Z socket-test-host app 2 ID48 - "
    b"distinct socket-path test message with unique content"
)

def _free_udp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def test_syslog_udp_handler_creates_event(db):
    """Handler must persist an Event via ingest_event(), source_type=syslog_udp."""
    listener = SyslogUdpListener(host="127.0.0.1", port=0)
    listener.handle_datagram(SAMPLE_RFC5424, "203.0.113.5")

    # Use a fresh session — handler used its own SessionLocal.
    s = SessionLocal()
    try:
        ev = s.query(Event).order_by(desc(Event.ingested_at)).first()
        assert ev is not None
        assert ev.source_type == "syslog_udp"
        assert ev.source == "203.0.113.5"
        assert ev.raw_size == len(SAMPLE_RFC5424)
        assert ev.filename == "syslog"
        assert ev.content_type == "text/plain"
    finally:
        s.close()


def test_syslog_udp_handler_drops_oversized_datagram(monkeypatch):
    """Datagrams larger than MAX_EVENT_BYTES must be dropped, not ingested."""
    # Shrink the limit so we don't need a real 1 MiB payload.
    monkeypatch.setattr(settings, "MAX_EVENT_BYTES", 64, raising=False)

    listener = SyslogUdpListener(host="127.0.0.1", port=0)
    before = _latest_event_count()
    listener.handle_datagram(b"x" * 200, "203.0.113.6")
    after = _latest_event_count()
    assert after == before, "oversized datagram must not create an Event row"


def _latest_event_count() -> int:
    s = SessionLocal()
    try:
        return s.query(Event).count()
    finally:
        s.close()


def test_syslog_udp_socket_end_to_end():
    """Real UDP socket → protocol → handler → Event row."""
    from datetime import datetime, timezone

    port = _free_udp_port()
    listener = SyslogUdpListener(host="127.0.0.1", port=port)

    async def _run():
        await listener.start()
        try:
            # Snapshot the wall clock just before sending so we can filter
            # on ingested_at and exclude any earlier test's events.
            started_at = datetime.now(timezone.utc)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto(SOCKET_SAMPLE_RFC5424, ("127.0.0.1", port))
            finally:
                sock.close()

            # Poll for an event that is uniquely ours:
            #   source_type = syslog_udp
            #   raw_size    = length of SOCKET_SAMPLE_RFC5424
            #   ingested_at >= started_at
            deadline = time.time() + 3.0
            found = None
            while time.time() < deadline:
                s = SessionLocal()
                try:
                    found = (
                        s.query(Event)
                        .filter(Event.source_type == "syslog_udp")
                        .filter(Event.raw_size == len(SOCKET_SAMPLE_RFC5424))
                        .filter(Event.ingested_at >= started_at)
                        .order_by(desc(Event.ingested_at))
                        .first()
                    )
                finally:
                    s.close()
                if found is not None:
                    break
                await asyncio.sleep(0.05)

            assert found is not None, (
                "no syslog_udp Event row created for the socket-path datagram"
            )
            assert found.source == "127.0.0.1"
            assert found.raw_size == len(SOCKET_SAMPLE_RFC5424)
        finally:
            await listener.stop()

    try:
        asyncio.run(_run())
    except OSError as e:
        pytest.skip(f"could not bind ephemeral UDP port: {e}")