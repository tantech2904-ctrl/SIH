"""Syslog UDP listener.

Design notes:
- Thin adapter over ingest_event(). Never reimplements pipeline steps.
- Each received datagram is one event (RFC 5426, UDP transport).
- Oversized datagrams are dropped with a logged reason, never truncated.
- Runs as an asyncio task from app/main.py's lifespan.
- Audit entries use actor="system:syslog_udp".

A future SyslogTcpListener (RFC 6587) would live next to this module and
share the same _handle_payload() logic.
"""
from __future__ import annotations

import asyncio
import socket
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.audit_service import record_audit
from app.services.ingest_service import ingest_event

log = get_logger(__name__)

# One datagram should never exceed this. The HTTP path enforces
# MAX_EVENT_BYTES; we mirror that behavior for UDP.
_MAX_DATAGRAM_BYTES = 65535  # hard UDP ceiling
_SOURCE_TYPE = "syslog_udp"
_FILENAME = "syslog"
_CONTENT_TYPE = "text/plain"
_AUDIT_ACTOR = "system:syslog_udp"


class _UdpProtocol(asyncio.DatagramProtocol):
    """asyncio protocol adapter that forwards datagrams to the listener."""

    def __init__(self, listener: "SyslogUdpListener") -> None:
        self._listener = listener

    def datagram_received(self, data: bytes, addr) -> None:
        # Fire-and-forget: the handler is synchronous DB work, so we run it
        # in the default executor to avoid blocking the event loop.
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, self._listener.handle_datagram, data, addr[0])

    def error_received(self, exc: Exception) -> None:
        log.warning("syslog.udp.error_received", error=str(exc))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc is not None:
            log.warning("syslog.udp.connection_lost", error=str(exc))
        else:
            log.info("syslog.udp.connection_closed")


class SyslogUdpListener:
    """UDP listener for syslog datagrams."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._transport: Optional[asyncio.DatagramTransport] = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _UdpProtocol(self),
            local_addr=(self.host, self.port),
            family=socket.AF_INET,
        )
        self._transport = transport
        log.info(
            "syslog.udp.listening",
            host=self.host,
            port=self.port,
            max_bytes=settings.MAX_EVENT_BYTES,
        )

    async def stop(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            log.info("syslog.udp.stopped")

    # -- synchronous handler, unit-testable without a socket ----------------

    def handle_datagram(self, raw_bytes: bytes, sender: str) -> None:
        """Process a single received datagram.

        Invariant: raw is preserved first via ingest_event(); we do not
        touch the pipeline itself. Any failure is logged and swallowed —
        a bad datagram must never crash the listener.
        """
        if not raw_bytes:
            log.debug("syslog.udp.empty_datagram", sender=sender)
            return

        if len(raw_bytes) > settings.MAX_EVENT_BYTES:
            log.warning(
                "syslog.udp.oversized_dropped",
                sender=sender,
                size=len(raw_bytes),
                max=settings.MAX_EVENT_BYTES,
            )
            return

        if len(raw_bytes) > _MAX_DATAGRAM_BYTES:
            # Should be impossible since UDP caps at 65535, but be explicit.
            log.warning("syslog.udp.datagram_over_udp_max", sender=sender, size=len(raw_bytes))
            return

        db = SessionLocal()
        try:
            event = ingest_event(
                db,
                raw_bytes=raw_bytes,
                source=sender,
                source_type=_SOURCE_TYPE,
                filename=_FILENAME,
                content_type=_CONTENT_TYPE,
            )
            record_audit(
                db,
                actor=_AUDIT_ACTOR,
                action="INGEST_SYSLOG_UDP",
                resource="event",
                resource_id=event.event_id,
                source_ip=sender,
                new_state={
                    "processing_status": event.processing_status,
                    "detected_format": event.detected_format,
                    "raw_size": event.raw_size,
                },
            )
            db.commit()
            log.info(
                "syslog.udp.ingested",
                sender=sender,
                event_id=event.event_id,
                status=event.processing_status,
                size=len(raw_bytes),
            )
        except Exception as e:
            db.rollback()
            log.exception(
                "syslog.udp.ingest_failed",
                sender=sender,
                size=len(raw_bytes),
                error=str(e)[:500],
            )
        finally:
            db.close()