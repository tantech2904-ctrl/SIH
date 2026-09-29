"""Add connectors table.

Revision ID: 0004_connectors
Revises: 0003_audit_seq
Create Date: 2026-09-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_connectors"
down_revision = "0003_audit_seq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "connectors" in insp.get_table_names():
        # Already created by 0001_initial's create_all() on a prior run.
        return

    op.create_table(
        "connectors",
        sa.Column("connector_id", sa.String(36), primary_key=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("os", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("version", sa.String(32), nullable=False, server_default="0.0.0"),
        sa.Column("adapters", sa.JSON(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events_total", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_connectors_hostname", "connectors", ["hostname"])
    op.create_index("ix_connectors_last_heartbeat", "connectors", ["last_heartbeat"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "connectors" not in insp.get_table_names():
        return
    # Drop indexes only if present (they might not exist if upgrade
    # short-circuited because the table was pre-created by 0001).
    existing_indexes = {i["name"] for i in insp.get_indexes("connectors")}
    if "ix_connectors_last_heartbeat" in existing_indexes:
        op.drop_index("ix_connectors_last_heartbeat", table_name="connectors")
    if "ix_connectors_hostname" in existing_indexes:
        op.drop_index("ix_connectors_hostname", table_name="connectors")
    op.drop_table("connectors")