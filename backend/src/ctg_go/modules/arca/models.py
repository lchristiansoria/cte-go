import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ctg_go.db.base import Base


class ArcaCuit(Base):
    """A CUIT the organization manages through an ARCA delegation.

    ARCA's WSCPE exposes no operation to list delegations, so the CUIT is
    registered here and its delegation is verified against ARCA afterwards.
    """

    __tablename__ = "arca_cuits"
    __table_args__ = (
        UniqueConstraint("organization_id", "cuit", "environment"),
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("length(cuit)=11", name="arca_cuits_cuit_len_11"),
        CheckConstraint(
            "environment in ('homologacion','produccion')",
            name="arca_cuits_environment_allowed",
        ),
        CheckConstraint(
            "delegation_status in ('unverified','verified','rejected')",
            name="arca_cuits_delegation_status_allowed",
        ),
        ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    delegation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified"
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_kind: Mapped[str | None] = mapped_column(String(16))
    last_errors_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArcaCuitGrant(Base):
    """Which users of the organization may manage a delegated CUIT."""

    __tablename__ = "arca_cuit_grants"
    __table_args__ = (
        UniqueConstraint("arca_cuit_id", "user_id"),
        ForeignKeyConstraint(
            ["organization_id", "arca_cuit_id"],
            ["arca_cuits.organization_id", "arca_cuits.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    arca_cuit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ArcaCuitDataset(Base):
    """Synchronized ARCA data that belongs to one CUIT."""

    __tablename__ = "arca_cuit_datasets"
    __table_args__ = (
        UniqueConstraint("arca_cuit_id", "dataset", "scope_key"),
        ForeignKeyConstraint(
            ["organization_id", "arca_cuit_id"],
            ["arca_cuits.organization_id", "arca_cuits.id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    arca_cuit_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    dataset: Mapped[str] = mapped_column(String(48), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    payload_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_errors_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class ArcaCatalog(Base):
    """ARCA catalogs that do not depend on a CUIT, shared by environment."""

    __tablename__ = "arca_catalogs"
    __table_args__ = (UniqueConstraint("environment", "dataset", "scope_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset: Mapped[str] = mapped_column(String(48), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    payload_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_errors_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
