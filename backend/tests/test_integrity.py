def test_integrity_verified(client, analyst_headers):
    raw = ("CEF:0|V|P|1.0|1|Test|3|rt=2026-01-15T10:00:00Z src=203.0.113.1")
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    event_id = r.json()["event_id"]
    r2 = client.get(f"/api/v1/events/{event_id}/integrity", headers=analyst_headers)
    assert r2.status_code == 200
    d = r2.json()
    assert d["integrity_status"] == "VERIFIED"
    assert d["original_hash"] == d["recalculated_hash"]
    assert len(d["original_hash"]) == 64


def test_evidence_access_is_audited(client, analyst_headers, auditor_headers):
    raw = ("CEF:0|V|P|1.0|1|Test|3|rt=2026-01-15T10:00:00Z src=203.0.113.2")
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    event_id = r.json()["event_id"]
    client.get(f"/api/v1/events/{event_id}/raw", headers=analyst_headers)
    # Auditor should see EVIDENCE_ACCESS in audit
    r2 = client.get("/api/v1/audit?action=EVIDENCE_ACCESS", headers=auditor_headers)
    assert r2.status_code == 200
    assert any(e["action"] == "EVIDENCE_ACCESS" for e in r2.json()["items"])