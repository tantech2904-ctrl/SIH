from app.normalization.cse import CSEMapper


def test_cef_mapping_to_cse():
    fields = {
        "timestamp": "2026-01-15T10:22:03Z",
        "src": "203.0.113.5",
        "dst": "10.0.0.5",
        "suser": "administrator",
        "outcome": "failure",
        "proto": "tcp",
        "severity": "7",
        "vendor": "Acme",
        "message": "Failed logon",
        "format": "CEF",
    }
    mapper = CSEMapper(parser_id="cef")
    res = mapper.map(fields)
    assert res.fields["source.ip"] == "203.0.113.5"
    assert res.fields["destination.ip"] == "10.0.0.5"
    assert res.fields["user.name"] == "administrator"
    assert res.fields["status"] == "failure"
    assert res.fields["protocol"] == "tcp"
    assert res.fields["severity"] == "HIGH"  # numeric 7 → HIGH
    assert "timestamp" in res.fields


def test_mapping_provenance_recorded():
    fields = {"src_ip": "1.2.3.4", "@timestamp": "2026-01-15T10:00:00Z"}
    mapper = CSEMapper(parser_id="json")
    res = mapper.map(fields)
    originals = {p.original_field for p in res.provenance}
    assert "src_ip" in originals
    canon = {p.canonical_field for p in res.provenance}
    assert "source.ip" in canon


def test_custom_mapping_overrides_alias():
    fields = {"whatever_field": "1.2.3.4"}
    mapper = CSEMapper(
        parser_id="json",
        custom_mappings={"whatever_field": {"canonical": "source.ip", "confidence": 1.0, "source": "analyst"}},
    )
    res = mapper.map(fields)
    assert res.fields["source.ip"] == "1.2.3.4"
    src = [p for p in res.provenance if p.original_field == "whatever_field"][0]
    assert src.source == "analyst"


def test_severity_numeric_and_word():
    mapper = CSEMapper()
    assert mapper.map({"severity": "0"})["fields"]["severity"] == "INFO"
    assert mapper.map({"severity": "10"})["fields"]["severity"] == "CRITICAL"
    assert mapper.map({"severity": "critical"})["fields"]["severity"] == "CRITICAL"
    assert mapper.map({"severity": "warning"})["fields"]["severity"] == "MEDIUM"


def test_private_ip_accepted():
    mapper = CSEMapper()
    res = mapper.map({"src_ip": "10.0.0.1"})
    assert res.fields["source.ip"] == "10.0.0.1"


def test_invalid_ip_rejected():
    mapper = CSEMapper()
    res = mapper.map({"src_ip": "999.999.999.999"})
    assert "source.ip" not in res.fields
    assert "src_ip" in res.unmapped