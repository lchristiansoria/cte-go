"""persist gestion conversation messages

Revision ID: 20261017_0003
Revises: 20260910_0002
Create Date: 2026-10-17 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261017_0003"
down_revision: str | None = "20260910_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gestion_messages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("gestion_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_name", sa.String(length=255), nullable=True),
        sa.Column("attachment_media_type", sa.String(length=64), nullable=True),
        sa.Column("suggestions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('user','assistant')", name=op.f("ck_gestion_messages_role_allowed")),
        sa.ForeignKeyConstraint(
            ["organization_id", "gestion_id"],
            ["gestions.organization_id", "gestions.id"],
            name=op.f("fk_gestion_messages_organization_id_gestions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name=op.f("fk_gestion_messages_organization_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gestion_messages")),
    )
    op.create_index(
        op.f("ix_gestion_messages_org_gestion_created"),
        "gestion_messages",
        ["organization_id", "gestion_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gestion_messages_org_gestion_created"), table_name="gestion_messages")
    op.drop_table("gestion_messages")
