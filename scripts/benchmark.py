#!/usr/bin/env python3
"""Real benchmark against a running ULPF backend.

Measures: events/sec, average latency, p95 latency, parser success rate,
normalization success rate, validation status distribution.

NEVER hardcodes benchmark values. All numbers come from real measurements.

Usage:
    python scripts/benchmark.py --base http://localhost:8000 \
        --email admin@ulpf.local --password ChangeMe_Admin123! \
        --count 500
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


CEF_TEMPLATE = (
    "CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|"
    "rt=2026-01-15T10:22:03Z src={src} suser={user} dhost=dc01 "
    "outcome={outcome} reason=bad_password proto=tcp"
)
JSON_TEMPLATE = (
    '{{"@timestamp":"2026-01-15T10:22:03Z","event_type":"authentication",'
    '"user":"{user}","src_ip":"{src}","status":"{outcome}","severity":"LOW"}}'
)


def login(base: str, email: str, password: str) -> str:
    r = httpx.post(f"{base}/api/v1/auth/login",
                   json={"email": email, "password": password}, timeout=10.0)
    r.raise_for_status()
    return r.json()["access_token"]


def make_event(i: int) -> dict:
    src = f"203.0.113.{(i % 250) + 1}"
    user = f"user{i % 50}"
    outcome = "failure" if i % 3 else "success"
    if i % 2 == 0:
        raw = CEF_TEMPLATE.format(src=src, user=user, outcome=outcome)
    else:
        raw = JSON_TEMPLATE.format(src=src, user=user, outcome=outcome)
    return {"raw": raw, "filename": f"bench{i}.log"}


def ingest_one(client: httpx.Client, base: str, token: str, payload: dict) -> dict:
    t0 = time.perf_counter()
    r = client.post(
        f"{base}/api/v1/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    dt = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return {**r.json(), "_latency_ms": dt}


def percentile(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = int(round((p / 100.0) * (len(xs) - 1)))
    return xs[k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--email", default="admin@ulpf.local")
    ap.add_argument("--password", default="ChangeMe_Admin123!")
    ap.add_argument("--count", type=int, default=500)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    print(f"[+] Logging in to {args.base} as {args.email}")
    try:
        token = login(args.base, args.email, args.password)
    except Exception as e:
        print(f"[!] Login failed: {e}", file=sys.stderr)
        return 2

    print(f"[+] Warming up (10 events)…")
    with httpx.Client() as client:
        for i in range(10):
            try:
                ingest_one(client, args.base, token, make_event(i))
            except Exception:
                pass

    print(f"[+] Running {args.count} events at concurrency {args.concurrency}…")
    latencies: list[float] = []
    statuses: dict[str, int] = {}
    formats: dict[str, int] = {}
    errors = 0

    t_start = time.perf_counter()
    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [
                pool.submit(ingest_one, client, args.base, token, make_event(i))
                for i in range(args.count)
            ]
            done = 0
            for fut in as_completed(futures):
                done += 1
                try:
                    res = fut.result()
                    latencies.append(res["_latency_ms"])
                    statuses[res.get("processing_status", "UNKNOWN")] = (
                        statuses.get(res.get("processing_status", "UNKNOWN"), 0) + 1
                    )
                    fmt = res.get("detected_format") or "UNKNOWN"
                    formats[fmt] = formats.get(fmt, 0) + 1
                except Exception:
                    errors += 1
                if done % max(1, args.count // 10) == 0:
                    print(f"    … {done}/{args.count}")
    t_total = time.perf_counter() - t_start

    total_ok = sum(statuses.values())
    success = statuses.get("PROCESSED", 0) + statuses.get("WARNING", 0)
    quarantined = statuses.get("QUARANTINED", 0) + statuses.get("FAILED", 0)

    print()
    print("==================== BENCHMARK RESULTS ====================")
    print(f"Events attempted:          {args.count}")
    print(f"Events ingested OK:        {total_ok}")
    print(f"Errors (transport):        {errors}")
    print(f"Total wall time:           {t_total:.2f} s")
    if t_total > 0:
        print(f"Throughput:                {total_ok / t_total:.1f} events/sec")
    if latencies:
        print(f"Latency avg:               {statistics.mean(latencies):.1f} ms")
        print(f"Latency p50:               {percentile(latencies, 50):.1f} ms")
        print(f"Latency p95:               {percentile(latencies, 95):.1f} ms")
        print(f"Latency p99:               {percentile(latencies, 99):.1f} ms")
        print(f"Latency min/max:           {min(latencies):.1f} / {max(latencies):.1f} ms")
    print()
    print("Processing status distribution:")
    for k, v in sorted(statuses.items()):
        print(f"  {k:<20} {v}")
    print()
    print("Detected format distribution:")
    for k, v in sorted(formats.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v}")
    print()
    if total_ok:
        print(f"Pipeline success rate:     {success / total_ok * 100:.2f}%")
        print(f"Quarantine rate:           {quarantined / total_ok * 100:.2f}%")
    print("===========================================================")
    print()
    print("Note: these are REAL measured values from the running backend.")
    print("Results depend on hardware, database, and network.")
    return 0


if __name__ == "__main__":
    sys.exit(main())