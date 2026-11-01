"""add ARCA delegated CUITs, grants and synchronized datasets

Revision ID: 20261101_0005
Revises: 20261031_0004
Create Date: 2026-11-01 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261101_0005"
down_revision: str | None = "20261031_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arca_cuits",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cuit", sa.String(length=11), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("delegation_status", sa.String(length=16), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_kind", sa.String(length=16), nullable=True),
        sa.Column("last_errors_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(cuit)=11", name=op.f("ck_arca_cuits_arca_cuits_cuit_len_11")),
        sa.CheckConstraint(
            "environment in ('homologacion','produccion')",
            name=op.f("ck_arca_cuits_arca_cuits_environment_allowed"),
        ),
        sa.CheckConstraint(
            "delegation_status in ('unverified','verified','rejected')",
            name=op.f("ck_arca_cuits_arca_cuits_delegation_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_arca_cuits_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name=op.f("fk_arca_cuits_organization_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arca_cuits")),
        sa.UniqueConstraint(
            "organization_id", "cuit", "environment",
            name=op.f("uq_arca_cuits_organization_id"),
        ),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_arca_cuits_organization_id_id")),
    )
    op.create_table(
        "arca_cuit_grants",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("arca_cuit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "arca_cuit_id"],
            ["arca_cuits.organization_id", "arca_cuits.id"],
            name=op.f("fk_arca_cuit_grants_organization_id_arca_cuits"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name=op.f("fk_arca_cuit_grants_organization_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arca_cuit_grants")),
        sa.UniqueConstraint("arca_cuit_id", "user_id", name=op.f("uq_arca_cuit_grants_arca_cuit_id")),
    )
    op.create_table(
        "arca_cuit_datasets",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("arca_cuit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("dataset", sa.String(length=48), nullable=False),
        sa.Column("scope_key", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_errors_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "arca_cuit_id"],
            ["arca_cuits.organization_id", "arca_cuits.id"],
            name=op.f("fk_arca_cuit_datasets_organization_id_arca_cuits"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arca_cuit_datasets")),
        sa.UniqueConstraint(
            "arca_cuit_id", "dataset", "scope_key",
            name=op.f("uq_arca_cuit_datasets_arca_cuit_id"),
        ),
    )
    op.create_table(
        "arca_catalogs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("dataset", sa.String(length=48), nullable=False),
        sa.Column("scope_key", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_errors_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_arca_catalogs")),
        sa.UniqueConstraint(
            "environment", "dataset", "scope_key",
            name=op.f("uq_arca_catalogs_environment"),
        ),
    )


def downgrade() -> None:
    op.drop_table("arca_catalogs")
    op.drop_table("arca_cuit_datasets")
    op.drop_table("arca_cuit_grants")
    op.drop_table("arca_cuits")
