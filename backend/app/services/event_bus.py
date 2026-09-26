"""Redis pub/sub event bus for SSE streaming.

publish_event() is called from the ingestion side after db.commit().
subscribe() is consumed by the SSE endpoint to fan out to connected clients.

Degraded mode: if Redis is unavailable or REDIS_URL=memory://, both
operations are silent no-ops. The SSE endpoint still replays Last-Event-ID
and sends keepalives, but does not deliver live events. This is documented
in the connector README and the settings UI.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from app.core.config import settings

log = logging.getLogger(__name__)


def _is_redis_available() -> bool:
    url = settings.REDIS_URL or ""
    return url.startswith("redis://") or url.startswith("rediss://") or url.startswith("unix://")


def publish_event(event_id: str, payload: dict) -> None:
    """Publish one event to the bus. Best-effort — never raises."""
    if not _is_redis_available():
        return
    try:
        import redis  # redis-py
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        client.publish(
            settings.EVENT_BUS_CHANNEL,
            json.dumps({"event_id": event_id, "payload": payload}, default=str),
        )
    except Exception as e:
        log.warning("event_bus.publish_failed event_id=%s error=%s", event_id, e)


async def subscribe() -> AsyncIterator[dict]:
    """Yield messages from the bus as dicts. Blocks forever.

    Caller is responsible for closing when the client disconnects.
    """
    if not _is_redis_available():
        # Degraded mode: yield nothing, sleep forever so the caller's loop
        # still produces keepalives on its own.
        import asyncio
        while True:
            await asyncio.sleep(3600)
    import redis.asyncio as redis_async  # type: ignore
    client = redis_async.Redis.from_url(settings.REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(settings.EVENT_BUS_CHANNEL)
    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            try:
                data = msg["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield json.loads(data)
            except Exception as e:
                log.warning("event_bus.decode_failed error=%s", e)
    finally:
        try:
            await pubsub.unsubscribe(settings.EVENT_BUS_CHANNEL)
            await pubsub.close()
            await client.close()
        except Exception:
            pass