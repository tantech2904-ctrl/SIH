"""Minimal MITRE ATT&CK reference map.

Only a subset of commonly-relevant techniques used by ULPF's default rules.
This is a static lookup — we do NOT claim complete ATT&CK coverage.
"""
from __future__ import annotations

ATTACK_TECHNIQUES: dict[str, dict] = {
    "T1110": {"technique_name": "Brute Force", "tactic": "Credential Access"},
    "T1110.001": {"technique_name": "Password Guessing", "tactic": "Credential Access"},
    "T1110.003": {"technique_name": "Password Spraying", "tactic": "Credential Access"},
    "T1078": {"technique_name": "Valid Accounts", "tactic": "Defense Evasion"},
    "T1046": {"technique_name": "Network Service Scanning", "tactic": "Discovery"},
    "T1068": {"technique_name": "Exploitation for Privilege Escalation", "tactic": "Privilege Escalation"},
    "T1071": {"technique_name": "Application Layer Protocol", "tactic": "Command and Control"},
    "T1071.001": {"technique_name": "Web Protocols", "tactic": "Command and Control"},
    "T1071.004": {"technique_name": "DNS", "tactic": "Command and Control"},
    "T1486": {"technique_name": "Data Encrypted for Impact", "tactic": "Impact"},
    "T1059": {"technique_name": "Command and Scripting Interpreter", "tactic": "Execution"},
    "T1055": {"technique_name": "Process Injection", "tactic": "Defense Evasion"},
    "T1190": {"technique_name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
    "T1204": {"technique_name": "User Execution", "tactic": "Execution"},
    "T1566": {"technique_name": "Phishing", "tactic": "Initial Access"},
}


def map_to_attck(technique_id: str) -> dict | None:
    t = ATTACK_TECHNIQUES.get(technique_id)
    if not t:
        return None
    return {"technique_id": technique_id, **t}


def list_all() -> list[dict]:
    return [{"technique_id": k, **v} for k, v in ATTACK_TECHNIQUES.items()]