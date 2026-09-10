from __future__ import annotations

from sqlalchemy.orm import Session

from ctg_go.modules.audit.models import AuditEvent
from ctg_go.modules.identity.models import User


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        *,
        actor: User,
        entity_type: str,
        entity_id: str,
        action: str,
        details: dict,
    ) -> None:
        self.db.add(
            AuditEvent(
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                details_json=details,
            )
        )
