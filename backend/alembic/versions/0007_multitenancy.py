"""Add multi-tenancy columns across all core tables.

Revision ID: 0007_multitenancy
Revises: 0006_connector_desired
Create Date: 2026-09-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_multitenancy"
down_revision = "0006_connector_desired"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "events",
    "canonical_events",
    "raw_evidence",
    "connectors",
    "alerts",
    "incidents",
    "quarantine_events",
    "field_mappings",
    "schema_drift",
    "audit_logs",
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    # 1. Update users table with tenant_id and tenant_name
    if "users" in existing_tables:
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "tenant_id" not in user_cols:
            op.add_column(
                "users",
                sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default"),
            )
            op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
        if "tenant_name" not in user_cols:
            op.add_column(
                "users",
                sa.Column("tenant_name", sa.String(128), nullable=False, server_default="Default Workspace"),
            )

    # 2. Add tenant_id to each core entity table
    for tbl in TENANT_TABLES:
        if tbl not in existing_tables:
            continue
        cols = {c["name"] for c in insp.get_columns(tbl)}
        if "tenant_id" not in cols:
            op.add_column(
                tbl,
                sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default"),
            )
            op.create_index(f"ix_{tbl}_tenant_id", tbl, ["tenant_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    for tbl in TENANT_TABLES:
        if tbl in existing_tables:
            cols = {c["name"] for c in insp.get_columns(tbl)}
            if "tenant_id" in cols:
                op.drop_index(f"ix_{tbl}_tenant_id", table_name=tbl)
                op.drop_column(tbl, "tenant_id")

    if "users" in existing_tables:
        user_cols = {c["name"] for c in insp.get_columns("users")}
        if "tenant_name" in user_cols:
            op.drop_column("users", "tenant_name")
        if "tenant_id" in user_cols:
            op.drop_index("ix_users_tenant_id", table_name="users")
            op.drop_column("users", "tenant_id")
