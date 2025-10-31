from datetime import date, timedelta
from sqlalchemy.orm import Session
from .models import Sow
from .schemas import SowCreate, SowUpdate, SowOut
from . import models
from typing import Optional, List
from .auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from .db import get_db


GESTATION_DAYS = 114  # 3 months + 3 weeks + 3 days


def compute_expected_birth(mating_date: Optional[date]) -> Optional[date]:
    if not mating_date:
        return None
    return mating_date + timedelta(days=GESTATION_DAYS)

def is_overdue_row(s: Sow) -> bool:
    return bool(s.expected_birth and s.expected_birth < date.today())

def apply_business_rules(db: Session, sow: Sow, new_status: str | None):
    """
    - If status becomes 'gave_birth': set last_birth_date=today; clear mating/expected.
    - If status becomes 'nursing': require last_birth_date within 21 days.
    """
    if new_status is None:
        return

    if new_status == "gave_birth":
        sow.last_birth_date = date.today()
        sow.mating_date = None
        sow.expected_birth = None

    if new_status == "nursing":
        if not sow.last_birth_date:
            raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot set 'nursing' before 'gave_birth'.")
        if (date.today() - sow.last_birth_date).days > 21:
            raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nursing allowed only within 3 weeks of giving birth.")

def get_sow_row(db: Session, sow_id: int) -> Optional[Sow]:
    return db.query(Sow).get(sow_id)

def create_sow(db: Session, payload: SowCreate, caretaker_id: int) -> Sow:
    sow = Sow(
        sow_identifier = payload.sow_identifier,
        status         = payload.status,
        mating_date    = payload.mating_date,
        expected_birth = payload.expected_birth
                          if payload.expected_birth is not None
                          else compute_expected_birth(payload.mating_date),
        caretaker_id   = caretaker_id,
    )
    db.add(sow)
    db.commit()
    db.refresh(sow)
    return sow

def update_sow(db: Session, sow: Sow, payload: SowUpdate) -> Sow:
    if payload.sow_identifier is not None:
        sow.sow_identifier = payload.sow_identifier
    if payload.status is not None:
        sow.status = payload.status
    if payload.mating_date is not None:
        sow.mating_date = payload.mating_date

    if payload.expected_birth is not None:
        sow.expected_birth = payload.expected_birth
    elif payload.mating_date is not None:
        sow.expected_birth = compute_expected_birth(payload.mating_date)

    if payload.caretaker_id is not None:
        sow.caretaker_id = payload.caretaker_id

    apply_business_rules(db, sow, payload.status)

    db.add(sow)
    db.commit()
    db.refresh(sow)
    return sow

router = APIRouter(prefix="/api/sows", tags=["sows"])

# ---- Auth dependency: ADMIN or CARETAKER ----
# Replace this with your real auth/role check


# ---- List with filters/search ----
@router.get("", response_model=List[SowOut])
def list_sows(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search by sow_identifier (case-insensitive)"),
    status: Optional[str] = Query(None, regex="^(pregnant|nonpregnant|miscarriage|gave_birth|nursing)$"),
    due_within_days: Optional[int] = Query(None, description="e.g., 7 to see sows due within X days")
):
    query = db.query(Sow)

    if q:
        query = query.filter(Sow.sow_identifier.ilike(f"%{q}%"))

    if status:
        query = query.filter(Sow.status == status)

    if due_within_days is not None and due_within_days >= 0:
        today = date.today()
        window_end = today + timedelta(days=due_within_days)
        query = query.filter(
            Sow.status == "pregnant",
            Sow.expected_birth.isnot(None),
            Sow.expected_birth >= today,
            Sow.expected_birth <= window_end
        )

    rows = query.order_by(Sow.sow_id.asc()).all()

    # attach computed is_overdue
    out = []
    for r in rows:
        out.append(SowOut(
            sow_id=r.sow_id,
            sow_identifier=r.sow_identifier,
            status=r.status,
            mating_date=r.mating_date,
            expected_birth=r.expected_birth,
            last_birth_date=r.last_birth_date,
            caretaker_id=r.caretaker_id,
            is_overdue=is_overdue_row(r)
        ))
    return out

@router.get("/{sow_id}", response_model=SowOut)
def get_sow_ep(sow_id: int, db: Session = Depends(get_db)):
    r = db.query(Sow).get(sow_id)
    if not r:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, detail="Sow not found.")
    return SowOut(
        sow_id=r.sow_id,
        sow_identifier=r.sow_identifier,
        status=r.status,
        mating_date=r.mating_date,
        expected_birth=r.expected_birth,
        last_birth_date=r.last_birth_date,
        caretaker_id=r.caretaker_id,
        is_overdue=is_overdue_row(r)
    )

@router.post("", response_model=SowOut, status_code=http_status.HTTP_201_CREATED)
def create_sow_ep(
    payload: SowCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),  # caretaker = current.user_id
):
    sow = create_sow(db, payload, caretaker_id=current.user_id)
    return SowOut(
        sow_id=sow.sow_id,
        sow_identifier=sow.sow_identifier,
        status=sow.status,
        mating_date=sow.mating_date,
        expected_birth=sow.expected_birth,
        caretaker_id=sow.caretaker_id,
        is_overdue=is_overdue_row(sow),
    )

@router.put("/{sow_id}", response_model=SowOut)
def update_sow_ep(
    sow_id: int,
    payload: SowUpdate,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),  # authenticated only
):
    sow = get_sow_row(db, sow_id)
    if not sow:
        raise HTTPException(status_code=404, detail="Sow not found")

    sow = update_sow(db, sow, payload)
    return SowOut(
        sow_id=sow.sow_id,
        sow_identifier=sow.sow_identifier,
        status=sow.status,
        mating_date=sow.mating_date,
        expected_birth=sow.expected_birth,
        caretaker_id=sow.caretaker_id,
        is_overdue=is_overdue_row(sow),
    )
