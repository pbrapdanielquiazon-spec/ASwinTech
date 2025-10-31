from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from .auth import oauth2_scheme, require_roles
from .models import Role
from. import models

from .db import get_db
from .auth import get_current_user  # your existing current-user dependency
from .models import Inquiry, InquiryStatus
from .schemas import InquiryCreate, InquiryRespond, InquiryOut

router = APIRouter(prefix="/inquiries", tags=["Inquiries"])

# Helpers -------------------------------------------------

def ensure_role(user, allowed: tuple[str, ...]):
    if user.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")

# Routes --------------------------------------------------

@router.post("", response_model=InquiryOut, status_code=201,
             dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.CLIENT))])
def create_inquiry(data: InquiryCreate, db: Session = Depends(get_db),
                   user: models.User = Depends(require_roles(Role.CLIENT))):
    obj = models.Inquiry(
        client_id=user.user_id,
        subject=data.subject,
        message=data.message,
        status="unread"
    )
    db.add(obj); db.commit(); db.refresh(obj)

    if not obj.status:
        obj.status = "unread"
        db.add(obj); db.commit(); db.refresh(obj)

    return obj

@router.get("", response_model=list[InquiryOut], dependencies=[Depends(oauth2_scheme)])
def list_inquiries(db: Session = Depends(get_db),
                   user: models.User = Depends(require_roles(Role.ADMIN, Role.SALES, Role.CLIENT))):
    q = db.query(models.Inquiry)
    if user.role == Role.CLIENT.value:
        q = q.filter(models.Inquiry.client_id == user.user_id)
    return q.order_by(models.Inquiry.submitted_at.desc(), models.Inquiry.id.desc()).all()

@router.get("/{inquiry_id}", response_model=InquiryOut)
def get_inquiry(inquiry_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    r = db.get(Inquiry, inquiry_id)
    if not r:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if current_user.role in ("admin", "sales"):
        pass
    elif current_user.role == "client" and r.client_id == current_user.user_id:
        pass
    else:
        raise HTTPException(status_code=403, detail="Not permitted")

    return InquiryOut(
        inquiry_id=r.id,
        client_id=r.client_id,
        subject=r.subject,
        message=r.message,
        status=r.status,
        submitted_at=r.submitted_at,
        responded_by=r.responded_by,
        responded_at=r.responded_at,
    )

@router.patch("/{inquiry_id}/respond", response_model=InquiryOut)
def respond_inquiry(
    inquiry_id: int,
    payload: InquiryRespond,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # ADMIN-only
    role = getattr(current_user.role, "value", getattr(current_user, "role", "")).upper()
    if role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")

    q = db.get(Inquiry, inquiry_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")

    # one response per inquiry
    if q.response:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inquiry already has a response")

    # set response + mark responded
    q.response = payload.response
    q.status = "responded"
    q.responded_by = current_user.user_id
    q.responded_at = datetime.utcnow()

    db.add(q)
    db.commit()
    db.refresh(q)
    return q