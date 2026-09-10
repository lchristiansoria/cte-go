import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ctg_go.db.base import Base


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("organization_id", "cuit"),
        UniqueConstraint("organization_id", "id"),
        CheckConstraint("length(cuit)=11", name="clients_cuit_len_11"),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
