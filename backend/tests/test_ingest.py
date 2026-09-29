def test_ingest_cef_event(client, analyst_headers):
    raw = ("CEF:0|Acme|AuthApp|1.0|4625|Failed Logon|7|"
           "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=admin outcome=failure")
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["processing_status"] in ("PROCESSED", "WARNING")
    assert data["detected_format"] == "CEF"
    assert data["detection_confidence"] > 0.9
    assert data["parser_id"] == "cef"
    assert data["sha256"] and len(data["sha256"]) == 64


def test_ingest_json_event(client, analyst_headers):
    payload = {
        "@timestamp": "2026-01-15T10:40:00Z",
        "event_type": "authentication",
        "user": "alice",
        "src_ip": "198.51.100.10",
        "status": "success",
        "severity": "LOW",
    }
    r = client.post("/api/v1/ingest", json={"payload": payload, "filename": "a.json"}, headers=analyst_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["detected_format"] == "JSON"
    assert data["processing_status"] in ("PROCESSED", "WARNING")


def test_ingest_malformed_quarantines(client, analyst_headers):
    raw = "CEF:0|broken|header only"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    data = r.json()
    # Detection may fail or parser may fail — both routes lead to quarantine
    assert data["processing_status"] in ("QUARANTINED", "FAILED")


def test_ingest_requires_authentication(client):
    r = client.post("/api/v1/ingest", json={"raw": "test"})
    assert r.status_code == 401


def test_ingest_batch(client, analyst_headers):
    content = (
        "CEF:0|V|P|1|1|A|3|rt=2026-01-15T10:00:00Z src=1.2.3.4\n"
        "CEF:0|V|P|1|2|B|3|rt=2026-01-15T10:00:01Z src=1.2.3.5\n"
    )
    files = {"file": ("batch.log", content, "text/plain")}
    r = client.post("/api/v1/ingest/batch", files=files, headers=analyst_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2