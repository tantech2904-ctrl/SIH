"""Event bus for SSE streaming.

Supports:
1. Redis pub/sub (production & docker compose)
2. In-memory asynchronous queue broadcast (local dev mode / memory:// / redis offline fallback)

publish_event() is called from the ingestion side after db.commit().
subscribe() is consumed by the SSE endpoint to fan out to connected clients.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Set

from app.core.config import settings

log = logging.getLogger(__name__)

# In-memory subscriber queues for local mode or fallback
_memory_subscribers: Set[asyncio.Queue] = set()
_memory_loop: asyncio.AbstractEventLoop | None = None


def _is_redis_available() -> bool:
    url = settings.REDIS_URL or ""
    return url.startswith("redis://") or url.startswith("rediss://") or url.startswith("unix://")


def publish_event(event_id: str, payload: dict, tenant_id: str = "default") -> None:
    """Publish one event to the bus. Best-effort — never raises."""
    msg_data = {"event_id": event_id, "tenant_id": tenant_id, "payload": payload}

    # If Redis is configured, try publishing to Redis
    if _is_redis_available():
        try:
            import redis
            client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
            client.publish(
                settings.EVENT_BUS_CHANNEL,
                json.dumps(msg_data, default=str),
            )
            return
        except Exception as e:
            log.warning("event_bus.redis_publish_failed event_id=%s error=%s (falling back to in-memory)", event_id, e)

    # In-memory broadcast fallback
    if _memory_subscribers:
        dead_queues = set()
        for q in list(_memory_subscribers):
            try:
                q.put_nowait(msg_data)
            except Exception:
                dead_queues.add(q)
        for dead in dead_queues:
            _memory_subscribers.discard(dead)


async def subscribe() -> AsyncIterator[dict]:
    """Yield messages from the bus as dicts. Blocks forever.

    Caller is responsible for closing when the client disconnects.
    """
    if _is_redis_available():
        try:
            import redis.asyncio as redis_async
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
            return
        except Exception as e:
            log.warning("event_bus.redis_subscribe_failed error=%s (using in-memory bus)", e)

    # In-memory broadcast subscription
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _memory_subscribers.add(queue)
    try:
        while True:
            item = await queue.get()
            yield item
    finally:
        _memory_subscribers.discard(queue)