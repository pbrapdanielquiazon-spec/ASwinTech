from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, EmailStr, constr
from sqlalchemy.orm import Session

from .db import get_db              # your SessionLocal dependency
from . import models
from .security import hash_password

from .otp2 import start_otp, verify_otp, verify_email_token



# Import the one that returns the current User from a JWT/access token.
# Adjust the import path to wherever it lives in your project:
try:
    from .auth import get_current_user  # COMMON
except Exception:
    # If your function is in a different module, change this import accordingly.
    raise

auth_router = APIRouter(prefix="/auth", tags=["auth"])

# ----------------- Input models -----------------
class RegisterIn(BaseModel):
    name: str | None = None
    username: constr(strip_whitespace=True, min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=8)
    email_verification_token: str

class AdminCreateUserIn(RegisterIn):
    role: models.Role  # ADMIN will be filtered in code below

# ----------------- Helpers -----------------
def _ensure_unique(db: Session, username: str, email: str):
    if db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

def _require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    role_value = (getattr(user.role, "value", user.role) or "").upper()
    if role_value != models.Role.ADMIN.value:  # "ADMIN"
        raise HTTPException(status_code=403, detail="Admins only")
    return user

# ----------------- Public: Client self-registration -----------------
@auth_router.post("/register-client", status_code=201)
def register_client(data: RegisterIn, db: Session = Depends(get_db)):
    ok, reason = verify_email_token(
        db=db,
        email=data.email,
        purpose="register",
        token=data.email_verification_token,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    _ensure_unique(db, data.username, data.email)

    user = models.User(
        name=data.name,
        username=data.username,
        email=data.email,
        password=hash_password(data.password),          # store HASH
        role=models.Role.CLIENT.value,                   # force CLIENT
        status=models.UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.user_id, "role": user.role, "status": user.status}

# ----------------- Admin: create staff accounts -----------------
ALLOWED_STAFF_ROLES = {
    models.Role.SALES,
    models.Role.PROCUREMENT,
    models.Role.CARETAKER,
    # add models.Role.CLIENT here if you also want admins to add clients
}

@auth_router.post("/admin/users", status_code=201)
def admin_create_user(
    data: AdminCreateUserIn,
    db: Session = Depends(get_db),
    admin: models.User = Depends(_require_admin),
):
    if data.role not in ALLOWED_STAFF_ROLES:
        raise HTTPException(status_code=400, detail="Role not allowed for this endpoint")

    _ensure_unique(db, data.username, data.email)

    user = models.User(
        name=data.name,
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role=data.role.value,
        status=models.UserStatus.ACTIVE.value,
        updated_by=admin.user_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.user_id, "role": user.role, "status": user.status}

# ----------------- (Optional) guarded Admin self-register -----------------
# Useful for creating the very first admin; protect with a code.
import os
ADMIN_SIGNUP_CODE = os.getenv("ADMIN_SIGNUP_CODE")

@auth_router.post("/register-admin", status_code=201)
def register_admin(
    data: RegisterIn,
    code: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    if not ADMIN_SIGNUP_CODE or code != ADMIN_SIGNUP_CODE:
        raise HTTPException(status_code=403, detail="Invalid admin signup code")

    _ensure_unique(db, data.username, data.email)

    user = models.User(
        name=data.name,
        username=data.username,
        email=data.email,
        password=hash_password(data.password),
        role=models.Role.ADMIN.value,
        status=models.UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user_id": user.user_id, "role": user.role, "status": user.status}