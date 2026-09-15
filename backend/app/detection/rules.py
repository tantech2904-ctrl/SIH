"""Rule registry helpers. Actual rules live in the DB and are seeded by init_db."""
from sqlalchemy.orm import Session

from app.models.rule import DetectionRule


def list_enabled(db: Session) -> list[DetectionRule]:
    return db.query(DetectionRule).filter(DetectionRule.enabled.is_(True)).all()