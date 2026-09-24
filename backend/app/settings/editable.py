"""Allowlist of editable settings keys and their UI metadata."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditableKey:
    key: str
    label: str
    group: str
    type: str          # "string" | "bool" | "int" | "float" | "csv"
    sensitive: bool
    requires_restart: bool
    description: str


# The full allowlist. Keys NOT in this list cannot be read or written
# from the UI, even by an admin. This is a hard security boundary.
EDITABLE_KEYS: list[EditableKey] = [
    # ---------- Enrichment ----------
    EditableKey("VIRUSTOTAL_API_KEY", "VirusTotal API Key", "Enrichment",
                "string", True, False, "VirusTotal API v3 key."),
    EditableKey("VIRUSTOTAL_ENABLED", "Enable VirusTotal", "Enrichment",
                "bool", False, False, "Query VirusTotal for indicator reputation."),
    EditableKey("VIRUSTOTAL_UPLOAD_FILES", "Allow VirusTotal File Uploads", "Enrichment",
                "bool", False, False, "Disabled by default; ULPF never uploads files unless enabled."),
    EditableKey("ABUSEIPDB_API_KEY", "AbuseIPDB API Key", "Enrichment",
                "string", True, False, "AbuseIPDB API v2 key."),
    EditableKey("ABUSEIPDB_ENABLED", "Enable AbuseIPDB", "Enrichment",
                "bool", False, False, "Query AbuseIPDB for IP abuse confidence."),
    EditableKey("OTX_API_KEY", "AlienVault OTX API Key", "Enrichment",
                "string", True, False, "OTX DirectConnect API key."),
    EditableKey("OTX_ENABLED", "Enable AlienVault OTX", "Enrichment",
                "bool", False, False, "Query OTX pulses for indicator context."),
    EditableKey("MAXMIND_ACCOUNT_ID", "MaxMind Account ID", "Enrichment",
                "string", False, False, "MaxMind account ID (for reference)."),
    EditableKey("MAXMIND_LICENSE_KEY", "MaxMind License Key", "Enrichment",
                "string", True, False, "MaxMind license key."),
    EditableKey("MAXMIND_DB_PATH", "MaxMind DB Path", "Enrichment",
                "string", False, False, "Filesystem path to GeoLite2-City.mmdb."),
    EditableKey("GEOIP_ENABLED", "Enable GeoIP", "Enrichment",
                "bool", False, False, "Requires an mmdb file at MAXMIND_DB_PATH."),
    EditableKey("RDAP_ENABLED", "Enable RDAP", "Enrichment",
                "bool", False, False, "Query rdap.org for registration data."),
    EditableKey("DNS_ENABLED", "Enable DNS", "Enrichment",
                "bool", False, False, "Reverse/forward DNS lookups."),
    EditableKey("STIX_TAXII_URL", "STIX/TAXII URL", "Enrichment",
                "string", False, False, "Self-hosted TAXII 2.1 collection URL."),
    EditableKey("STIX_TAXII_USER", "STIX/TAXII User", "Enrichment",
                "string", False, False, "TAXII basic-auth username."),
    EditableKey("STIX_TAXII_PASS", "STIX/TAXII Password", "Enrichment",
                "string", True, False, "TAXII basic-auth password."),
    EditableKey("STIX_TAXII_ENABLED", "Enable STIX/TAXII", "Enrichment",
                "bool", False, False, "Query the configured TAXII collection."),
    EditableKey("ENRICHMENT_HTTP_TIMEOUT_SECONDS", "Enrichment HTTP Timeout (s)", "Enrichment",
                "int", False, False, "Per-provider HTTP timeout."),
    EditableKey("ENRICHMENT_CACHE_TTL_HOURS", "Enrichment Cache TTL (h)", "Enrichment",
                "int", False, False, "How long to cache enrichment responses."),
    EditableKey("ENRICHMENT_CIRCUIT_BREAKER_FAILURES", "Circuit Breaker Threshold", "Enrichment",
                "int", False, False, "Failures before a provider is disabled temporarily."),
    EditableKey("ENRICHMENT_CIRCUIT_BREAKER_RESET_SECONDS", "Circuit Breaker Reset (s)", "Enrichment",
                "int", False, False, "Seconds before re-trying a tripped provider."),

    # ---------- Listeners ----------
    EditableKey("SYSLOG_UDP_ENABLED", "Syslog UDP Listener", "Listeners",
                "bool", False, True, "Bind a UDP port to receive syslog datagrams."),
    EditableKey("SYSLOG_UDP_HOST", "Syslog UDP Host", "Listeners",
                "string", False, True, "Interface to bind (0.0.0.0 for all)."),
    EditableKey("SYSLOG_UDP_PORT", "Syslog UDP Port", "Listeners",
                "int", False, True, "UDP port to bind (default 5140)."),
    EditableKey("LOG_TAIL_ENABLED", "File Tail Ingestor", "Listeners",
                "bool", False, True, "Watch a list of files for new log lines."),
    EditableKey("LOG_TAIL_PATHS", "File Tail Paths", "Listeners",
                "csv", False, True, "Comma-separated absolute paths to tail."),
    EditableKey("LOG_TAIL_POLL_SECONDS", "File Tail Poll Interval (s)", "Listeners",
                "float", False, True, "Seconds between polls."),
    EditableKey("LOG_TAIL_FROM_START", "File Tail From Start", "Listeners",
                "bool", False, True, "Read existing lines on first start; default is to tail from end."),

    # ---------- Rate Limits ----------
    EditableKey("RATE_LIMIT_AUTH", "Auth Rate Limit", "Rate Limits",
                "string", False, False, "e.g. 10/minute."),
    EditableKey("RATE_LIMIT_INGEST", "Ingest Rate Limit", "Rate Limits",
                "string", False, False, "e.g. 600/minute."),
    EditableKey("RATE_LIMIT_SEARCH", "Search Rate Limit", "Rate Limits",
                "string", False, False, "e.g. 120/minute."),
    EditableKey("RATE_LIMIT_ENRICH", "Enrichment Rate Limit", "Rate Limits",
                "string", False, False, "e.g. 60/minute."),
    EditableKey("RATE_LIMIT_REPLAY", "Replay Rate Limit", "Rate Limits",
                "string", False, False, "e.g. 30/minute."),

    # ---------- Retention ----------
    EditableKey("RETENTION_RAW_EVIDENCE_DAYS", "Raw Evidence Retention (days)", "Retention",
                "int", False, False, "Raw evidence lifecycle."),
    EditableKey("RETENTION_EVENTS_DAYS", "Events Retention (days)", "Retention",
                "int", False, False, "Event retention."),
    EditableKey("RETENTION_AUDIT_DAYS", "Audit Retention (days)", "Retention",
                "int", False, False, "Audit log retention."),
    EditableKey("RETENTION_CACHE_DAYS", "Cache Retention (days)", "Retention",
                "int", False, False, "Enrichment cache retention."),

    # ---------- Logging ----------
    EditableKey("LOG_LEVEL", "Log Level", "Logging",
                "string", False, False, "DEBUG | INFO | WARNING | ERROR."),

    # ---------- Network ----------
    EditableKey("CORS_ORIGINS", "CORS Origins", "Network",
                "csv", False, True, "Comma-separated allowed browser origins."),
]

EDITABLE_KEY_MAP: dict[str, EditableKey] = {k.key: k for k in EDITABLE_KEYS}

MASKED_SENTINEL = "••••••••"


def is_editable(key: str) -> bool:
    return key in EDITABLE_KEY_MAP