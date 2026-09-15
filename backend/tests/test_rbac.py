def test_admin_can_access_audit(client, admin_headers):
    r = client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200


def test_auditor_can_access_audit(client, auditor_headers):
    r = client.get("/api/v1/audit", headers=auditor_headers)
    assert r.status_code == 200


def test_auditor_cannot_ingest(client, auditor_headers):
    r = client.post("/api/v1/ingest", json={"raw": "test"}, headers=auditor_headers)
    assert r.status_code == 403


def test_analyst_can_ingest(client, analyst_headers):
    raw = "CEF:0|V|P|1.0|1|Test|3|rt=2026-01-15T10:00:00Z src=1.2.3.4"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200


def test_no_token_rejected(client):
    r = client.get("/api/v1/events")
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/api/v1/events", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401