"""Canonical Security Event (CSE) vocabulary.

CSE is a practical, OCSF-aligned schema. We do NOT claim full OCSF compliance.
Field names use a dotted-path convention for nested canonical fields, but are
materialized flat on the CanonicalEvent model for query performance.
"""
from __future__ import annotations

# Canonical field paths → metadata
CSE_FIELDS: dict[str, dict] = {
    "timestamp": {"type": "datetime", "required": True, "desc": "Event time (UTC)"},
    "event_type": {"type": "string", "required": True, "desc": "High-level type, e.g. authentication, network, file"},
    "category": {"type": "string", "required": True, "desc": "OCSF-style category"},
    "severity": {"type": "string", "required": True, "desc": "INFO|LOW|MEDIUM|HIGH|CRITICAL"},

    "source.ip": {"type": "ip", "required": False, "desc": "Source IP address"},
    "source.port": {"type": "port", "required": False, "desc": "Source port"},
    "source.hostname": {"type": "string", "required": False, "desc": "Source hostname"},

    "destination.ip": {"type": "ip", "required": False, "desc": "Destination IP address"},
    "destination.port": {"type": "port", "required": False, "desc": "Destination port"},
    "destination.hostname": {"type": "string", "required": False, "desc": "Destination hostname"},

    "user.name": {"type": "string", "required": False, "desc": "Username"},
    "user.email": {"type": "string", "required": False, "desc": "User email"},

    "action": {"type": "string", "required": False, "desc": "Action performed"},
    "protocol": {"type": "string", "required": False, "desc": "Network protocol"},
    "device": {"type": "string", "required": False, "desc": "Device / host producing the event"},
    "vendor": {"type": "string", "required": False, "desc": "Vendor"},
    "product": {"type": "string", "required": False, "desc": "Product"},
    "message": {"type": "string", "required": False, "desc": "Human-readable message"},
    "status": {"type": "string", "required": False, "desc": "Outcome status"},
    "raw_reference": {"type": "string", "required": False, "desc": "Pointer to raw evidence"},

    "extensions.url": {"type": "url", "required": False, "desc": "URL indicator"},
    "extensions.domain": {"type": "string", "required": False, "desc": "Domain indicator"},
    "extensions.file_hash": {"type": "string", "required": False, "desc": "File hash"},
    "extensions.cve": {"type": "string", "required": False, "desc": "CVE identifier"},
    "extensions.ip": {"type": "ip", "required": False, "desc": "Additional IP indicator"},
}

# The flat column name on CanonicalEvent that corresponds to each canonical path
CSE_PATH_TO_COLUMN: dict[str, str] = {
    "timestamp": "timestamp",
    "event_type": "event_type",
    "category": "category",
    "severity": "severity",
    "source.ip": "source_ip",
    "source.port": "source_port",
    "source.hostname": "source_hostname",
    "destination.ip": "destination_ip",
    "destination.port": "destination_port",
    "destination.hostname": "destination_hostname",
    "user.name": "user_name",
    "user.email": "extensions",  # stored under extensions
    "action": "action",
    "protocol": "protocol",
    "device": "device",
    "vendor": "vendor",
    "product": "product",
    "message": "message",
    "status": "status",
    "raw_reference": "raw_reference",
    # extension paths → extensions dict
    "extensions.url": "extensions",
    "extensions.domain": "extensions",
    "extensions.file_hash": "extensions",
    "extensions.cve": "extensions",
    "extensions.ip": "extensions",
}

SEVERITY_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def severity_rank(s: str | None) -> int:
    if not s:
        return 0
    s_up = s.upper()
    return SEVERITY_ORDER.index(s_up) if s_up in SEVERITY_ORDER else 0


# Semantic alias table: vendor field name (lowercased, non-alnum stripped) → canonical path.
# This supplements the parser-specific mappings and is used for unknown formats.
SEMANTIC_ALIASES: dict[str, str] = {
    # source ip
    "src": "source.ip", "srcip": "source.ip", "src_ip": "source.ip",
    "sourceip": "source.ip", "source_ip": "source.ip", "sourceaddress": "source.ip",
    "clientip": "source.ip", "client_ip": "source.ip", "clientaddress": "source.ip",
    "saddr": "source.ip", "sip": "source.ip", "s_ip": "source.ip", "sipaddr": "source.ip",
    "originip": "source.ip", "orig_ip": "source.ip",
    # destination ip
    "dst": "destination.ip", "dstip": "destination.ip", "dst_ip": "destination.ip",
    "destinationip": "destination.ip", "destination_ip": "destination.ip",
    "destinationaddress": "destination.ip", "targetip": "destination.ip",
    "target_ip": "destination.ip", "daddr": "destination.ip", "dip": "destination.ip",
    "d_ip": "destination.ip", "dest_ip": "destination.ip", "destip": "destination.ip",
    # source port
    "srcport": "source.port", "src_port": "source.port", "sourceport": "source.port",
    "sport": "source.port", "source_port": "source.port", "s_port": "source.port",
    "clientport": "source.port",
    # destination port
    "dstport": "destination.port", "dst_port": "destination.port", "destport": "destination.port",
    "dest_port": "destination.port", "dport": "destination.port", "destinationport": "destination.port",
    "targetport": "destination.port", "d_port": "destination.port",
    # user
    "user": "user.name", "username": "user.name", "user_name": "user.name",
    "account": "user.name", "accountname": "user.name", "account_name": "user.name",
    "principal": "user.name", "actor": "user.name", "srcuser": "user.name",
    "src_user": "user.name", "suser": "user.name", "login": "user.name",
    "userid": "user.name", "user_id": "user.name",
    "email": "user.email", "user_email": "user.email", "useremail": "user.email",
    # action
    "action": "action", "act": "action", "operation": "action", "verb": "action",
    "event_action": "action", "eventaction": "action",
    # status
    "status": "status", "result": "status", "outcome": "status", "disposition": "status",
    # severity
    "severity": "severity", "sev": "severity", "level": "severity", "priority": "severity",
    "crit": "severity", "log_level": "severity", "loglevel": "severity",
    # protocol
    "protocol": "protocol", "proto": "protocol", "transport": "protocol",
    # device / host
    "host": "device", "hostname": "device", "host_name": "device",
    "computer": "device", "device": "device", "device_name": "device",
    "devicename": "device", "dvc": "device", "dvchost": "device",
    "shost": "source.hostname", "sourcehost": "source.hostname", "source_hostname": "source.hostname",
    "dhost": "destination.hostname", "destinationhost": "destination.hostname",
    "destination_hostname": "destination.hostname",
    # message
    "message": "message", "msg": "message", "name": "message", "description": "message", "text": "message",
    "body": "message", "event_desc": "message", "event_name": "message",
    # vendor / product
    "vendor": "vendor", "manufacturer": "vendor", "source_vendor": "vendor",
    "product": "product", "app": "product", "application": "product",
    "appname": "product", "app_name": "product",
    # timestamp
    "ts": "timestamp", "timestamp": "timestamp", "time": "timestamp",
    "@timestamp": "timestamp", "event_time": "timestamp", "eventtime": "timestamp",
    "datetime": "timestamp", "occurred_at": "timestamp", "start": "timestamp",
    "end": "timestamp", "rt": "timestamp", "devtime": "timestamp",
    # event type / category
    "event_type": "event_type", "eventtype": "event_type", "type": "event_type",
    "category": "category", "event_category": "category",
    # extension fields
    "url": "extensions.url", "uri": "extensions.url", "request_url": "extensions.url",
    "domain": "extensions.domain", "fqdn": "extensions.domain", "dns_name": "extensions.domain",
    "md5": "extensions.file_hash", "sha1": "extensions.file_hash", "sha256": "extensions.file_hash",
    "hash": "extensions.file_hash", "filehash": "extensions.file_hash",
    "cve": "extensions.cve", "vuln": "extensions.cve", "vuln_id": "extensions.cve",
}


def normalize_alias_key(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "_")


def lookup_alias(name: str) -> str | None:
    key = normalize_alias_key(name)
    if key in SEMANTIC_ALIASES:
        return SEMANTIC_ALIASES[key]
    key2 = key.replace("_", "")
    return SEMANTIC_ALIASES.get(key2)