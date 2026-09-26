from functools import lru_cache
import logging
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.live"), case_sensitive=False, extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_NAME: str = "ULPF"
    APP_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database / Redis
    DATABASE_URL: str = "sqlite:///./ulpf.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET: str = "dev-insecure-secret-change-me-32-chars-min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Object storage
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "ulpf-raw"
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"

    # Limits
    MAX_UPLOAD_BYTES: int = 50 * 1024 * 1024
    MAX_EVENT_BYTES: int = 1 * 1024 * 1024

    # SSE
    SSE_KEEPALIVE_SECONDS: int = 15
    SSE_REPLAY_MAX: int = 200
    EVENT_BUS_CHANNEL: str = "ulpf:events"

    # Syslog UDP ingestion (optional, default off)
    SYSLOG_UDP_ENABLED: bool = False
    SYSLOG_UDP_HOST: str = "0.0.0.0"
    SYSLOG_UDP_PORT: int = 5140

    # File tail ingestion (optional, default off)
    LOG_TAIL_ENABLED: bool = False
    LOG_TAIL_PATHS: str = ""
    LOG_TAIL_POLL_SECONDS: float = 1.0
    LOG_TAIL_FROM_START: bool = False

    # Rate limits
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_INGEST: str = "600/minute"
    RATE_LIMIT_SEARCH: str = "120/minute"
    RATE_LIMIT_ENRICH: str = "60/minute"
    RATE_LIMIT_REPLAY: str = "30/minute"

    # Enrichment
    VIRUSTOTAL_API_KEY: str = ""
    VIRUSTOTAL_ENABLED: bool = False
    VIRUSTOTAL_UPLOAD_FILES: bool = False

    ABUSEIPDB_API_KEY: str = ""
    ABUSEIPDB_ENABLED: bool = False

    OTX_API_KEY: str = ""
    OTX_ENABLED: bool = False

    MAXMIND_ACCOUNT_ID: str = ""
    MAXMIND_LICENSE_KEY: str = ""
    MAXMIND_DB_PATH: str = ""
    GEOIP_ENABLED: bool = False

    RDAP_ENABLED: bool = True
    DNS_ENABLED: bool = True

    STIX_TAXII_URL: str = ""
    STIX_TAXII_USER: str = ""
    STIX_TAXII_PASS: str = ""
    STIX_TAXII_ENABLED: bool = False

    ENRICHMENT_HTTP_TIMEOUT_SECONDS: int = 6
    ENRICHMENT_CACHE_TTL_HOURS: int = 24
    ENRICHMENT_CIRCUIT_BREAKER_FAILURES: int = 5
    ENRICHMENT_CIRCUIT_BREAKER_RESET_SECONDS: int = 60

    # Detection
    RISK_AUTO_QUARANTINE_BELOW_CONFIDENCE: float = 0.55
    CORRELATION_WINDOW_SECONDS: int = 300

    # Retention
    RETENTION_RAW_EVIDENCE_DAYS: int = 90
    RETENTION_EVENTS_DAYS: int = 180
    RETENTION_AUDIT_DAYS: int = 365
    RETENTION_CACHE_DAYS: int = 7

    # Bootstrap
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@ulpf.local"
    BOOTSTRAP_ADMIN_PASSWORD: str = "ChangeMe_Admin123!"
    BOOTSTRAP_ANALYST_EMAIL: str = "analyst@ulpf.local"
    BOOTSTRAP_ANALYST_PASSWORD: str = "ChangeMe_Analyst123!"
    BOOTSTRAP_AUDITOR_EMAIL: str = "auditor@ulpf.local"
    BOOTSTRAP_AUDITOR_PASSWORD: str = "ChangeMe_Auditor123!"

    RESTART_MODE: str = "auto"

    @field_validator("JWT_SECRET")
    @classmethod
    def _check_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def log_tail_paths_list(self) -> List[str]:
        return [p.strip() for p in self.LOG_TAIL_PATHS.split(",") if p.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def reload_settings() -> None:
    """Re-read the active env file and update the cached Settings singleton.

    File resolution order:
      1. ULPF_ENV_LIVE (bind-mounted /app/.env.live in Docker)
      2. ULPF_ENV_FILE (local .env), defaulting to ".env"

    Behavior:
      - If neither file exists, this is a no-op.
      - The whole file is validated BEFORE any value is applied. If any
        field fails validation (e.g. JWT_SECRET < 32 chars), no values are
        applied and the previous singleton state is preserved. This makes
        the reload atomic — partial application is not supported.
      - Does NOT mutate os.environ. Variables set by the container runtime
        (e.g. DATABASE_URL, REDIS_URL in docker-compose's environment: block)
        remain authoritative for those keys, which is correct — those are
        structural and not UI-editable.
    """
    import os
    from pathlib import Path

    env_path: Path | None = None
    live = os.environ.get("ULPF_ENV_LIVE")
    if live:
        p = Path(live)
        if p.exists():
            env_path = p
    if env_path is None:
        p = Path(os.environ.get("ULPF_ENV_FILE", ".env"))
        if p.exists():
            env_path = p

    if env_path is None:
        _log.debug("settings.reload.no_file")
        return

    overrides: dict[str, str] = {}
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                v = v[1:-1]
            overrides[k] = v
    except Exception as e:
        _log.warning("settings.reload.read_failed error=%s", e)
        return

    # Build a candidate dict: current singleton values + file overrides,
    # coerced to the target field types.
    candidate: dict = {k: getattr(settings, k) for k in settings.model_fields}
    for field, raw_value in overrides.items():
        if field not in settings.model_fields:
            continue
        try:
            spec = settings.model_fields[field]
            ann = spec.annotation
            if ann is int or ann == "int":
                value = int(raw_value)
            elif ann is float or ann == "float":
                value = float(raw_value)
            elif ann is bool or ann == "bool":
                value = str(raw_value).strip().lower() in ("true", "1", "yes", "on")
            else:
                value = raw_value
            candidate[field] = value
        except Exception as e:
            _log.warning("settings.reload.coerce_failed field=%s error=%s", field, e)
            # Keep the current value for this field.

    # Validate atomically. If any field fails, apply nothing.
    try:
        Settings(**candidate)
    except Exception as e:
        _log.warning("settings.reload.validation_failed error=%s", e)
        return

    # All good — apply.
    for field, value in candidate.items():
        try:
            setattr(settings, field, value)
        except Exception as e:
            _log.warning("settings.reload.apply_failed field=%s error=%s", field, e)