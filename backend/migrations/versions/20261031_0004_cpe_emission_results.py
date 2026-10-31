"""persist CPE emission requests and responses

Revision ID: 20261031_0004
Revises: 20261017_0003
Create Date: 2026-10-31 00:00:00
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261031_0004"
down_revision: str | None = "20261017_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cpe_operations", sa.Column("request_json", sa.JSON(), nullable=True))
    op.add_column("cpe_operations", sa.Column("response_json", sa.JSON(), nullable=True))
    op.add_column("cpe_operations", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cpe_operations", "error_message")
    op.drop_column("cpe_operations", "response_json")
    op.drop_column("cpe_operations", "request_json")
