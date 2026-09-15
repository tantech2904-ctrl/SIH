"""Synthetic telemetry generator — DEFENSIVE ONLY.

This module never launches attacks, never scans, never exploits. It generates
realistic log events that the pipeline can process, so the platform can be
demonstrated end-to-end offline.
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import require_analyst
from app.core.rate_limit import limiter
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.audit_service import record_audit
from app.services.ingest_service import ingest_event

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_rfc5424_failed_login(src_ip: str) -> str:
    return f"<34>1 {_now()} auth-server sshd 12345 ID47 - Failed password for invalid user admin from {src_ip} port 40000 ssh2"


def gen_cef_bruteforce(src_ip: str) -> str:
    return (
        f"CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|"
        f"rt={_now()} src={src_ip} suser=administrator dhost=dc01.example.local "
        f"outcome=failure reason=bad_password"
    )


def gen_leef_malware(src_ip: str, dst_ip: str, sha: str) -> str:
    return (
        f"LEEF:1.0|VendorX|EDR|2.0|MalwareDetected|"
        f"devTime={_now()}\tsrc={src_ip}\tdst={dst_ip}\tfileHash={sha}\tseverity=8\tmsg=Suspicious executable"
    )


def gen_json_auth(src_ip: str, user: str, success: bool) -> str:
    return json.dumps({
        "@timestamp": _now(),
        "event_type": "authentication",
        "action": "login",
        "user": user,
        "src_ip": src_ip,
        "status": "success" if success else "failure",
        "vendor": "ExampleIdP",
        "product": "SSO",
        "severity": "LOW" if success else "MEDIUM",
        "message": f"Login {'succeeded' if success else 'failed'} for {user}",
    })


def gen_csv_netflow(src_ip: str, dst_ip: str, dport: int) -> str:
    header = "timestamp,src_ip,dst_ip,src_port,dst_port,protocol,action,severity"
    row = f"{_now()},{src_ip},{dst_ip},{random.randint(40000,60000)},{dport},tcp,allow,INFO"
    return header + "\n" + row


def gen_unknown_vendor(src_ip: str) -> str:
    # deliberately non-standard
    return f"XLOG|{_now()}|{src_ip}|user=alice|op=read|obj=/etc/passwd|res=denied|sev=warn"


def gen_malformed() -> str:
    return "CEF:0|broken|header only"


def gen_schema_drift(src_ip: str) -> str:
    # Drift: previously 'src_ip', now 'clientip'
    return json.dumps({
        "@timestamp": _now(),
        "clientip": src_ip,
        "dest_ip": "10.0.0.5",
        "user_name": "bob",
        "action": "login",
        "status": "success",
        "severity": "LOW",
        "message": "drift sample",
    })


SCENARIOS = {
    "bruteforce": lambda: gen_cef_bruteforce(f"203.0.113.{random.randint(1,254)}"),
    "portscan": lambda: gen_csv_netflow("198.51.100.10", "10.0.0.5", random.choice([22, 23, 445, 3389, 8080, 9999])),
    "suspicious_auth": lambda: gen_rfc5424_failed_login("203.0.113.66"),
    "malware_hash": lambda: gen_leef_malware("192.0.2.10", "10.0.0.5",
                                             "44d88612fea8a8f36de82e1278abb02f"),  # EICAR (well-known test hash)
    "malicious_ip": lambda: gen_json_auth("203.0.113.99", "root", False),
    "dns_anomaly": lambda: gen_json_auth("10.0.0.10", "svc-account", False),
    "web_attack": lambda: (
        f"CEF:0|WAF|Edge|1.0|SQLi|SQL Injection attempt|8|"
        f"rt={_now()} src=203.0.113.5 dst=10.0.0.20 request=/login?id=1'OR'1'='1 outcome=blocked"
    ),
    "privesc": lambda: (
        f"CEF:0|Linux|auditd|1.0|priv_esc|sudo to root|9|"
        f"rt={_now()} src=10.0.0.10 suser=alice action=sudo outcome=success"
    ),
    "unknown_vendor": lambda: gen_unknown_vendor("192.0.2.55"),
    "malformed": gen_malformed,
    "schema_drift": lambda: gen_schema_drift("192.0.2.77"),
}


@router.post("/generate")
@limiter.limit(settings.RATE_LIMIT_INGEST)
def generate(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Generate synthetic telemetry. Never executes attacks — produces log events only."""
    scenario = body.get("scenario", "bruteforce")
    count = int(body.get("count", 1))
    count = max(1, min(count, 500))

    if scenario == "all":
        scenarios = list(SCENARIOS.keys())
    else:
        if scenario not in SCENARIOS:
            return {"error": f"Unknown scenario: {scenario}", "available": list(SCENARIOS.keys())}
        scenarios = [scenario]

    results = []
    for _ in range(count):
        for s in scenarios:
            raw = SCENARIOS[s]()
            ev = ingest_event(
                db, raw_bytes=raw.encode("utf-8"),
                source=f"testlab:{s}", source_type="synthetic",
                filename=f"{s}.log", content_type="text/plain",
            )
            results.append({
                "scenario": s, "event_id": ev.event_id,
                "status": ev.processing_status,
                "format": ev.detected_format,
                "confidence": ev.detection_confidence,
            })
    record_audit(db, actor=user.email, action="TESTLAB_GENERATE", resource="testlab",
                 new_state={"scenarios": scenarios, "count": len(results)})
    db.commit()
    return {"generated": len(results), "results": results}


@router.get("/scenarios")
def list_scenarios(user: User = Depends(require_analyst)):
    return {"scenarios": list(SCENARIOS.keys())}