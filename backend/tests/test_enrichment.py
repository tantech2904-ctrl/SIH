def test_provider_status_endpoint(client, analyst_headers):
    r = client.get("/api/v1/enrichment/providers/status", headers=analyst_headers)
    assert r.status_code == 200
    names = {p["provider"] for p in r.json()["providers"]}
    assert "VirusTotal" in names
    assert "GeoIP" in names


def test_unconfigured_provider_returns_not_configured(client, analyst_headers):
    # With no API keys in test env, VirusTotal must report NOT_CONFIGURED
    r = client.get("/api/v1/threat-intel/203.0.113.5", headers=analyst_headers)
    assert r.status_code == 200
    results = r.json()["results"]
    vt = next((x for x in results if x["provider"] == "VirusTotal"), None)
    assert vt is not None
    assert vt["status"] == "NOT_CONFIGURED"


def test_invalid_indicator_type_rejected(client, analyst_headers):
    r = client.get("/api/v1/threat-intel/not-an-indicator", headers=analyst_headers)
    # Either 200 with empty results or 400 — never a crash
    assert r.status_code in (200, 400)