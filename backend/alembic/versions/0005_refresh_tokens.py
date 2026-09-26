"""Add refresh_tokens table.

Revision ID: 0005_refresh_tokens
Revises: 0004_connectors
Create Date: 2026-09-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_refresh_tokens"
down_revision = "0004_connectors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "refresh_tokens" in insp.get_table_names():
        # Already created by 0001_initial's create_all() on a prior run.
        return

    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(36), nullable=True),
        sa.Column("source_ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_email", "refresh_tokens", ["user_email"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "refresh_tokens" not in insp.get_table_names():
        return
    existing_indexes = {i["name"] for i in insp.get_indexes("refresh_tokens")}
    if "ix_refresh_tokens_expires_at" in existing_indexes:
        op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    if "ix_refresh_tokens_user_email" in existing_indexes:
        op.drop_index("ix_refresh_tokens_user_email", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")