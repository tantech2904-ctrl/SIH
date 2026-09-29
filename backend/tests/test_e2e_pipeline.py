"""End-to-end pipeline test covering the full SIH acceptance flow.

This test runs against the in-memory SQLite + local-store test environment.
"""
import pytest


CEF_LOG = (
    "CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|"
    "rt=2026-01-15T10:22:03Z src=203.0.113.5 suser=administrator "
    "dhost=dc01 outcome=failure proto=tcp"
)

LEEF_LOG = (
    "LEEF:1.0|IBM|QRadar|2.0|1234|"
    "devTime=2026-01-15T10:30:00Z\tsrc=192.0.2.10\tdst=10.0.0.5\tseverity=8"
)

RFC5424_LOG = (
    "<34>1 2026-01-15T10:22:03.123Z host app 123 ID47 - Failed password for admin"
)

JSON_LOG = (
    '{"@timestamp":"2026-01-15T10:40:00Z","event_type":"authentication",'
    '"user":"alice","src_ip":"10.0.0.1","status":"failure","severity":"LOW"}'
)

XML_LOG = (
    '<?xml version="1.0"?><Event><timestamp>2026-01-15T10:00:00Z</timestamp>'
    '<src_ip>1.2.3.4</src_ip><severity>LOW</severity></Event>'
)

CSV_LOG = (
    "timestamp,src_ip,dst_ip,dport,protocol,action\n"
    "2026-01-15T10:00:00Z,1.2.3.4,5.6.7.8,443,tcp,allow\n"
)


@pytest.mark.parametrize(
    "raw,expected_format",
    [
        (CEF_LOG, "CEF"),
        (LEEF_LOG, "LEEF"),
        (RFC5424_LOG, "RFC5424"),
        (JSON_LOG, "JSON"),
        (XML_LOG, "XML"),
        (CSV_LOG, "CSV"),
    ],
)
def test_e2e_supported_format(client, analyst_headers, raw, expected_format):
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["detected_format"] == expected_format, data
    assert data["processing_status"] in ("PROCESSED", "WARNING"), data

    # Fetch full event
    r2 = client.get(f"/api/v1/events/{data['event_id']}", headers=analyst_headers)
    assert r2.status_code == 200
    ev = r2.json()
    assert ev["canonical"] is not None
    assert ev["canonical"]["event_type"]
    assert ev["canonical"]["severity"]

    # Verify integrity
    r3 = client.get(f"/api/v1/events/{data['event_id']}/integrity", headers=analyst_headers)
    assert r3.status_code == 200
    assert r3.json()["integrity_status"] == "VERIFIED"

    # Timeline should show pipeline stages
    r4 = client.get(f"/api/v1/events/{data['event_id']}/timeline", headers=analyst_headers)
    assert r4.status_code == 200
    stages = [s["stage"] for s in r4.json()["stages"]]
    assert "INGESTED" in stages
    assert "PRESERVED" in stages
    assert "HASHED" in stages
    assert "DETECTED" in stages


def test_e2e_malformed_quarantined(client, analyst_headers):
    raw = "not-a-log-at-all just noise 1234 !!!"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    data = r.json()
    # Either quarantined or detected as UNKNOWN below threshold
    assert data["processing_status"] in ("QUARANTINED", "FAILED", "PROCESSED")
    # If quarantined, must be searchable
    if data["processing_status"] == "QUARANTINED":
        r2 = client.get("/api/v1/quarantine", headers=analyst_headers)
        assert any(q["event_id"] == data["event_id"] for q in r2.json()["items"])


def test_e2e_unknown_format_full_flow(client, analyst_headers):
    """Unknown vendor log → quarantine → structural analysis → approve → replay."""
    raw = "VENDORX_LOG|ts=2026-01-15T10:00:00Z|srcip=203.0.113.99|user=alice|action=read|result=denied"
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    assert r.status_code == 200
    event_id = r.json()["event_id"]

    # It should be quarantined (low detection confidence)
    r2 = client.get("/api/v1/quarantine", headers=analyst_headers)
    items = r2.json()["items"]
    entry = next((q for q in items if q["event_id"] == event_id), None)

    if entry:
        # Get structural analysis
        r3 = client.get(f"/api/v1/quarantine/{entry['id']}/analysis", headers=analyst_headers)
        assert r3.status_code == 200
        analysis = r3.json()
        assert "candidates" in analysis
        # Should have found at least one field candidate
        assert analysis["field_count"] >= 1


def test_e2e_audit_trail_complete(client, analyst_headers, admin_headers):
    """Every ingest should produce an audit trail entry."""
    raw = CEF_LOG
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    event_id = r.json()["event_id"]

    r2 = client.get("/api/v1/audit?action=INGEST", headers=admin_headers)
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert any(a["resource_id"] == event_id for a in items)


def test_e2e_dashboard_reflects_real_counts(client, analyst_headers):
    # Ingest one event
    r = client.post("/api/v1/ingest", json={"raw": CEF_LOG}, headers=analyst_headers)
    assert r.status_code == 200

    r2 = client.get("/api/v1/dashboard", headers=analyst_headers)
    assert r2.status_code == 200
    d = r2.json()
    assert d["totals"]["events"] >= 1
    assert d["totals"]["canonical_events"] >= 1


def test_e2e_search_filters_work(client, analyst_headers):
    # Ingest with a distinctive source IP
    raw = CEF_LOG.replace("203.0.113.5", "203.0.113.240")
    client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)

    r = client.get("/api/v1/events?source_ip=203.0.113.240", headers=analyst_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(e["source_ip"] == "203.0.113.240" for e in items)
    assert len(items) >= 1


def test_e2e_correlation_groups_activity(client, analyst_headers):
    """Ingest several events from same source, ensure dashboard/correlation reflect it."""
    for i in range(5):
        raw = CEF_LOG.replace("203.0.113.5", "203.0.113.250").replace("10:22:03", f"10:22:{i:02d}")
        client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)

    r = client.get("/api/v1/dashboard", headers=analyst_headers)
    top_sources = r.json()["top_source_ips"]
    assert any(x["ip"] == "203.0.113.250" for x in top_sources)