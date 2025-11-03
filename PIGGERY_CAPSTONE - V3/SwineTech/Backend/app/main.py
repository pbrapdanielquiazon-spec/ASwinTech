# app/main.py
from typing import List, Optional, Literal
from datetime import date, datetime
from fastapi import FastAPI, Depends, HTTPException, Response, status, Query
from .inquiries import router as inquiries_router
from .reports import router as reports_router
from sqlalchemy.orm import Session
from . import models
import json
from .audit import log_audit
from .db import SessionLocal, engine
from .auth import oauth2_scheme, require_roles, get_current_user    
from .models import Role, AuditAction, AuditEntity
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Table, func, select, text, insert
from . import admin_users, list_users
from .schemas import (PigIn, PigOut, PigUpdate, 
                      LitterIn, LitterOut, LitterUpdate, 
                      FeedingLogIn, FeedingLogOut, FeedingLogUpdate, 
                      ExpenseIn, ExpenseOut, ExpenseUpdate,
                      SupplyIn, SupplyOut, SupplyUpdate, SupplyAdjustQty,   
                      SaleIn, SaleOut, SaleUpdate,
                      PigHealthIn, PigHealthOut, PigHealthUpdate,
                      BookingIn, BookingOut, BookingUpdate, BookingDecisionIn,
                      ReceiptIn, ReceiptOut, ReceiptUpdate,
                      FeedbackIn, FeedbackOut,
                      AvailablePigIn, AvailablePigUpdate, AvailablePigOut, AvailablePigPublicOut)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .auth import router as auth_core_router
from .routes_auth import auth_router
from .sows import router as sows_router
from .otp_routes import router as otp_router
from .routes_audit_meta import router as meta_router


if "litters" not in models.Base.metadata.tables:
    Table("litters", models.Base.metadata, autoload_with=engine)

api = FastAPI(
    title="Piggery API",
    version="0.2.2",
    docs_url="/docs",            # Swagger -> /api/docs
    openapi_url="/openapi.json", # OpenAPI -> /api/openapi.json
)

api.include_router(reports_router)
api.include_router(inquiries_router)
api.include_router(auth_core_router)
api.include_router(auth_router)
api.include_router(admin_users.router, prefix="/api")
api.include_router(auth_router)
api.include_router(list_users.router)
api.include_router(sows_router)
api.include_router(otp_router)
api.include_router(meta_router)


api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],   
)

site = FastAPI()

site.mount("/api", api)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "Frontend"

site.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@site.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")

@site.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    p = FRONTEND_DIR / path
    return FileResponse(p) if p.is_file() else FileResponse(FRONTEND_DIR / "index.html")

app = site


# Create tables
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





# ---- PIGS CRUD ----

@api.get("/pigs", response_model=List[PigOut])
def list_pigs(db: Session = Depends(get_db)):
    return db.query(models.Pig).all()


@api.post("/pigs", response_model=PigOut, status_code=201,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.CARETAKER))])
def create_pig(pig: PigIn, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):  # ← ADD THIS PARAM
    obj = models.Pig(**pig.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)

    # === ADD: audit
    log_audit(
        db,
        entity=AuditEntity.PIG,
        entity_id=obj.id,
        action=AuditAction.CREATE,
        user_id=current_user.user_id,
        details={"payload": pig.model_dump(mode="json")}
    )
    db.commit()  # commit the audit row

    return obj



def _pig_or_404(db: Session, pig_id: int) -> models.Pig:
    obj = db.get(models.Pig, pig_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pig not found")
    return obj


@api.get("/pigs/{pig_id}", response_model=PigOut)
def get_pig(pig_id: int, db: Session = Depends(get_db)):
    return _pig_or_404(db, pig_id)


@api.put("/pigs/{pig_id}", response_model=PigOut)
def update_pig(pig_id: int, data: PigUpdate, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user)):  # ← ADD THIS PARAM
    pig = _pig_or_404(db, pig_id)

    payload = data.model_dump(exclude_unset=True)  # ← keep a copy for details
    for field, value in payload.items():
        setattr(pig, field, value)

    db.add(pig); db.commit(); db.refresh(pig)

    # === ADD: audit
    log_audit(
        db,
        entity=AuditEntity.PIG,
        entity_id=pig.id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details={"changes": payload}
    )
    db.commit()

    return pig



@api.delete("/pigs/{pig_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_pig(pig_id: int, db: Session = Depends(get_db)):
    pig = _pig_or_404(db, pig_id)
    db.delete(pig); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- LITTERS CRUD ----

def _litter_or_404(db: Session, litter_id: int) -> models.Litter:
    obj = db.get(models.Litter, litter_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Litter not found")
    return obj

@api.get("/litters", response_model=List[LitterOut])
def list_litters(db: Session = Depends(get_db)):
    return db.query(models.Litter).all()

# create litter
# create litter
@api.post("/litters", response_model=LitterOut, status_code=201,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.CARETAKER))])
def create_litter(litter: LitterIn, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    obj = models.Litter(**litter.model_dump())
    obj.caretaker_id = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)

    # === ADD: audit
    log_audit(
        db,
        entity=AuditEntity.LITTER,
        entity_id=obj.litter_id,
        action=AuditAction.CREATE,
        user_id=current_user.user_id,
        details={"payload": litter.model_dump(mode="json")}
    )
    db.commit()

    return obj


# get one litter
@api.get("/litters/{litter_id}", response_model=LitterOut)
def get_litter(litter_id: int, db: Session = Depends(get_db)):
    return _litter_or_404(db, litter_id)

# update litter
@api.put("/litters/{litter_id}", response_model=LitterOut)
def update_litter(litter_id: int, data: LitterUpdate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):  # ← ADD
    litter = _litter_or_404(db, litter_id)

    payload = data.model_dump(exclude_unset=True)  # ← keep for details
    for field, value in payload.items():
        setattr(litter, field, value)

    db.add(litter); db.commit(); db.refresh(litter)

    # === ADD: audit
    log_audit(
        db,
        entity=AuditEntity.LITTER,
        entity_id=litter.litter_id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details={"changes": payload}
    )
    db.commit()

    return litter


# delete litter
@api.delete("/litters/{litter_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_litter(litter_id: int, db: Session = Depends(get_db)):
    litter = _litter_or_404(db, litter_id)
    db.delete(litter); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---- FEEDING LOGS CRUD ----

def _feedinglog_or_404(db: Session, log_id: int) -> models.FeedingLog:
    obj = db.get(models.FeedingLog, log_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Feeding log not found")
    return obj

@api.get("/feeding-logs", response_model=List[FeedingLogOut])
def list_feeding_logs(db: Session = Depends(get_db)):
    return db.query(models.FeedingLog).order_by(models.FeedingLog.feeding_time.desc()).all()

@api.post("/feeding-logs", response_model=FeedingLogOut, status_code=201,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.CARETAKER))])
def create_feeding_log(data: FeedingLogIn, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user),
):

    # validate litter exists
    if db.get(models.Litter, data.litter_id) is None:
        raise HTTPException(status_code=400, detail="litter_id does not exist")

    obj = models.FeedingLog(**data.model_dump())
    
    obj.caretaker_id = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)
    log_id = (
        getattr(obj, "feeding_log_id", None)
        or getattr(obj, "id", None)
        or getattr(obj, "log_id", None)
    )
    if log_id is None:
        raise HTTPException(status_code=500, detail="Cannot determine feeding log primary key")

    log_audit(
        db,
        entity=AuditEntity.FEED_LOG,
        entity_id=log_id,
        action=AuditAction.CREATE,
        user_id=getattr(current_user, "user_id", None),
        details={"payload": data.model_dump(exclude_none=True, mode="json")},
    )
    db.commit()

    return obj

@api.get("/feeding-logs/{log_id}", response_model=FeedingLogOut)
def get_feeding_log(log_id: int, db: Session = Depends(get_db)):
    return _feedinglog_or_404(db, log_id)

@api.put("/feeding-logs/{log_id}", response_model=FeedingLogOut)
def update_feeding_log(
    log_id: int,
    data: FeedingLogUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = _feedinglog_or_404(db, log_id)

    if data.litter_id is not None and data.litter_id != obj.litter_id:
        if db.get(models.Litter, data.litter_id) is None:
            raise HTTPException(status_code=400, detail="litter_id does not exist")

    payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        setattr(obj, field, value)

    # keep caretaker automatic from token
    obj.caretaker_id = current_user.user_id

    db.add(obj); db.commit(); db.refresh(obj)

    # ---- AUDIT (UPDATE)
    real_id = (
        getattr(obj, "feeding_log_id", None)
        or getattr(obj, "id", None)
        or getattr(obj, "log_id", None)
    )
    log_audit(
        db,
        entity=AuditEntity.FEED_LOG,
        entity_id=real_id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details={"changes": payload},
    )
    db.commit()

    return obj



@api.delete("/feeding-logs/{log_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_feeding_log(log_id: int, db: Session = Depends(get_db)):
    obj = _feedinglog_or_404(db, log_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# list logs for a specific litter
@api.get("/litters/{litter_id}/feeding-logs", response_model=List[FeedingLogOut])
def feeding_logs_for_litter(litter_id: int, db: Session = Depends(get_db)):

    # optional: 404 if litter missing
    if db.get(models.Litter, litter_id) is None:
        raise HTTPException(status_code=404, detail="Litter not found")
    return db.query(models.FeedingLog).filter(models.FeedingLog.litter_id == litter_id).order_by(
        models.FeedingLog.feeding_time.desc()
    ).all()

# ---- EXPENSES CRUD ----

def _expense_or_404(db: Session, exp_id: int) -> models.Expense:
    obj = db.get(models.Expense, exp_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Expense not found")
    return obj

@api.get("/expenses", response_model=List[ExpenseOut])
def list_expenses(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    category: str | None = None,
):
    q = db.query(models.Expense)
    if start:
        q = q.filter(models.Expense.date_spent >= start)
    if end:
        q = q.filter(models.Expense.date_spent <= end)
    if category:
        q = q.filter(models.Expense.category == category)
    return q.order_by(models.Expense.date_spent.desc(), models.Expense.id.desc()).all()

@api.post("/expenses", response_model=ExpenseOut, status_code=201,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.PROCUREMENT))])
def create_expense(data: ExpenseIn, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user),):
    # validate recorded_by exists if provided
    # if data.recorded_by is not None and db.get(models.User, data.recorded_by) is None:
    # raise HTTPException(status_code=400, detail="recorded_by user_id does not exist")
    obj = models.Expense(**data.model_dump())
    obj.recorded_by = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)

    # create_expense – after db.refresh(obj) and before return:
    log_audit(
        db,
        entity=AuditEntity.EXPENSE,
        entity_id=obj.id,
        action=AuditAction.CREATE,
        user_id=current_user.user_id,
        details={"amount": float(obj.amount or 0), "category": obj.category}
    )
    db.commit()
    return obj

@api.get("/expenses/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    return _expense_or_404(db, expense_id)

@api.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)
):
    obj = _expense_or_404(db, expense_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.recorded_by = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)

    # update_expense – right before return obj:
    log_audit(
        db,
        entity=AuditEntity.EXPENSE,
        entity_id=obj.id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details=data.model_dump(exclude_unset=True)
    )
    db.commit()
    return obj

@api.delete("/expenses/{expense_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    obj = _expense_or_404(db, expense_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

    
# ---- SUPPLIES CRUD ----

def _supply_or_404(db: Session, supply_id: int) -> models.Supply:
    obj = db.get(models.Supply, supply_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supply not found")
    return obj

@api.get("/supplies", response_model=List[SupplyOut])
def list_supplies(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search in item_name"),
    category: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(models.Supply)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Supply.item_name.ilike(like))
    if category:
        query = query.filter(models.Supply.category == category)
    return query.order_by(models.Supply.item_name.asc()).offset(skip).limit(limit).all()

@api.post("/supplies", response_model=SupplyOut, status_code=201,  
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.PROCUREMENT))])
def create_supply(data: SupplyIn, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user),
):
    obj = models.Supply(**data.model_dump())
    obj.updated_by = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)
    log_audit(
        db,
        entity=AuditEntity.SUPPLY,
        entity_id=obj.id,
        action=AuditAction.CREATE,
        user_id=current_user.user_id,
        details={"data": data.model_dump()}
    )
    db.commit()
    return obj

@api.get("/supplies/{supply_id}", response_model=SupplyOut)
def get_supply(supply_id: int, db: Session = Depends(get_db)):
    return _supply_or_404(db, supply_id)

@api.put("/supplies/{supply_id}", response_model=SupplyOut,
         dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.PROCUREMENT))])
def update_supply(supply_id: int, data: SupplyUpdate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user),
):
    obj = _supply_or_404(db, supply_id)

    # if quantity is provided directly, enforce non-negative
    payload = data.model_dump(exclude_unset=True)
    if "quantity" in payload and payload["quantity"] is not None and payload["quantity"] < 0:
        raise HTTPException(status_code=400, detail="quantity cannot be negative")
    
    before = {"item_name": obj.item_name, "category": obj.category, "quantity": obj.quantity, "unit": obj.unit}
    for field, value in payload.items():
        setattr(obj, field, value)

    obj.updated_by = current_user.user_id 
    db.add(obj); db.commit(); db.refresh(obj)
    after = {"item_name": obj.item_name, "category": obj.category, "quantity": obj.quantity, "unit": obj.unit}
    log_audit(
        db,
        entity=AuditEntity.SUPPLY,
        entity_id=obj.id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details={"before": before, "after": after}
    )
    db.commit()
    return obj

@api.patch("/supplies/{supply_id}/adjust-qty", response_model=SupplyOut)
def adjust_supply_quantity(supply_id: int, data: SupplyAdjustQty, db: Session = Depends(get_db),
                           current_user: models.User = Depends(get_current_user),
):
    obj = _supply_or_404(db, supply_id)
    before_qty = obj.quantity or 0
    new_qty = (obj.quantity or 0) + data.quantity
    if new_qty < 0:
        raise HTTPException(status_code=409, detail="Adjustment would make quantity negative")
    obj.quantity = new_qty

    obj.updated_by = current_user.user_id  
    db.add(obj); db.commit(); db.refresh(obj)

    log_audit(
        db,
        entity=AuditEntity.SUPPLY,
        entity_id=obj.id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details={"qty_before": before_qty, "delta": data.quantity, "qty_after": obj.quantity}
    )
    db.commit()
    return obj

@api.delete("/supplies/{supply_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_supply(supply_id: int, db: Session = Depends(get_db)):
    obj = _supply_or_404(db, supply_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---- SALES CRUD ----

def _sale_or_404(db: Session, sale_id: int) -> models.Sale:
    obj = db.get(models.Sale, sale_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Sale not found")
    return obj

@api.get("/sales", response_model=List[SaleOut])
def list_sales(
    db: Session = Depends(get_db),
    start: date | None = None,
    end: date | None = None,
    client_id: int | None = None,
):
    q = db.query(models.Sale)
    if start: q = q.filter(models.Sale.payment_date >= start)
    if end:   q = q.filter(models.Sale.payment_date <= end)
    if client_id: q = q.filter(models.Sale.client_id == client_id)
    return q.order_by(models.Sale.payment_date.desc(), models.Sale.id.desc()).all()

@api.post(
    "/sales",
    response_model=SaleOut,
    status_code=201,
    dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.SALES))],
)
def create_sale(
    data: SaleIn,
    db: Session = Depends(get_db),
    me: models.User = Depends(get_current_user),
):
    # 1) Validate booking exists
    booking = db.get(models.Booking, data.booking_id) if data.booking_id else None
    if not booking:
        raise HTTPException(status_code=400, detail="booking_id does not exist")

    # Optional: only allow approved bookings to be sold
    if str(getattr(booking, "status", "")).lower() != "approved":
        raise HTTPException(status_code=409, detail="Booking must be approved before sale")

    # Optional: ensure each booking can only be sold once
    if db.query(models.Sale).filter(models.Sale.booking_id == data.booking_id).first():
        raise HTTPException(status_code=409, detail="Sale already exists for this booking")

    # 2) Get pigs attached to this booking (via booking_pigs junction)
    pigs_ids = db.execute(
        select(models.BookingPig.pigs_id).where(models.BookingPig.booking_id == data.booking_id)
    ).scalars().all()

    if not pigs_ids:
        raise HTTPException(status_code=400, detail="No pigs linked to booking")

    # 3) Check their listings and ensure none are already sold
    listings = (
        db.query(models.AvailablePig)
          .filter(models.AvailablePig.pigs_id.in_(pigs_ids))
          .all()
    )
    if not listings or len(listings) != len(pigs_ids):
        raise HTTPException(status_code=400, detail="Some pigs do not have an available listing")

    already_sold = [l.pigs_id for l in listings if str(l.status).lower() == "sold"]
    if already_sold:
        raise HTTPException(status_code=409, detail=f"Pigs already sold: {already_sold}")

    # 4) Build sale payload (auto-fill client_id + recorded_by)
    payload = data.model_dump()
    payload["client_id"] = booking.client_id
    payload["recorded_by"] = me.user_id

    # 5) Atomic write: create sale + flip listings to 'sold'
    try:
        # Create sale
        sale = models.Sale(**payload)
        db.add(sale)

        # Flip listings to SOLD (only if available/reserved)
        (
            db.query(models.AvailablePig)
              .filter(
                  models.AvailablePig.pigs_id.in_(pigs_ids),
                  models.AvailablePig.status.in_(["available", "reserved"]),
              )
              .update({"status": "sold"}, synchronize_session=False)
        )

        # Optional: mark booking completed
        # booking.status = "completed"
        # db.add(booking)

        db.commit()
        db.refresh(sale)

        log_audit(
            db,
            entity=AuditEntity.SALE,
            entity_id=sale.id,
            action=AuditAction.CREATE,
            user_id=me.user_id,
            details={"booking_id": sale.booking_id, "total": float(sale.total_amount or 0)}
        )
        db.commit()


        return sale

    except Exception:
        db.rollback()   
        raise

@api.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    return _sale_or_404(db, sale_id)

@api.put("/sales/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: int,
    data: SaleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    obj = _sale_or_404(db, sale_id)

    payload = data.model_dump(exclude_unset=True)

    # Never allow client_id to be set by the caller
    payload.pop("client_id", None)

    # If booking_id is being changed (or provided), validate and sync client_id from it
    if "booking_id" in payload and payload["booking_id"] is not None:
        booking = db.get(models.Booking, payload["booking_id"])
        if not booking:
            raise HTTPException(status_code=400, detail="booking_id does not exist")
        payload["client_id"] = booking.client_id
    # else: booking_id unchanged → client_id stays as is (no manual edits allowed)

    # Apply updates
    for field, value in payload.items():
        setattr(obj, field, value)

    # Audit: who performed the change
    obj.recorded_by = current_user.user_id

    db.add(obj); db.commit(); db.refresh(obj)

    # inside update_sale, right before return obj:
    log_audit(
        db,
        entity=AuditEntity.SALE,
        entity_id=obj.id,
        action=AuditAction.UPDATE,
        user_id=current_user.user_id,
        details=payload
    )
    db.commit()
    return obj


    return obj

@api.delete("/sales/{sale_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    obj = _sale_or_404(db, sale_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---- PIG HEALTH RECORDS CRUD ----

def _health_or_404(db: Session, record_id: int) -> models.PigHealthRecord:
    obj = db.get(models.PigHealthRecord, record_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Health record not found")
    return obj

# ---------- list (secured: any authenticated user can read; adjust if you want it public) ----------
@api.get("/pig-health", response_model=List[PigHealthOut], dependencies=[Depends(oauth2_scheme)])
def list_pig_health(
    db: Session = Depends(get_db),
    pig_id: int | None = None,
    died: bool | None = None,
    start: date | None = None,
    end: date | None = None,
):
    q = db.query(models.PigHealthRecord)
    if pig_id is not None:
        q = q.filter(models.PigHealthRecord.pig_id == pig_id)
    if died is not None:
        q = q.filter(models.PigHealthRecord.mortality == died)
    if start:
        q = q.filter(models.PigHealthRecord.recorded_at >= datetime.combine(start, datetime.min.time()))
    if end:
        q = q.filter(models.PigHealthRecord.recorded_at <= datetime.combine(end, datetime.max.time()))
    # use your real PK name (likely health_record_id)
    return q.order_by(
        models.PigHealthRecord.recorded_at.desc(),
        models.PigHealthRecord.health_record_id.desc()
    ).all()

# ---------- create (token + role) ----------
@api.post(
    "/pig-health",
    response_model=PigHealthOut,
    status_code=201,
    dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.CARETAKER))]
)
def create_pig_health(data: PigHealthIn, db: Session = Depends(get_db),
                      current_user: models.User = Depends(get_current_user),):
    # FK sanity checks (prevent 500 from FK violation)
    if db.execute(text("SELECT 1 FROM pigs WHERE pigs_id = :pid"), {"pid": data.pig_id}).first() is None:
        raise HTTPException(status_code=400, detail="pig_id does not exist")

    payload = data.model_dump(exclude_none=True)
    # avoid pushing recorded_at=None into NOT NULL column; let server_default fill it
    if payload.get("recorded_at") is None:
        payload.pop("recorded_at", None)

    obj = models.PigHealthRecord(**payload)
           
    obj.caretaker_id = current_user.user_id
    db.add(obj); db.commit(); db.refresh(obj)

        # === ADD: audit (CREATE)
    log_audit(
        db,
        entity=AuditEntity.HEALTH,
        entity_id=obj.health_record_id,
        action=AuditAction.CREATE,
        user_id=current_user.user_id,
        details={"payload": data.model_dump(exclude_none=True, mode="json")}
    )
    # === ADD: audit (RECORD)
    log_audit(
        db,
        entity=AuditEntity.HEALTH,
        entity_id=obj.health_record_id,
        action=AuditAction.RECORD,
        user_id=current_user.user_id,
        details={"treatment_supply_id": getattr(obj, "treatment_supply_id", None)}
    )
    db.commit()

    return obj

# ---------- read one (token required) ----------
@api.get("/pig-health/{record_id}", response_model=PigHealthOut, dependencies=[Depends(oauth2_scheme)])
def get_pig_health(record_id: int, db: Session = Depends(get_db)):
    return _health_or_404(db, record_id)

# ---------- update (token + role) ----------
@api.put(
    "/pig-health/{record_id}",
    response_model=PigHealthOut,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CARETAKER))],
)
def update_pig_health(
    record_id: int,
    data: PigHealthUpdate,                         # caretaker_id may exist but is optional
    db: Session = Depends(get_db),
    me: models.User = Depends(get_current_user),   # ← from JWT
):
    obj = _health_or_404(db, record_id)
    payload = data.model_dump(exclude_unset=True)

    # If client didn’t send caretaker_id (or sent null), use the logged-in user
    if "caretaker_id" not in payload or payload["caretaker_id"] is None:
        payload["caretaker_id"] = me.user_id
    else:
        # (optional) validate provided user exists
        if db.get(models.User, payload["caretaker_id"]) is None:
            raise HTTPException(status_code=400, detail="caretaker_id does not exist")

    # Don’t let clients set recorded_at to None
    if payload.get("recorded_at") is None:
        payload.pop("recorded_at", None)

    for k, v in payload.items():
        setattr(obj, k, v)

    db.add(obj); db.commit(); db.refresh(obj)

    log_audit(
        db,
        entity=AuditEntity.HEALTH,
        entity_id=obj.health_record_id,
        action=AuditAction.UPDATE,
        user_id=me.user_id,
        details={"changes": payload}
    )
    db.commit()

    return obj

# ---------- delete (token + role) ----------
@api.delete(
    "/pig-health/{record_id}",
    status_code=204,
    dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.CARETAKER))]
)
def delete_pig_health(record_id: int, db: Session = Depends(get_db)):
    obj = _health_or_404(db, record_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- BOOKINGS CRUD ----


def _booking_or_404(db: Session, booking_id: int) -> models.Booking:
    obj = db.get(models.Booking, booking_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Booking not found")
    return obj

def _ensure_receipt_for_booking(db: Session, booking: models.Booking):
    """
    Idempotent: create a ReservationReceipt for this booking if one doesn't exist.
    Called when a booking is approved.
    """
    existing = (
        db.query(models.ReservationReceipt)
          .filter(models.ReservationReceipt.booking_id == booking.id)
          .first()
    )
    if existing:
        return existing

    payload = {
        "receipt_no": f"RCPT-{booking.id:06d}",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "client_id": booking.client_id,
        "type": booking.type,
        "item_details": booking.item_details,
        "booking_date": str(booking.booking_date),
        "status": booking.status,
        "approved_by": booking.approved_by,
    }

    rec = models.ReservationReceipt(
        booking_id=booking.id,
        receipt_data=json.dumps(payload, ensure_ascii=False),
    )
    db.add(rec)
    return rec

@api.post("/bookings/{booking_id}/decision", response_model=BookingOut,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.SALES))])
def decide_booking(
    booking_id: int,
    decision: BookingDecisionIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="booking not found")

    if decision.decision == "approved":
        booking.status = "approved"
        booking.approved_by = user.user_id

        # fetch pigs in this booking
        pigs_ids = db.execute(
            select(models.BookingPig.pigs_id).where(models.BookingPig.booking_id == booking_id)
        ).scalars().all()

        if pigs_ids:
            # set available pigs to reserved (only those currently available)
            db.query(models.AvailablePig).filter(
                models.AvailablePig.pigs_id.in_(pigs_ids),
                models.AvailablePig.status == "available",
            ).update({"status": "reserved"}, synchronize_session=False)

        _ensure_receipt_for_booking(db, booking)

    else:
        booking.status = "declined"
        booking.approved_by = user.user_id

    db.add(booking); db.commit(); db.refresh(booking)

    # return with pigs_ids included
    linked = db.execute(
        select(models.BookingPig.pigs_id).where(models.BookingPig.booking_id == booking_id)
    ).scalars().all()
    return BookingOut(**booking.__dict__, pigs_ids=linked)

@api.get("/bookings", response_model=list[BookingOut], dependencies=[Depends(oauth2_scheme)])
def list_bookings(
    db: Session = Depends(get_db),
    client_id: int | None = None,
    status: str | None = None,
    start: date | None = None,
    end: date | None = None,
    user: models.User = Depends(get_current_user),
):
    # Base query
    q = db.query(models.Booking)

    # Normalize role
    user_role = getattr(user.role, "value", user.role)
    user_role = str(user_role).upper()

    # Normalize status
    status_norm = status.lower() if status else None

    if user_role in (Role.ADMIN.value, Role.SALES.value):
        # Staff: all bookings, default to pending
        if status_norm:
            q = q.filter(models.Booking.status == status_norm)
        else:
            q = q.filter(models.Booking.status == "pending")
        if client_id is not None:
            q = q.filter(models.Booking.client_id == client_id)
    else:
        # Clients: only their bookings
        q = q.filter(models.Booking.client_id == user.user_id)
        if status_norm:
            q = q.filter(models.Booking.status == status_norm)

    if start:
        q = q.filter(models.Booking.booking_date >= start)
    if end:
        q = q.filter(models.Booking.booking_date <= end)

    # Join with booking_pigs and group pig ids
    results = (
        db.query(
            models.Booking,
            func.group_concat(models.BookingPig.pigs_id).label("pigs_ids"),
        )
        .outerjoin(models.BookingPig, models.Booking.id == models.BookingPig.booking_id)
        .filter(q.whereclause if q.whereclause is not None else True)
        .group_by(models.Booking.id)
        .order_by(models.Booking.booking_date.desc(), models.Booking.id.desc())
        .all()
    )

    # Map results into BookingOut schema with pigs_ids
    output = []
    for booking, pigs_ids in results:
        pigs_list = [int(pid) for pid in pigs_ids.split(",")] if pigs_ids else []
        obj = BookingOut.from_orm(booking)
        obj.pigs_ids = pigs_list
        output.append(obj)

    return output


@api.post("/bookings", response_model=BookingOut,
          status_code=201,
          dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.CLIENT))])
def create_booking(
    data: BookingIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    payload = data.model_dump(exclude_none=True)

    # normalize/validate type
    t = str(payload.get("type", "")).lower()
    if t not in ("pig", "lechon", "market"):
        raise HTTPException(status_code=400, detail="type must be 'pig' or 'lechon' or 'market'")
    payload["type"] = t

    # force ownership + initial state
    payload["client_id"] = user.user_id
    payload["status"] = "pending"

    # create the booking
    booking = models.Booking(**{k: v for k, v in payload.items() if k != "pigs_ids"})
    db.add(booking)
    db.flush()  # get booking.id before inserting junction rows

    # validate all pigs exist
    pigs_ids = list(dict.fromkeys(data.pigs_ids))  # dedupe
    if not pigs_ids:
        raise HTTPException(status_code=400, detail="pigs_ids cannot be empty")

    rows = db.execute(select(models.Pig.id).where(models.Pig.id.in_(pigs_ids))).scalars().all()
    missing = set(pigs_ids) - set(rows)
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown pigs_id(s): {sorted(missing)}")

    # (optional) ensure all pigs are listed & available/reserved constraints as you like
    # e.g., ensure they are currently 'available' in available_pigs:
    # bad = db.query(models.AvailablePig).filter(models.AvailablePig.pigs_id.in_(pigs_ids),
    #                                           models.AvailablePig.status != "available").all()
    # if bad:
    #     raise HTTPException(status_code=409, detail="Some pigs are not available")

    # insert into booking_pigs
    db.execute(insert(models.BookingPig), [
        {"booking_id": booking.id, "pigs_id": pid} for pid in pigs_ids
    ])

    db.commit()
    db.refresh(booking)

    # attach pigs_ids to response
    out = BookingOut(**booking.__dict__, pigs_ids=pigs_ids)
    return out

@api.get("/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    return _booking_or_404(db, booking_id)

@api.put("/bookings/{booking_id}", response_model=BookingOut, dependencies=[Depends(oauth2_scheme)])
def update_booking(
    booking_id: int,
    data: BookingUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles(Role.ADMIN, Role.SALES, Role.CLIENT))
):
    booking = _booking_or_404(db, booking_id)

    # Clients can only edit their own booking’s non-status fields
    if user.role == Role.CLIENT.value and booking.client_id != user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    payload = data.model_dump(exclude_unset=True)

    # do NOT allow status/approved_by/approved_at via PUT
    for forbidden in ("status", "approved_by", "approved_at"):
        if forbidden in payload:
            raise HTTPException(status_code=400, detail=f"Use /bookings/{{id}}/decision to change status")

    for k, v in payload.items():
        setattr(booking, k, v)

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

@api.delete("/bookings/{booking_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    obj = _booking_or_404(db, booking_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---- RECEIPTS CRUD ----

def _receipt_or_404(db: Session, rid: int) -> models.ReservationReceipt:
    obj = db.get(models.ReservationReceipt, rid)
    if not obj:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return obj

@api.get("/receipts", response_model=List[ReceiptOut])
def list_receipts(db: Session = Depends(get_db), booking_id: int | None = None):
    q = db.query(models.ReservationReceipt)
    if booking_id is not None:
        q = q.filter(models.ReservationReceipt.booking_id == booking_id)
    rows = q.order_by(models.ReservationReceipt.generated_at.desc(), models.ReservationReceipt.id.desc()).all()

    # convert JSON string back to dict for the response
    for r in rows:
        try:
            r.receipt_data = json.loads(r.receipt_data)  # type: ignore[attr-defined]
        except Exception:
            pass
    return rows

@api.post("/receipts", response_model=ReceiptOut, status_code=201)
def create_receipt(data: ReceiptIn, db: Session = Depends(get_db)):
    # FK guard
    if db.execute("SELECT 1 FROM bookings WHERE booking_id=%s", (data.booking_id,)).first() is None:
        raise HTTPException(status_code=400, detail="booking_id does not exist")

    #one receipt per booking — enforce
    exists = db.query(models.ReservationReceipt).filter_by(booking_id=data.booking_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="Receipt already exists for this booking")

    obj = models.ReservationReceipt(
        booking_id=data.booking_id,
        receipt_data=json.dumps(data.receipt_data, ensure_ascii=False),
    )
    db.add(obj); db.commit(); db.refresh(obj)

    # turn string back to dict for response
    obj.receipt_data = data.receipt_data  # type: ignore[attr-defined]
    return obj

@api.get("/receipts/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    obj = _receipt_or_404(db, receipt_id)
    try:
        obj.receipt_data = json.loads(obj.receipt_data)  # type: ignore[attr-defined]
    except Exception:
        pass
    return obj

@api.put("/receipts/{receipt_id}", response_model=ReceiptOut)
def update_receipt(receipt_id: int, data: ReceiptUpdate, db: Session = Depends(get_db)):
    obj = _receipt_or_404(db, receipt_id)
    payload = data.model_dump(exclude_unset=True)
    if "receipt_data" in payload and payload["receipt_data"] is not None:
        obj.receipt_data = json.dumps(payload["receipt_data"], ensure_ascii=False)
    db.add(obj); db.commit(); db.refresh(obj)

    # respond with dict
    try:
        obj.receipt_data = json.loads(obj.receipt_data)  # type: ignore[attr-defined]
    except Exception:
        pass
    return obj

@api.delete("/receipts/{receipt_id}", status_code=204,
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    obj = _receipt_or_404(db, receipt_id)
    db.delete(obj); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ---- FEEDBACK CRUD ----

def _feedback_or_404(db: Session, feedback_id: int) -> models.Feedback:
    obj = db.get(models.Feedback, feedback_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return obj

# 1) CLIENT creates feedback (no client_id in body)
@api.post("/feedback", response_model=FeedbackOut, status_code=201,
             dependencies=[Depends(oauth2_scheme)])
def create_feedback(
    data: FeedbackIn,
    db: Session = Depends(get_db),
    me: models.User = Depends(require_roles(Role.CLIENT)),
):
    fb = models.Feedback(
        client_id=me.user_id,     # <— from token
        comment=data.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb

# 2) ADMIN/SALES list all; optional filters
@api.get("/feedback", response_model=List[FeedbackOut],
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN, Role.SALES))])
def list_feedback(
    db: Session = Depends(get_db),
    client_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
):
    q = db.query(models.Feedback)
    if client_id is not None:
        q = q.filter(models.Feedback.client_id == client_id)
    if start:
        q = q.filter(models.Feedback.submitted_at >= datetime.combine(start, datetime.min.time()))
    if end:
        q = q.filter(models.Feedback.submitted_at <= datetime.combine(end, datetime.max.time()))
    return q.order_by(models.Feedback.submitted_at.desc(), models.Feedback.id.desc()).all()

# 3) CLIENT sees own feedback
@api.get("/feedback/mine", response_model=List[FeedbackOut],
            dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.CLIENT))])
def my_feedback(
    db: Session = Depends(get_db),
    me: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Feedback)
          .filter(models.Feedback.client_id == me.user_id)
          .order_by(models.Feedback.submitted_at.desc(), models.Feedback.id.desc())
          .all()
    )

# 4) Read one: allow ADMIN/SALES or the owner client
@api.get("/feedback/{feedback_id}", response_model=FeedbackOut, dependencies=[Depends(oauth2_scheme)])
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    obj = _feedback_or_404(db, feedback_id)
    role = (user.role.value if hasattr(user.role, "value") else user.role).upper()
    if role not in {Role.ADMIN.value, Role.SALES.value} and obj.client_id != user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return obj

# 5) Delete (optional): ADMIN only
@api.delete("/feedback/{feedback_id}", status_code=204,
               dependencies=[Depends(oauth2_scheme), Depends(require_roles(Role.ADMIN))])
def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    obj = _feedback_or_404(db, feedback_id)
    db.delete(obj)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

#available pigs crud

@api.post(
    "/available-pigs",
    response_model=AvailablePigOut,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CARETAKER))],
)
def create_available_pig(
    data: AvailablePigIn,
    db: Session = Depends(get_db),
    me: models.User = Depends(get_current_user),
):
    # Ensure pig exists
    pig = db.get(models.Pig, data.pigs_id)
    if not pig:
        raise HTTPException(status_code=400, detail="pig_id does not exist")

    # Basic validation only (no fixed thresholds)
    if data.weight_kg <= 0:
        raise HTTPException(status_code=400, detail="weight_kg must be > 0")

    # Prevent duplicate active listing for same pig
    existing = (
        db.query(models.AvailablePig)
          .filter(
              models.AvailablePig.pigs_id == data.pigs_id,
              models.AvailablePig.status.in_(["available", "reserved"])
          )
          .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="pig is already listed (available/reserved)")

    obj = models.AvailablePig(
        pigs_id=data.pigs_id,
        weight_kg=data.weight_kg,
        sale_type=data.sale_type,   # "market" or "lechon" — no weight rule enforced
        status="available",
        notes=data.notes,
        listed_by=me.user_id,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# ---------- STAFF: manage listings ----------
@api.put(
    "/available-pigs/{listing_id}",
    response_model=AvailablePigOut,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.CARETAKER))],
)
def update_available_pig(
    listing_id: int,
    data: AvailablePigUpdate,
    db: Session = Depends(get_db),
    me: models.User = Depends(get_current_user),
):
    obj = db.get(models.AvailablePig, listing_id)
    if not obj:
        raise HTTPException(status_code=404, detail="listing not found")

    payload = data.model_dump(exclude_unset=True)

    if "pigs_id" in payload and payload["pigs_id"] is not None:
        # validate pig exists
        if db.get(models.Pig, payload["pigs_id"]) is None:
            raise HTTPException(status_code=400, detail="pigs_id does not exist")
        # avoid duplicate active listing for the new pigs_id
        dup = (
            db.query(models.AvailablePig)
              .filter(models.AvailablePig.pigs_id == payload["pigs_id"],
                      models.AvailablePig.status.in_(["available", "reserved"]),
                      models.AvailablePig.available_pigs_id != listing_id)
              .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="new pigs_id is already listed")

    for k, v in payload.items():
        setattr(obj, k, v)

    db.add(obj); db.commit(); db.refresh(obj)
    return obj

# -------- CLIENT: read only (supports available / reserved / sold / all) --------
@api.get(
    "/available-pigs",
    # was: response_model=list[AvailablePigPublicOut]
    response_model=list[AvailablePigOut],
)
def list_available_pigs_public(
    db: Session = Depends(get_db),
    status: Optional[Literal["available","reserved","sold","all"]] = "available",
    sale_type: Optional[Literal["market","lechon"]] = None,
    min_weight: Optional[float] = None,
    max_weight: Optional[float] = None,
):
    q = db.query(models.AvailablePig)
    if status and status != "all":
        q = q.filter(models.AvailablePig.status == status.lower())
    if sale_type:
        q = q.filter(models.AvailablePig.sale_type == sale_type.lower())
    if min_weight is not None:
        q = q.filter(models.AvailablePig.weight_kg >= min_weight)
    if max_weight is not None:
        q = q.filter(models.AvailablePig.weight_kg <= max_weight)

    return q.order_by(models.AvailablePig.created_at.desc(),
                      models.AvailablePig.id.desc()).all()

# ---- SOWS CRUD ----





# from starlette.routing import Mount, Route
# from fastapi.routing import APIRoute

# def dump_routes(app, prefix=""):
#     print("\n=== ROUTES @", prefix or "/", "===")
#     for r in app.routes:
#         if isinstance(r, Mount):
#             # Mounted sub-app (e.g., /static or /api)
#             try:
#                 title = getattr(r.app, "title", None) or r.app
#             except Exception:
#                 title = r.app
#             print(f"[MOUNT] {r.path!s}  ->  {title}")
#             # Recurse into the mounted app to see its routes too
#             try:
#                 dump_routes(r.app, prefix + r.path)
#             except Exception:
#                 pass
#         elif isinstance(r, APIRoute):
#             methods = ",".join(sorted(r.methods or []))
#             ep = getattr(r.endpoint, "__name__", str(r.endpoint))
#             print(f"[API ] {methods:10s} {r.path!s}  ->  {ep}")
#         elif isinstance(r, Route):
#             methods = ",".join(sorted(r.methods or []))
#             ep = getattr(r.endpoint, "__name__", str(r.endpoint))
#             print(f"[ROUTE] {methods:10s} {r.path!s}  ->  {ep}")
#         else:
#             # Fallback for other route types
#             print(f"[OTHER] {type(r).__name__}  {getattr(r,'path','?')}  ->  {r}")

#     print("=== END ROUTES ===\n")

# dump_routes(app)

ALLOWED_CATS = {"medicine", "vaccine"}

def _load_supply_for_use(db: Session, supply_id: int, *, for_update: bool = True):
    # WRONG (current): where(models.Supply, supply_id == supply_id)
    # RIGHT:
    stmt = select(models.Supply).where(models.Supply.id == supply_id)  # or .supply_id if that’s your PK name
    if for_update:
        stmt = stmt.with_for_update()
    supply = db.scalar(stmt)
    if not supply:
        raise HTTPException(404, "Supply not found.")
    cat = (supply.category or "").strip().lower()
    if cat not in ALLOWED_CATS:
        raise HTTPException(400, "Selected supply is not a medicine or vaccine.")
    if (supply.quantity or 0) < 1:
        raise HTTPException(400, "Selected supply is out of stock.")
    return supply


@api.post("", response_model=PigHealthOut)
def create_health(payload: PigHealthIn,
                  db: Session = Depends(get_db),
                  me = Depends(get_current_user)):

    # tx boundary
    with db.begin():
        # validate supply & lock row
        supply = _load_supply_for_use(db, payload.treatment_supply_id, for_update=True)

        # decrement
        supply.quantity = int(supply.quantity) - 1
        supply.updated_at = datetime.utcnow()  # if you keep server-naive, strip tz
        supply.updated_by = me.user_id

        # create health record; mirror friendly name for display
        rec = models.PigHealthRecord(
            pig_id=payload.pig_id,
            diagnosis=payload.diagnosis,
            treatment_supply_id=supply.id,
            treatment=supply.item_name,                 # <- for display
            recorded_at=payload.recorded_at or datetime.utcnow().replace(tzinfo=None),
            mortality=payload.mortality or False,
            symptoms=payload.symptoms,
            caretaker_id=me.user_id
        )
        db.add(rec)
        db.flush()   # get PK

        # return
        out = PigHealthOut.from_orm(rec)
        return out


@api.put("/{health_record_id}", response_model=PigHealthOut)
def update_health(health_record_id: int,
                  payload: PigHealthUpdate,
                  db: Session = Depends(get_db),
                  me = Depends(get_current_user)):

    with db.begin():
        rec = db.get(models.PigHealthRecord, health_record_id)
        if not rec:
            raise HTTPException(404, "Health record not found.")

        # If changing the supply, perform A→B swap atomically
        if payload.treatment_supply_id is not None and payload.treatment_supply_id != rec.treatment_supply_id:
            # lock old and new rows in a consistent order to avoid deadlocks
            old_id = rec.treatment_supply_id
            new_id = payload.treatment_supply_id
            first, second = sorted([old_id, new_id])

            s_first  = _load_supply_for_use(db, first, for_update=True)   # validates cat/qty when used
            s_second = _load_supply_for_use(db, second, for_update=True)

            # we only need to validate stock on the NEW one; put 1 back to old
            # Determine which object is old/new after sorting
            s_old  = s_first  if old_id == first  else s_second
            s_new  = s_second if new_id == second else s_first

            # return 1 to A (old)
            s_old.quantity  = int(s_old.quantity) + 1
            s_old.updated_at = datetime.utcnow()
            s_old.updated_by = me.user_id

            # deduct 1 from B (new) - validate stock first
            if (s_new.quantity or 0) < 1:
                raise HTTPException(400, "New treatment is out of stock.")
            s_new.quantity  = int(s_new.quantity) - 1
            s_new.updated_at = datetime.utcnow()
            s_new.updated_by = me.user_id

            # update record
            rec.treatment_supply_id = s_new.id
            rec.treatment = s_new.item_name

        # non-supply fields
        if payload.diagnosis is not None:
            rec.diagnosis = payload.diagnosis
        if payload.recorded_at is not None:
            rec.recorded_at = payload.recorded_at
        if payload.mortality is not None:
            rec.mortality = bool(payload.mortality)
        if payload.symptoms is not None:
            rec.symptoms = payload.symptoms

        db.flush()
        return PigHealthOut.from_orm(rec)
