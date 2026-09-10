import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ctg_go.db.base import Base


class CPEDraftStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    CONFIRMED = "confirmed"


class CPEOperationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    CANCELLED = "cancelled"


class CPEDraft(Base):
    __tablename__ = "cpe_drafts"
    __table_args__ = (
        CheckConstraint("version >= 1", name="cpe_drafts_version_gte_1"),
        CheckConstraint("status in ('draft','ready','confirmed')", name="cpe_drafts_status_allowed"),
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "gestion_id"],
            ["gestions.organization_id", "gestions.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "responsible_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_cpe_drafts_org_gestion", "organization_id", "gestion_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    gestion_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=CPEDraftStatus.DRAFT.value, server_default=CPEDraftStatus.DRAFT.value
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CPEOperation(Base):
    __tablename__ = "cpe_operations"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending','in_progress','success','failed','uncertain','cancelled')",
            name="cpe_operations_status_allowed",
        ),
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "cpe_draft_id"],
            ["cpe_drafts.organization_id", "cpe_drafts.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_cpe_operations_org_draft_status", "organization_id", "cpe_draft_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cpe_draft_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=CPEOperationStatus.PENDING.value, server_default=CPEOperationStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CPEReassignment(Base):
    __tablename__ = "cpe_reassignments"
    __table_args__ = (
        CheckConstraint("length(trim(reason)) > 0", name="cpe_reassignments_reason_not_empty"),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "cpe_draft_id"],
            ["cpe_drafts.organization_id", "cpe_drafts.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "previous_responsible_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "new_responsible_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_cpe_reassignments_org_draft", "organization_id", "cpe_draft_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cpe_draft_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    previous_responsible_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    new_responsible_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
