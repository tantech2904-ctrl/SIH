#!/usr/bin/env python3
"""Regenerate the samples/ directory. Runs standalone — no app imports needed."""
import json
import os
import random
from datetime import datetime, timedelta, timezone

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")
os.makedirs(OUT, exist_ok=True)


def _ts(offset_s: int = 0) -> str:
    return (datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write(name: str, content: str) -> None:
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(content)
    print(f"  wrote {path}")


def main() -> None:
    # RFC5424
    lines = []
    for i in range(5):
        lines.append(
            f"<34>1 {_ts(i*2)} auth-server sshd {12345+i} ID47 - Failed password for invalid user admin from 203.0.113.5 port {43210+i} ssh2"
        )
    lines.append(
        f"<38>1 {_ts(30)} auth-server sshd 12350 ID47 - Accepted password for admin from 203.0.113.5 port 43220 ssh2"
    )
    write("rfc5424.log", "\n".join(lines) + "\n")

    # CEF
    lines = []
    for i in range(5):
        lines.append(
            f"CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|7|rt={_ts(i*2)} "
            f"src=203.0.113.5 suser=administrator dhost=dc01.example.local outcome=failure reason=bad_password proto=tcp"
        )
    lines.append(
        f"CEF:0|AcmeCorp|AuthApp|1.0|4624|Successful Logon|3|rt={_ts(30)} "
        f"src=203.0.113.5 suser=administrator dhost=dc01.example.local outcome=success proto=tcp"
    )
    write("cef.log", "\n".join(lines) + "\n")

    # LEEF
    write("leef.log",
          f"LEEF:1.0|VendorX|EDR|2.0|MalwareDetected|devTime={_ts(60)}\tsrc=192.0.2.10\tdst=10.0.0.5\t"
          f"fileHash=44d88612fea8a8f36de82e1278abb02f\tseverity=8\tmsg=Suspicious executable quarantined\n"
          f"LEEF:1.0|VendorX|EDR|2.0|NetworkAnomaly|devTime={_ts(120)}\tsrc=10.0.0.5\tdst=203.0.113.99\tdport=4444\tseverity=7\tmsg=Connection to suspicious port\n")

    # JSON
    write("events.json", json.dumps({
        "@timestamp": _ts(300),
        "event_type": "authentication",
        "action": "login",
        "user": "alice",
        "src_ip": "198.51.100.10",
        "status": "failure",
        "vendor": "ExampleIdP",
        "product": "SSO",
        "severity": "MEDIUM",
        "message": "Login failed for alice from 198.51.100.10",
    }, indent=2) + "\n")

    # JSONL
    jl = []
    for i in range(5):
        jl.append(json.dumps({
            "@timestamp": _ts(400 + i*5),
            "event_type": "authentication", "action": "login", "user": "bob",
            "src_ip": "203.0.113.42", "status": "failure",
            "vendor": "ExampleIdP", "severity": "MEDIUM",
        }))
    jl.append(json.dumps({
        "@timestamp": _ts(430), "event_type": "authentication", "action": "login",
        "user": "bob", "src_ip": "203.0.113.42", "status": "success",
        "vendor": "ExampleIdP", "severity": "LOW",
    }))
    write("events.jsonl", "\n".join(jl) + "\n")

    # XML
    write("events.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n<Event>\n'
          f'  <timestamp>{_ts(600)}</timestamp>\n'
          '  <event_type>network</event_type>\n'
          '  <src_ip>203.0.113.77</src_ip>\n'
          '  <dst_ip>10.0.0.20</dst_ip>\n'
          '  <dst_port>22</dst_port>\n'
          '  <protocol>tcp</protocol>\n'
          '  <action>block</action>\n'
          '  <severity>MEDIUM</severity>\n'
          '  <message>Firewall blocked inbound SSH from suspicious source</message>\n'
          '  <vendor>ExampleFirewall</vendor>\n'
          '</Event>\n')

    # CSV
    write("events.csv",
          "timestamp,src_ip,dst_ip,src_port,dst_port,protocol,action,severity,message\n"
          f"{_ts(800)},203.0.113.88,10.0.0.5,51000,22,tcp,allow,INFO,SSH session from external host\n"
          f"{_ts(805)},203.0.113.88,10.0.0.5,51001,23,tcp,block,MEDIUM,Telnet attempt blocked\n"
          f"{_ts(810)},203.0.113.88,10.0.0.5,51002,445,tcp,block,MEDIUM,SMB probe blocked\n")

    # Malformed
    write("malformed.log", "CEF:0|broken|header only\n")

    # Unknown vendor
    write("unknown_vendor.log",
          f"XLOG|{_ts(1000)}|203.0.113.55|user=alice|op=read|obj=/etc/passwd|res=denied|sev=warn|hostname=web01\n")

    # Schema drift
    write("schema_drift.log",
          json.dumps({"@timestamp": _ts(1100), "clientip": "198.51.100.5", "dest_ip": "10.0.0.5",
                      "user_name": "carol", "action": "login", "status": "success",
                      "severity": "LOW", "message": "drift sample 1"}) + "\n" +
          json.dumps({"@timestamp": _ts(1105), "clientip": "198.51.100.6", "dest_ip": "10.0.0.5",
                      "user_name": "dan", "action": "login", "status": "success",
                      "severity": "LOW", "message": "drift sample 2"}) + "\n")

    # Suspicious auth
    lines = []
    for i in range(6):
        lines.append(
            f"CEF:0|AcmeCorp|AuthApp|1.0|4625|Failed Logon|8|rt={_ts(1200+i*2)} "
            f"src=203.0.113.99 suser=root dhost=dc01 outcome=failure reason=bad_password proto=rdp"
        )
    write("suspicious_auth.log", "\n".join(lines) + "\n")

    # Malicious IP
    write("malicious_ip.log",
          f"CEF:0|Firewall|Edge|1.0|deny|Blocked inbound|6|rt={_ts(1400)} "
          f"src=203.0.113.250 dst=10.0.0.10 spt=40404 dpt=22 proto=tcp act=blocked "
          f"outcome=success msg=Blocked connection from known-bad IP\n")

    # Malware hash
    write("malware_hash.log",
          f"LEEF:1.0|VendorX|EDR|2.0|FileDetected|devTime={_ts(1500)}\tsrc=10.0.0.10\t"
          f"dst=10.0.0.20\tfileHash=44d88612fea8a8f36de82e1278abb02f\tseverity=9\t"
          f"msg=EICAR test file detected\n")


if __name__ == "__main__":
    print("Generating samples...")
    main()
    print("Done.")