"""Create application settings and optional audit history tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )
    op.create_index("idx_audit_records_created_at", "audit_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_records_created_at", table_name="audit_records")
    op.drop_table("audit_records")
    op.drop_table("app_settings")
