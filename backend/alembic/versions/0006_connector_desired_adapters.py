"""Add connector desired-state columns.

Revision ID: 0006_connector_desired
Revises: 0005_refresh_tokens
Create Date: 2026-09-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_connector_desired"
down_revision = "0005_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "connectors" not in insp.get_table_names():
        # Cannot add columns to a table that doesn't exist. This should
        # never happen in practice (0004 creates it), but we guard anyway.
        return

    existing_cols = {c["name"] for c in insp.get_columns("connectors")}

    if "available_adapters" not in existing_cols:
        op.add_column(
            "connectors",
            sa.Column("available_adapters", sa.JSON(), nullable=False, server_default="[]"),
        )
    if "desired_adapters" not in existing_cols:
        op.add_column(
            "connectors",
            sa.Column("desired_adapters", sa.JSON(), nullable=True),
        )
    if "config_poll_interval_s" not in existing_cols:
        op.add_column(
            "connectors",
            sa.Column("config_poll_interval_s", sa.Integer(), nullable=False, server_default="30"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "connectors" not in insp.get_table_names():
        return

    existing_cols = {c["name"] for c in insp.get_columns("connectors")}
    if "config_poll_interval_s" in existing_cols:
        op.drop_column("connectors", "config_poll_interval_s")
    if "desired_adapters" in existing_cols:
        op.drop_column("connectors", "desired_adapters")
    if "available_adapters" in existing_cols:
        op.drop_column("connectors", "available_adapters")