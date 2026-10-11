"""safe evolution indexes for reassignment blocking

Revision ID: 20260910_0002
Revises: 20260910_0001
Create Date: 2026-09-10 00:10:00
"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260910_0002"
down_revision: str | None = "20260910_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cpe_operations_blocking_status
        ON cpe_operations (organization_id, cpe_draft_id)
        WHERE status IN ('pending', 'in_progress', 'uncertain')
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cpe_drafts_responsible_lookup
        ON cpe_drafts (organization_id, responsible_user_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cpe_drafts_responsible_lookup")
    op.execute("DROP INDEX IF EXISTS ix_cpe_operations_blocking_status")
