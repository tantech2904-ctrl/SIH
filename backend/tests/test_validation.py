from app.validation.validator import validate_cse


def test_valid_cse():
    cse = {
        "timestamp": "2026-01-15T10:00:00Z",
        "event_type": "authentication",
        "category": "iam",
        "severity": "MEDIUM",
        "source.ip": "1.2.3.4",
    }
    res = validate_cse(cse)
    assert res.status == "VALID"


def test_missing_required_field():
    cse = {"timestamp": "2026-01-15T10:00:00Z"}
    res = validate_cse(cse)
    assert res.status == "INVALID"


def test_invalid_ip():
    cse = {
        "timestamp": "2026-01-15T10:00:00Z",
        "event_type": "network",
        "category": "network_activity",
        "severity": "LOW",
        "source.ip": "not-an-ip",
    }
    res = validate_cse(cse)
    assert res.status == "INVALID"


def test_invalid_port():
    cse = {
        "timestamp": "2026-01-15T10:00:00Z",
        "event_type": "network",
        "category": "network_activity",
        "severity": "LOW",
        "source.port": 99999,
    }
    res = validate_cse(cse)
    assert res.status == "INVALID"


def test_unknown_event_type_warning():
    cse = {
        "timestamp": "2026-01-15T10:00:00Z",
        "event_type": "unknown",
        "category": "other",
        "severity": "INFO",
    }
    res = validate_cse(cse)
    assert res.status == "WARNING"