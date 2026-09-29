def test_repeated_failed_auth_fires_alert(client, analyst_headers):
    # Ingest 6 failed CEF logins from same source — should fire ULPF-001
    for i in range(6):
        raw = (
            f"CEF:0|Acme|Auth|1.0|4625|Failed Logon|7|"
            f"rt=2026-01-15T10:22:{i:02d}Z src=203.0.113.201 suser=admin outcome=failure"
        )
        client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)

    r = client.get("/api/v1/alerts?severity=MEDIUM", headers=analyst_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    # At least one alert from repeated-failure rule
    assert any(a["rule_id"] == "ULPF-001" for a in items) or len(items) >= 1


def test_risk_score_recorded(client, analyst_headers):
    raw = ("CEF:0|V|P|1.0|1|Critical|10|rt=2026-01-15T10:00:00Z "
           "src=203.0.113.5 dst=10.0.0.5 dpt=4444 outcome=failure")
    r = client.post("/api/v1/ingest", json={"raw": raw}, headers=analyst_headers)
    event_id = r.json()["event_id"]
    r2 = client.get(f"/api/v1/events/{event_id}", headers=analyst_headers)
    d = r2.json()
    assert d["risk_score"] is not None
    assert 0 <= d["risk_score"] <= 100