# routers/admin_users.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from .db import get_db  # your session dependency
from .models import User  # your User ORM model
from .schemas import UserCountOut
from .routes_auth import _require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users/count", response_model=UserCountOut)
def users_count(
    active_only: bool = Query(False, description="Count only active users"),
    db: Session = Depends(get_db),
    _: User = Depends(_require_admin),
):
    q = db.query(User)
    if active_only:
        # adjust field name/value to your schema (e.g., 'ACTIVE', True, etc.)
        q = q.filter(User.status == "active")

    # total
    total = q.with_entities(func.count(User.user_id)).scalar()  # change 'id' to your PK column

    # by role (optional; handy for dashboards)
    rows = (
        q.with_entities(User.role, func.count(User.user_id))
         .group_by(User.role)
         .all()
    )
    # normalize enum/string to upper-case keys
    by_role = {}
    for role_val, cnt in rows:
        key = str(getattr(role_val, "value", role_val)).upper()
        by_role[key] = cnt

    return UserCountOut(total=total or 0, by_role=by_role)
