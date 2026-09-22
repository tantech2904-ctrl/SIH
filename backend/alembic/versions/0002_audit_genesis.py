"""Add is_genesis flag to audit_logs for hash-chain anchoring.

Revision ID: 0002_audit_genesis
Revises: 0001_initial
Create Date: 2026-01-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_audit_genesis"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return index_name in {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    if not _column_exists("audit_logs", "is_genesis"):
        op.add_column(
            "audit_logs",
            sa.Column("is_genesis", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _index_exists("audit_logs", "ix_audit_logs_is_genesis"):
        op.create_index("ix_audit_logs_is_genesis", "audit_logs", ["is_genesis"])


def downgrade() -> None:
    if _index_exists("audit_logs", "ix_audit_logs_is_genesis"):
        op.drop_index("ix_audit_logs_is_genesis", table_name="audit_logs")
    if _column_exists("audit_logs", "is_genesis"):
        op.drop_column("audit_logs", "is_genesis")