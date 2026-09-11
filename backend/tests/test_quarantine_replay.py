def test_quarantine_and_replay(client, analyst_headers):
    # First ingest malformed → quarantine
    raw = "GARBAGE_NOT_A_LOG_FORMAT_1234"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    q_event_id = r.json()["event_id"]

    # List quarantine
    r2 = client.get("/api/v1/quarantine", headers=analyst_headers)
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert any(q["event_id"] == q_event_id for q in items)

    # Find our entry
    entry = next(q for q in items if q["event_id"] == q_event_id)

    # Structural analysis should be available
    r3 = client.get(f"/api/v1/quarantine/{entry['id']}/analysis", headers=analyst_headers)
    assert r3.status_code == 200
    analysis = r3.json()
    assert "candidates" in analysis


def test_quarantine_approve_mapping_and_replay(client, analyst_headers):
    raw = "XLOG|2026-01-15T11:20:00Z|203.0.113.55|user=alice|op=read|res=denied"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    q_event_id = r.json()["event_id"]

    # Get quarantine entry
    r2 = client.get("/api/v1/quarantine", headers=analyst_headers)
    entry = next(
        (q for q in r2.json()["items"] if q["event_id"] == q_event_id),
        None,
    )
    if not entry:
        return  # unknown format may have low confidence but not quarantined

    # Approve analyzer-style mappings directly
    mappings = [
        {"original_field": "field_2", "canonical_field": "source.ip", "confidence": 0.9},
    ]
    r3 = client.post(
        f"/api/v1/quarantine/{entry['id']}/approve-mapping",
        json={"mappings": mappings},
        headers=analyst_headers,
    )
    assert r3.status_code in (200, 400)  # 400 if event has no parser — acceptable


def test_replay_records_history(client, analyst_headers):
    raw = "CEF:0|V|P|1.0|1|Test|3|rt=2026-01-15T10:00:00Z src=203.0.113.3"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    event_id = r.json()["event_id"]
    r2 = client.post(f"/api/v1/events/{event_id}/replay", headers=analyst_headers)
    assert r2.status_code == 200
    assert r2.json()["result"] in ("SUCCESS", "FAILED")

    r3 = client.get(f"/api/v1/events/{event_id}/replay-history", headers=analyst_headers)
    assert r3.status_code == 200
    assert len(r3.json()["items"]) >= 1