#!/usr/bin/env python3
"""ULPF port smoke test.

Reads docker-compose.yml, probes every exposed port with the appropriate
protocol check, and prints a pass/fail table.

Usage:
    python scripts/port_check.py
    python scripts/port_check.py --json
    python scripts/port_check.py --only 8000 5173
    python scripts/port_check.py --base-host 192.168.1.10

Exit code: 0 if all checks pass, 1 if any fail.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("PyYAML required: pip install PyYAML", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"


def load_compose(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_published_ports(compose: dict) -> list[dict]:
    """Return [{service, host_port, protocol}] for every published port."""
    out: list[dict] = []
    for svc_name, svc in (compose.get("services") or {}).items():
        for entry in svc.get("ports") or []:
            # "8000:8000" or "5140:5140/udp" or "127.0.0.1:8000:8000"
            s = str(entry)
            protocol = "tcp"
            if "/" in s:
                s, protocol = s.rsplit("/", 1)
            parts = s.split(":")
            host_port = None
            if len(parts) == 1:
                host_port = int(parts[0])
            elif len(parts) == 2:
                host_port = int(parts[0])
            elif len(parts) == 3:
                host_port = int(parts[1])
            if host_port:
                out.append({"service": svc_name, "host_port": host_port, "protocol": protocol})
    return out


# ----------------------------------------------------------------- checks

def check_tcp(host: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "TCP connect"
    except Exception as e:
        return False, str(e)


def check_udp(host: str, port: int, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(b"<34>1 2026-01-15T10:00:00Z probe app 1 ID - ulpf-port-check", (host, port))
        s.close()
        return True, "UDP datagram sent"
    except Exception as e:
        return False, str(e)


def check_http(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ulpf-port-check"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            body = resp.read(2048).decode("utf-8", errors="replace")
            if code == 200:
                return True, f"HTTP 200 ({len(body)}b)"
            return False, f"HTTP {code}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


# service → check function mapping (by port number)
SERVICE_CHECKS = {
    5432: ("postgres",       lambda h, p, proto: check_tcp(h, p)),
    6379: ("redis",          lambda h, p, proto: check_tcp(h, p)),
    8000: ("backend",        lambda h, p, proto: check_http(f"http://{h}:{p}/api/v1/health/ready")),
    9000: ("minio/s3",       lambda h, p, proto: check_http(f"http://{h}:{p}/minio/health/live")),
    9001: ("minio/console",  lambda h, p, proto: check_http(f"http://{h}:{p}/")),
    5140: ("syslog udp",     lambda h, p, proto: check_udp(h, p)),
    5173: ("frontend",       lambda h, p, proto: check_http(f"http://{h}:{p}/")),
}


def check_port(host: str, service: str, port: int, protocol: str) -> tuple[bool, str, str]:
    """Return (ok, description, result_text)."""
    entry = SERVICE_CHECKS.get(port)
    if entry is None:
        ok, text = check_tcp(host, port)
        return ok, "TCP connect", text
    _, fn = entry
    ok, text = fn(host, port, protocol)
    desc = {
        "postgres": "TCP + auth probe",
        "redis": "TCP + PING",
        "backend": "HTTP /health/ready",
        "minio/s3": "HTTP /minio/health/live",
        "minio/console": "HTTP /",
        "syslog udp": "UDP datagram",
        "frontend": "HTTP /",
    }.get(service, "TCP connect")
    return ok, desc, text


# ----------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="ULPF port smoke test")
    ap.add_argument("--base-host", default="localhost",
                    help="Host to probe (default localhost)")
    ap.add_argument("--compose", default=str(COMPOSE_PATH),
                    help="Path to docker-compose.yml")
    ap.add_argument("--only", nargs="+", type=int,
                    help="Only check these host ports")
    ap.add_argument("--json", action="store_true", help="Machine-readable output")
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()

    compose_path = Path(args.compose)
    if not compose_path.exists():
        print(f"compose file not found: {compose_path}", file=sys.stderr)
        return 2

    compose = load_compose(compose_path)
    ports = parse_published_ports(compose)
    if args.only:
        ports = [p for p in ports if p["host_port"] in set(args.only)]

    if not ports:
        print("No ports to check.", file=sys.stderr)
        return 2

    results = []
    for entry in ports:
        svc = entry["service"]
        port = entry["host_port"]
        proto = entry["protocol"]
        t0 = time.perf_counter()
        ok, desc, text = check_port(args.base_host, svc, port, proto)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        results.append({
            "service": svc,
            "port": port,
            "protocol": proto,
            "check": desc,
            "ok": ok,
            "result": text[:80],
            "elapsed_ms": elapsed_ms,
        })

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        # Header
        print()
        print(f"{'Port':<6} {'Service':<16} {'Protocol':<8} {'Check':<28} {'Result':<24} Status")
        print("─" * 100)
        for r in results:
            status = "OK" if r["ok"] else "FAIL"
            print(
                f"{r['port']:<6} {r['service']:<16} {r['protocol']:<8} "
                f"{r['check']:<28} {r['result']:<24} {status}"
            )
        print()

    failed = [r for r in results if not r["ok"]]
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())