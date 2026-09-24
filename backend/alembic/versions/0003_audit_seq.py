"""Add monotonic seq column to audit_logs and make it the primary key.

Revision ID: 0003_audit_seq
Revises: 0002_audit_genesis
Create Date: 2026-01-03 00:00:00

The original audit_logs table used audit_id (a UUID) as the primary key.
UUIDs are random, so (timestamp, audit_id) ordering does not reliably
reflect insertion order when timestamps collide. This migration adds an
auto-incrementing `seq` column that becomes the authoritative chain
order and the new primary key.

This is a chain-breaking schema change: rows written before this
migration have integrity_hash values computed without `seq` in the
payload. After this migration, verify_audit_chain() will report those
rows as hash_mismatch. In production this would require a manual
re-hash migration. In dev, wipe the DB and restart.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_audit_seq"
down_revision = "0002_audit_genesis"
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
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _column_exists("audit_logs", "seq"):
        # Add a nullable integer column
        op.add_column("audit_logs", sa.Column("seq", sa.Integer(), nullable=True))

        # Populate in insertion order (approximated by timestamp + audit_id)
        bind.execute(sa.text("""
            WITH ordered AS (
                SELECT audit_id,
                       ROW_NUMBER() OVER (ORDER BY timestamp ASC, audit_id ASC) AS rn
                FROM audit_logs
            )
            UPDATE audit_logs
            SET seq = ordered.rn
            FROM ordered
            WHERE audit_logs.audit_id = ordered.audit_id
        """))

        # Enforce NOT NULL
        op.alter_column("audit_logs", "seq", nullable=False)

        # Create a sequence for future inserts on Postgres
        bind.execute(sa.text(
            "CREATE SEQUENCE IF NOT EXISTS audit_logs_seq_seq OWNED BY audit_logs.seq"
        ))
        # Set the sequence to continue after the max existing seq
        bind.execute(sa.text(
            "SELECT setval('audit_logs_seq_seq', "
            "COALESCE((SELECT MAX(seq) FROM audit_logs), 0) + 1, false)"
        ))
        # Make the column use the sequence as its default
        bind.execute(sa.text(
            "ALTER TABLE audit_logs ALTER COLUMN seq SET DEFAULT nextval('audit_logs_seq_seq')"
        ))

    # Only manipulate the PK if we're migrating an existing DB whose PK is
    # currently audit_id. On a fresh DB, the model's create_all already
    # made `seq` the primary key.
    insp = sa.inspect(bind)
    pk = insp.get_pk_constraint("audit_logs")
    pk_cols = pk.get("constrained_columns") or []
    if pk_cols != ["seq"]:
        try:
            bind.execute(sa.text(
                "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_pkey"
            ))
        except Exception:
            pass
        try:
            bind.execute(sa.text(
                "ALTER TABLE audit_logs ADD PRIMARY KEY (seq)"
            ))
        except Exception:
            pass

    # Ensure audit_id has a unique index (it was the PK before)
    if not _index_exists("audit_logs", "ix_audit_logs_audit_id_unique"):
        try:
            op.create_index(
                "ix_audit_logs_audit_id_unique",
                "audit_logs",
                ["audit_id"],
                unique=True,
            )
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    try:
        bind.execute(sa.text(
            "ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_pkey"
        ))
        bind.execute(sa.text(
            "ALTER TABLE audit_logs ADD PRIMARY KEY (audit_id)"
        ))
    except Exception:
        pass
    try:
        op.drop_index("ix_audit_logs_audit_id_unique", table_name="audit_logs")
    except Exception:
        pass
    try:
        bind.execute(sa.text("DROP SEQUENCE IF EXISTS audit_logs_seq_seq"))
    except Exception:
        pass
    if _column_exists("audit_logs", "seq"):
        op.drop_column("audit_logs", "seq")