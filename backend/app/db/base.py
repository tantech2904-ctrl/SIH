from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic + metadata sees them
from app.models import (  # noqa: E402,F401
    user, event, evidence, canonical, parser, mapping, drift,
    quarantine, replay, enrichment, indicator, attck, rule,
    alert, incident, audit, processing,
)