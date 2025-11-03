# audit.py
from typing import Mapping, Any, Optional
from sqlalchemy.orm import Session
from .models import AuditEvent, AuditEntity, AuditAction
from fastapi.encoders import jsonable_encoder  # <-- add this

def log_audit(
    db: Session,
    *,
    entity: AuditEntity,
    entity_id: int,
    action: AuditAction,
    user_id: Optional[int],
    details: Optional[Mapping[str, Any]] = None,
) -> None:
    evt = AuditEvent(
        entity_type=entity,
        entity_id=entity_id,
        action=action,
        recorded_by=user_id,
        details=jsonable_encoder(details) if details is not None else None,  # <-- JSON-safe
    )
    db.add(evt)
    # caller commits
