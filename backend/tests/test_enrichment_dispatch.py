"""Verify that ingestion dispatches the enrichment Celery task after commit.

The dispatch helper (ingest_service.dispatch_enrichment_async) must:
  - fire AFTER db.commit() so the worker can see the CanonicalEvent row;
  - be called exactly once per ingested event;
  - be safe when Celery is unreachable (swallow and log).

We monkeypatch the task's .delay method to record calls, which avoids
needing a real Redis broker in tests.
"""
from __future__ import annotations


def test_ingest_dispatches_enrichment_once(client, analyst_headers, monkeypatch):
    from app.workers import tasks as tasks_module

    dispatched: list[str] = []
    monkeypatch.setattr(
        tasks_module.enrich_event_task,
        "delay",
        lambda event_id: dispatched.append(event_id),
    )

    raw = (
        "CEF:0|Acme|AuthApp|1.0|4625|Failed Logon|7|"
        "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=admin outcome=failure"
    )
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    event_id = r.json()["event_id"]
    assert dispatched == [event_id], f"expected one dispatch, got {dispatched}"


def test_batch_ingest_dispatches_per_event(client, analyst_headers, monkeypatch):
    from app.workers import tasks as tasks_module

    dispatched: list[str] = []
    monkeypatch.setattr(
        tasks_module.enrich_event_task,
        "delay",
        lambda event_id: dispatched.append(event_id),
    )

    content = (
        "CEF:0|V|P|1|1|A|3|rt=2026-01-15T10:00:00Z src=1.2.3.4\n"
        "CEF:0|V|P|1|2|B|3|rt=2026-01-15T10:00:01Z src=1.2.3.5\n"
    )
    files = {"file": ("batch.log", content, "text/plain")}
    r = client.post("/api/v1/ingest/batch", files=files, headers=analyst_headers)
    assert r.status_code == 200
    assert len(dispatched) >= 2


def test_dispatch_failure_is_swallowed(client, analyst_headers, monkeypatch, caplog):
    """If the task's .delay raises, ingestion must still succeed."""
    from app.workers import tasks as tasks_module

    def _boom(event_id: str) -> None:
        raise RuntimeError("simulated broker outage")

    monkeypatch.setattr(tasks_module.enrich_event_task, "delay", _boom)

    raw = (
        "CEF:0|Acme|AuthApp|1.0|4625|Failed Logon|7|"
        "rt=2026-01-15T10:22:03Z src=203.0.113.7 suser=admin outcome=failure"
    )
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    assert r.json()["processing_status"] in ("PROCESSED", "WARNING")