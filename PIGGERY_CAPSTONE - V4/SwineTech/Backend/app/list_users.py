from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .routes_auth import _require_admin
from .schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get(
    "/admin/users",
    response_model=List[UserOut],
    summary="List users (admin)",
)
def list_users(
    active_only: bool = Query(False, description="Only ACTIVE users"),
    role: Optional[str] = Query(None, description="Filter by role (ADMIN/SALES/PROCUREMENT/CARETAKER/CLIENT)"),
    q: Optional[str] = Query(None, description="Search by username/name/email"),
    db: Session = Depends(get_db),
):
    query = db.query(User)

    if active_only:
        query = query.filter(func.upper(User.status) == "ACTIVE")

    if role:
        query = query.filter(func.upper(User.role) == role.upper())

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                User.username.ilike(like),
                User.name.ilike(like),
                User.email.ilike(like),
            )
        )

    # newest first (adjust if your PK/column differs)
    users = query.order_by(User.user_id.desc()).all()
    return users
