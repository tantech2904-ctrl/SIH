"""Contract tests for the cross-platform connector.

These pin the exact HTTP shapes that scripts/ulpf-connector/ emits to
/api/v1/ingest, AND that the resulting CSE (canonical) rows contain the
fields the aliases promise. If any of these fail after a vocabulary
change, the connector README's "Known limitations" section needs an
update.
"""
from __future__ import annotations


# --------------------------------------------------------------- Windows Event Log

WINDOWS_EVENT_XML = """<?xml version="1.0"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing"/>
    <EventID>4625</EventID>
    <Level>8</Level>
    <TimeCreated SystemTime="2026-01-15T10:22:03Z"/>
    <Computer>HOST01</Computer>
    <Channel>Security</Channel>
    <EventRecordID>12345</EventRecordID>
  </System>
  <EventData>
    <Data Name="TargetUserName">alice</Data>
    <Data Name="IpAddress">203.0.113.5</Data>
    <Data Name="LogonType">3</Data>
  </EventData>
</Event>"""


def test_contract_windows_eventlog_xml(client, analyst_headers):
    r = client.post("/api/v1/ingest", json={
        "raw": WINDOWS_EVENT_XML,
        "source": "HOST01",
        "source_type": "windows_eventlog",
        "filename": "Security.evtx",
        "content_type": "application/xml",
    }, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["detected_format"] == "EVTX"
    assert data["parser_id"] == "windows_evtx"
    assert data["processing_status"] in ("PROCESSED", "WARNING")
    assert data["sha256"]

    r2 = client.get(f"/api/v1/events/{data['event_id']}", headers=analyst_headers)
    assert r2.status_code == 200
    cse = r2.json()["canonical"]
    assert cse is not None
    assert cse["processing_metadata"]["parser_id"] == "windows_evtx"


# --------------------------------------------------------------- Linux journald

JOURNALD_JSON = (
    '{"__REALTIME_TIMESTAMP":"2026-01-15T10:22:03.123456Z",'
    '"MESSAGE":"Failed password for root from 203.0.113.5 port 51422 ssh2",'
    '"SYSLOG_IDENTIFIER":"sshd",'
    '"PRIORITY":"6",'
    '"severity":"INFO",'
    '"__CURSOR":"s=abcdef;c=12345;i=9999;b=aaaa",'
    '"_HOSTNAME":"host01"}'
)


def test_contract_journald_json(client, analyst_headers):
    r = client.post("/api/v1/ingest", json={
        "raw": JOURNALD_JSON,
        "source": "host01",
        "source_type": "journald",
        "filename": "system.journal",
        "content_type": "application/json",
    }, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["detected_format"] in ("JSON", "JSONL")
    assert data["processing_status"] in ("PROCESSED", "WARNING")
    assert data["sha256"]

    r2 = client.get(f"/api/v1/events/{data['event_id']}", headers=analyst_headers)
    cse = r2.json()["canonical"]
    assert cse is not None
    assert cse["device"] == "host01"
    assert cse["product"] == "sshd"
    assert "Failed password" in (cse["message"] or "")
    assert cse["severity"] == "INFO"


# --------------------------------------------------------------- macOS Unified Log

UNIFIED_LOG_JSON = (
    '{"timestamp":"2026-01-15T10:22:03Z",'
    '"subsystem":"com.apple.securityd",'
    '"category":"auth",'
    '"eventMessage":"User alice authentication failed from 203.0.113.5",'
    '"processImagePath":"/usr/sbin/sshd",'
    '"process":"sshd",'
    '"eventType":"logEvent"}'
)


def test_contract_macos_unified_log_json(client, analyst_headers):
    r = client.post("/api/v1/ingest", json={
        "raw": UNIFIED_LOG_JSON,
        "source": "macbook-01",
        "source_type": "unified_log",
        "filename": "unified.log",
        "content_type": "application/json",
    }, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["detected_format"] in ("JSON", "JSONL")
    assert data["processing_status"] in ("PROCESSED", "WARNING")
    assert data["sha256"]

    r2 = client.get(f"/api/v1/events/{data['event_id']}", headers=analyst_headers)
    cse = r2.json()["canonical"]
    assert cse is not None
    assert cse["message"] == "User alice authentication failed from 203.0.113.5"
    assert cse["product"] == "com.apple.securityd"


# --------------------------------------------------------------- file_tail

FILE_TAIL_LINE = (
    "Jan 15 10:22:03 host01 sshd[1234]: Failed password for admin from "
    "203.0.113.5 port 51422 ssh2"
)


def test_contract_file_tail_rfc3164_line(client, analyst_headers):
    r = client.post("/api/v1/ingest", json={
        "raw": FILE_TAIL_LINE,
        "source": "host01",
        "source_type": "file_tail",
        "filename": "auth.log",
        "content_type": "text/plain",
    }, headers=analyst_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["processing_status"] in ("PROCESSED", "WARNING", "QUARANTINED", "FAILED")
    assert data["sha256"]