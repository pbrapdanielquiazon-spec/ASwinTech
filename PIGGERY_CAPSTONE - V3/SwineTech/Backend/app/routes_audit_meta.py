from datetime import datetime
from typing import Optional, TypedDict, Literal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, aliased

from .db import get_db
from .models import AuditEvent, AuditAction, AuditEntity, User

router = APIRouter(prefix="/api", tags=["meta"])

# ---- helpers ----

class MetaOut(TypedDict, total=False):
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str

def _name(u: Optional[User]) -> Optional[str]:
    if not u:
        return None
    # Full name if available, else username, else email, else user_id
    return (getattr(u, "name", None) or
            getattr(u, "full_name", None) or
            getattr(u, "username", None) or
            getattr(u, "email", None) or
            str(getattr(u, "user_id", None)))

def _fetch_meta(db: Session, entity: AuditEntity, entity_id: int) -> MetaOut:
    # Join users twice to resolve names for created_by / updated_by
    u1 = aliased(User)
    u2 = aliased(User)

    q = (
        db.query(AuditEvent)
          .filter(
              AuditEvent.entity_type == entity,
              AuditEvent.entity_id == entity_id,
              AuditEvent.action.in_([AuditAction.CREATE, AuditAction.UPDATE]),
          )
          .order_by(AuditEvent.recorded_at.asc())
          .all()
    )

    if not q:
        # Not an error: simply “unknown”
        return {}

    created_ev = next((e for e in q if e.action == AuditAction.CREATE), None)
    updated_ev = next((e for e in reversed(q) if e.action == AuditAction.UPDATE), None)

    out: MetaOut = {}

    if created_ev:
        creator = db.get(User, created_ev.recorded_by) if created_ev.recorded_by else None
        out["created_at"] = created_ev.recorded_at.isoformat() + "Z"
        out["created_by"] = _name(creator) or "—"

    if updated_ev:
        updator = db.get(User, updated_ev.recorded_by) if updated_ev.recorded_by else None
        out["updated_at"] = updated_ev.recorded_at.isoformat() + "Z"
        out["updated_by"] = _name(updator) or "—"

    return out

# ---- endpoints ----
@router.get("/pigs/{pig_id}/meta")
def pig_meta(pig_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.PIG, pig_id)

@router.get("/litters/{litter_id}/meta")
def litter_meta(litter_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.LITTER, litter_id)

@router.get("/pig-health/{record_id}/meta")
def health_meta(record_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.HEALTH, record_id)

@router.get("/sows/{sow_id}/meta")
def sow_meta(sow_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.SOW, sow_id)

@router.get("/feeding-logs/{log_id}/meta")
def feeding_log_meta(log_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.FEED_LOG, log_id)

@router.get("/supplies/{supply_id}/meta")
def supplies_meta(supply_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.SUPPLY, supply_id)

@router.get("/sales/{sale_id}/meta")
def sale_meta(sale_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.SALE, sale_id)

@router.get("/expenses/{expense_id}/meta")
def expense_meta(expense_id: int, db: Session = Depends(get_db)) -> MetaOut:
    return _fetch_meta(db, AuditEntity.EXPENSE, expense_id)



