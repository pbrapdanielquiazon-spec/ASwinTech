# app/auth.py
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable, Union, Literal
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from .db import get_db
from . import models
from .security import verify_password, hash_password  # we created this in app/security.py



# --- Settings from env ---
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# This must match the login path below
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/auth", tags=["auth"])

# ------------- Token schema -------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ------------- Helpers -------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[models.User]:
    # allow username OR email in the login field
    user = db.query(models.User).filter(models.User.username == username_or_email).first()
    if not user:
        user = db.query(models.User).filter(models.User.email == username_or_email).first()
    if not user:
        return None

    # ✅ only verify password here
    if not verify_password(password, user.password):
        return None

    return user

# ------------- The dependency you import elsewhere -------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exc
        # ✅ sub now holds user_id (as str)
        user_id = int(sub)
    except Exception:
        raise credentials_exc

    user = db.query(models.User).get(user_id)
    if not user:
        raise credentials_exc
    if (user.status or "").upper() != models.UserStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="User inactive")
    return user

# Optional: role guard for routes
def require_roles(*allowed_roles: Union[models.Role, str]) -> Callable[..., models.User]:
    """
    Guard: allow only users whose role is in allowed_roles.
    Works whether user.role and/or allowed_roles are strings or Enum members.
    """
    # Normalize allowed -> uppercase strings
    allowed: set[str] = {
        (r.value if isinstance(r, Enum) else str(r)).upper()
        for r in allowed_roles
    }

    def _dep(user: models.User = Depends(get_current_user)) -> models.User:
        # Normalize user's role -> uppercase string
        user_role = (
            user.role.value if isinstance(user.role, Enum) else str(user.role)
        ).upper()

        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return user

    return _dep

# ------------- Login endpoint -------------
@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        # wrong username/email or wrong password
        raise HTTPException(status_code=400, detail="Incorrect username/email or password")

    # ✅ status check here (case-insensitive); return 403 (not 400)
    if (user.status or "").upper() != models.UserStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="User inactive")

    token = create_access_token({"sub": str(user.user_id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# ------------- Who am I -------------
@router.get("/me")
def me(current: models.User = Depends(get_current_user)):
    return {
        "user_id": current.user_id,
        "username": current.username,
        "email": current.email,
        "role": current.role,
        "status": current.status,
        "name": current.name,
    }

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SALES = "SALES"
    PROCUREMENT = "PROCUREMENT"
    CARETAKER = "CARETAKER"
    CLIENT = "CLIENT"

class UpdateProfileIn(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[models.Role] = None
    status: Optional[Literal["active", "inactive"]] = None

def _user_to_dict(u: models.User) -> dict:
    """Return the same shape as GET /auth/me for consistency."""
    return {
        "user_id": u.user_id,
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "name": u.name,
    }

# ========= Update own profile (ADMIN or CLIENT) =========
@router.put("/me")
def update_me(
    payload: UpdateProfileIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    # Only ADMIN or CLIENT may hit this route
    role_val = (current.role.value if isinstance(current.role, Enum) else str(current.role)).upper()
    if role_val not in {models.Role.ADMIN.value, models.Role.CLIENT.value}:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # email uniqueness (if changed)
    if payload.email and payload.email != current.email:
        exists = db.query(models.User).filter(models.User.email == payload.email).first()
        if exists and exists.user_id != current.user_id:
            raise HTTPException(status_code=400, detail="Email already in use")

    # apply changes
    if payload.name is not None:
        current.name = payload.name
    if payload.email is not None:
        current.email = payload.email
    if payload.password:
        current.password = hash_password(payload.password)

    db.add(current)
    db.commit()
    db.refresh(current)
    return _user_to_dict(current)

@router.put("/users/{user_id}")
def admin_update_user(
    user_id: int,
    payload: UpdateProfileIn,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_roles(models.Role.ADMIN)),
):
    target = db.query(models.User).get(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Normalize roles to uppercase strings
    def _val(r): return (r.value if isinstance(r, Enum) else str(r)).upper()
    target_role = _val(target.role)
    admin_role  = _val(admin.role)

    # Admin may update: SALES, PROCUREMENT, CARETAKER, or their own ADMIN record.
    staff_roles = {
        _val(models.Role.SALES),
        _val(models.Role.PROCUREMENT),
        _val(models.Role.CARETAKER),
    }

    if target_role == _val(models.Role.ADMIN):
        if target.user_id != admin.user_id:
            # not allowed to modify other admins
            raise HTTPException(status_code=403, detail="Cannot modify another admin account")
    elif target_role not in staff_roles:
        # no client edits here (and not unknown roles)
        raise HTTPException(status_code=403, detail="Only staff accounts can be modified by admin")

    # email uniqueness check
    if payload.email and payload.email != target.email:
        exists = db.query(models.User).filter(models.User.email == payload.email).first()
        if exists and exists.user_id != target.user_id:
            raise HTTPException(status_code=400, detail="Email already in use")

    # apply updates (username is immutable)
    if payload.name is not None:
        target.name = payload.name
    if payload.email is not None:
        target.email = payload.email
    if payload.password:
        target.password = hash_password(payload.password)

    # ===================== NEW (minimal) =====================
    # Role change (optional) — only for ADMIN caller (already enforced by dependency)
    if payload.role is not None:
        new_role_u = _val(payload.role)  # normalize for checks

        # You still cannot edit *other* admins. If trying to promote someone to ADMIN, block unless it's yourself.
        if new_role_u == _val(models.Role.ADMIN) and target.user_id != admin.user_id:
            raise HTTPException(status_code=403, detail="Cannot promote another account to ADMIN")

        # Only allow setting to a known role (models.Role typing already guarantees this)
        target.role = payload.role

    # Status change (optional) — accepts only "active"/"inactive" (lowercase)
    if payload.status is not None:
        if payload.status not in ("active", "inactive"):
            raise HTTPException(status_code=422, detail="status must be 'active' or 'inactive'")
        target.status = (
            models.UserStatus.ACTIVE if payload.status == "active" else models.UserStatus.INACTIVE
        )
    # ===================== /NEW =====================

    db.add(target)
    db.commit()
    db.refresh(target)
    return _user_to_dict(target)

