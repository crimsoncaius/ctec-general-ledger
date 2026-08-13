import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(
    db: Session,
    *,
    company_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        company_id=company_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        metadata_json=metadata or {},
        correlation_id=correlation_id or str(uuid.uuid4()),
    )
    db.add(event)
    return event
