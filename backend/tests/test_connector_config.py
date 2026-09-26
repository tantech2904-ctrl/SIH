"""Tests for connector desired-state endpoints (Gap 3.11.6)."""
from __future__ import annotations

import uuid


def _heartbeat(client, analyst_headers, **overrides) -> dict:
    body = {
        "hostname": "test-host",
        "os": "Linux",
        "version": "1.0.0",
        "adapters": ["linux_file_tail"],
        "available_adapters": ["linux_file_tail", "linux_journald"],
        "events_total": 0,
    }
    body.update(overrides)
    r = client.post("/api/v1/connectors/heartbeat", json=body, headers=analyst_headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_heartbeat_stores_available_and_running(client, analyst_headers):
    hb = _heartbeat(client, analyst_headers)
    cid = hb["connector_id"]

    r = client.get("/api/v1/connectors", headers=analyst_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    row = next((x for x in items if x["connector_id"] == cid), None)
    assert row is not None
    assert row["adapters"] == ["linux_file_tail"]
    assert set(row["available_adapters"]) == {"linux_file_tail", "linux_journald"}
    assert row["desired_adapters"] is None
    assert row["config_poll_interval_s"] == 30


def test_get_config_defaults_to_null(client, analyst_headers):
    hb = _heartbeat(client, analyst_headers)
    r = client.get(
        f"/api/v1/connectors/{hb['connector_id']}/config",
        headers=analyst_headers,
    )
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["desired_adapters"] is None
    assert cfg["poll_interval_s"] == 30


def test_set_config_persists_and_is_returned_on_get(client, analyst_headers):
    hb = _heartbeat(client, analyst_headers)
    cid = hb["connector_id"]

    r = client.post(
        f"/api/v1/connectors/{cid}/config",
        json={"desired_adapters": ["linux_journald"], "poll_interval_s": 15},
        headers=analyst_headers,
    )
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["desired_adapters"] == ["linux_journald"]
    assert cfg["poll_interval_s"] == 15

    r2 = client.get(f"/api/v1/connectors/{cid}/config", headers=analyst_headers)
    assert r2.status_code == 200
    cfg2 = r2.json()
    assert cfg2["desired_adapters"] == ["linux_journald"]
    assert cfg2["poll_interval_s"] == 15


def test_set_config_rejects_unknown_adapters(client, analyst_headers):
    hb = _heartbeat(client, analyst_headers)
    cid = hb["connector_id"]

    r = client.post(
        f"/api/v1/connectors/{cid}/config",
        json={"desired_adapters": ["windows_eventlog"]},
        headers=analyst_headers,
    )
    assert r.status_code == 400
    body = r.json()
    msg = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "windows_eventlog" in msg


def test_set_config_validates_poll_interval(client, analyst_headers):
    hb = _heartbeat(client, analyst_headers)
    cid = hb["connector_id"]

    r = client.post(
        f"/api/v1/connectors/{cid}/config",
        json={"desired_adapters": [], "poll_interval_s": 1},
        headers=analyst_headers,
    )
    assert r.status_code == 400


def test_kill_switch_empty_desired_adapters(client, analyst_headers):
    """An empty desired list is valid and means 'stop everything'."""
    hb = _heartbeat(client, analyst_headers)
    cid = hb["connector_id"]

    r = client.post(
        f"/api/v1/connectors/{cid}/config",
        json={"desired_adapters": []},
        headers=analyst_headers,
    )
    assert r.status_code == 200
    assert r.json()["desired_adapters"] == []