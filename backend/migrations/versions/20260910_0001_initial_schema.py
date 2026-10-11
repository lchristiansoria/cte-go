"""initial persistence schema

Revision ID: 20260910_0001
Revises:
Create Date: 2026-09-10 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260910_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("name", name=op.f("uq_organizations_name")),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('admin','operator')", name=op.f("ck_users_role_allowed")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_users_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("organization_id", "email", name=op.f("uq_users_organization_id")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_users_organization_id_1")),
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cuit", sa.String(length=11), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(cuit)=11", name=op.f("ck_clients_cuit_len_11")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_clients_organization_id_organizations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.UniqueConstraint("organization_id", "cuit", name=op.f("uq_clients_organization_id")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_clients_organization_id_1")),
    )

    op.create_table(
        "gestions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_gestions_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "client_id"], ["clients.organization_id", "clients.id"], name=op.f("fk_gestions_organization_id_clients"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "created_by_user_id"], ["users.organization_id", "users.id"], name=op.f("fk_gestions_organization_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gestions")),
        sa.UniqueConstraint("organization_id", "code", name=op.f("uq_gestions_organization_id")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_gestions_organization_id_1")),
    )

    op.create_table(
        "cpe_drafts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("gestion_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('draft','ready','confirmed')", name=op.f("ck_cpe_drafts_status_allowed")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_cpe_drafts_cpe_drafts_version_gte_1")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_cpe_drafts_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "gestion_id"], ["gestions.organization_id", "gestions.id"], name=op.f("fk_cpe_drafts_organization_id_gestions"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "created_by_user_id"], ["users.organization_id", "users.id"], name="fk_cpe_drafts_creator_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "responsible_user_id"], ["users.organization_id", "users.id"], name="fk_cpe_drafts_responsible_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpe_drafts")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_cpe_drafts_organization_id")),
    )

    op.create_table(
        "cpe_operations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cpe_draft_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status in ('pending','in_progress','success','failed','uncertain','cancelled')",
            name=op.f("ck_cpe_operations_status_allowed"),
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_cpe_operations_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "cpe_draft_id"], ["cpe_drafts.organization_id", "cpe_drafts.id"], name=op.f("fk_cpe_operations_organization_id_cpe_drafts"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpe_operations")),
        sa.UniqueConstraint("organization_id", "id", name=op.f("uq_cpe_operations_organization_id")),
    )

    op.create_table(
        "cpe_reassignments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cpe_draft_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("previous_responsible_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("new_responsible_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(reason)) > 0", name=op.f("ck_cpe_reassignments_reason_not_empty")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_cpe_reassignments_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "cpe_draft_id"], ["cpe_drafts.organization_id", "cpe_drafts.id"], name=op.f("fk_cpe_reassignments_organization_id_cpe_drafts"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "actor_user_id"], ["users.organization_id", "users.id"], name="fk_cpe_reassignments_actor_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "previous_responsible_user_id"], ["users.organization_id", "users.id"], name="fk_cpe_reassignments_previous_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "new_responsible_user_id"], ["users.organization_id", "users.id"], name="fk_cpe_reassignments_new_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpe_reassignments")),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name=op.f("fk_audit_events_organization_id_organizations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "actor_user_id"], ["users.organization_id", "users.id"], name=op.f("fk_audit_events_organization_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )

    op.create_index(op.f("ix_cpe_drafts_org_gestion"), "cpe_drafts", ["organization_id", "gestion_id"], unique=False)
    op.create_index(op.f("ix_cpe_operations_org_draft_status"), "cpe_operations", ["organization_id", "cpe_draft_id", "status"], unique=False)
    op.create_index(op.f("ix_cpe_reassignments_org_draft"), "cpe_reassignments", ["organization_id", "cpe_draft_id"], unique=False)
    op.create_index(op.f("ix_audit_events_org_entity"), "audit_events", ["organization_id", "entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_events_org_entity"), table_name="audit_events")
    op.drop_index(op.f("ix_cpe_reassignments_org_draft"), table_name="cpe_reassignments")
    op.drop_index(op.f("ix_cpe_operations_org_draft_status"), table_name="cpe_operations")
    op.drop_index(op.f("ix_cpe_drafts_org_gestion"), table_name="cpe_drafts")
    op.drop_table("audit_events")
    op.drop_table("cpe_reassignments")
    op.drop_table("cpe_operations")
    op.drop_table("cpe_drafts")
    op.drop_table("gestions")
    op.drop_table("clients")
    op.drop_table("users")
    op.drop_table("organizations")
