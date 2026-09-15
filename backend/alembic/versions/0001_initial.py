"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00

This migration creates all ULPF tables. It is idempotent: running
`alembic upgrade head` against an empty DB is safe, and running it twice
against a populated DB is a no-op because alembic tracks revisions.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use metadata create_all — the models are the single source of truth.
    # This avoids hand-maintaining column definitions in two places.
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)


def downgrade() -> None:
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.drop_all(bind=engine)