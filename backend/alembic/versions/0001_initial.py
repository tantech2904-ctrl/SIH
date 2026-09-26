"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00

This migration brings an empty database up to the "rev 0001" schema by
creating every table that the SQLAlchemy models declare at the time this
migration runs.

IMPORTANT — why this uses an existence guard around create_all():

Originally this migration called `Base.metadata.create_all(bind=engine)`
unconditionally. That created *every* table in the metadata, including
tables that later migrations (0004, 0005, ...) also tried to create with
`op.create_table()`. The result was a permanent `DuplicateTable` crash
loop on every restart.

The guard below creates only the tables that don't already exist. This
makes the migration safe to run against:

  - a completely empty database (creates everything)
  - a database that already has some tables (creates only the missing ones)
  - a database where a previous run partially applied (no-ops cleanly)

The convention going forward: `0001_initial` bootstraps the base schema
from the models; every later migration must guard its `op.create_table()`
/ `op.add_column()` calls with an existence check so it survives being
re-run against a database that 0001 already touched.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db.base import Base
    from app.db.session import engine
    from sqlalchemy import inspect

    existing = set(inspect(engine).get_table_names())
    to_create = [t for t in Base.metadata.sorted_tables if t.name not in existing]
    if to_create:
        Base.metadata.create_all(bind=engine, tables=to_create)


def downgrade() -> None:
    from app.db.base import Base
    from app.db.session import engine
    Base.metadata.drop_all(bind=engine)