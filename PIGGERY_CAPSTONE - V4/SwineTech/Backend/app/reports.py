# app/reports.py
from datetime import date, datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date, literal
from sqlalchemy.sql.expression import true 
from .auth import get_current_user, require_roles, UserRole  # you already have these
from .db import get_db
from . import models, schemas

router = APIRouter(prefix="/reports", tags=["Reports"])

# ----- helpers -----

def _date_window(filters: schemas.ReportFilters | None) -> tuple[date | None, date | None]:
    if not filters:
        return None, None
    return filters.date_from, filters.date_to

def _between(col, start: date | None, end: date | None):
    conds = []
    if start:
        conds.append(col >= start)
    if end:
        conds.append(col <= end)
    return and_(*conds) if conds else true()

def _safe_report_type(raw: str | None) -> "schemas.ReportType":
    """
    Coerce whatever is in the DB to a valid ReportType.
    Defaults to 'sales' if empty/invalid.
    """
    raw = (raw or "sales").strip().lower()
    try:
        return schemas.ReportType(raw)
    except ValueError:
        return schemas.ReportType.SALES


# ----- generators -----

def sales(db: Session, start: date | None, end: date | None) -> Dict[str, Any]:
    # Revenue from sales.total_amount (paid within window)
    revenue = (
    db.query(func.sum(models.Sale.total_amount))
      .filter(_between(cast(models.Sale.payment_date, Date), start, end))
      .scalar()
    or 0.0
    )

    expenses = (
    db.query(func.sum(models.Expense.amount))
      .filter(_between(cast(models.Expense.date_spent, Date), start, end))
      .scalar()
    or 0.0
    )

    # Optional monthly breakdown
    monthly = (
        db.query(
            func.date_format(models.Sale.payment_date, "%Y-%m").label("month"),
            func.coalesce(func.sum(models.Sale.total_amount), 0.0).label("revenue"),
            literal(0.0).label("expenses"),
        )
        .filter(_between(cast(models.Sale.payment_date, Date), start, end))
        .group_by("month")
        .all()
    )
    exp_monthly = (
        db.query(
            func.date_format(models.Expense.date_spent, "%Y-%m").label("month"),
            literal(0.0).label("revenue"),
            func.coalesce(func.sum(models.Expense.amount), 0.0).label("expenses"),
        )
        .filter(_between(cast(models.Expense.date_spent, Date), start, end))
        .group_by("month")
        .all()
    )

    # Merge month rows
    month_map: Dict[str, Dict[str, float]] = {}
    for m, rev, _ in monthly:
        month_map.setdefault(m, {"revenue": 0.0, "expenses": 0.0})
        month_map[m]["revenue"] = float(rev)
    for m, _, exp in exp_monthly:
        month_map.setdefault(m, {"revenue": 0.0, "expenses": 0.0})
        month_map[m]["expenses"] = float(exp)

    return {
        "revenue": float(revenue),
        "expenses": float(expenses),
        "profit": float(revenue) - float(expenses),
        "by_month": [{"month": k, "revenue": v["revenue"], "expenses": v["expenses"], "profit": v["revenue"] - v["expenses"]}
                     for k, v in sorted(month_map.items())],
        "window": {"from": str(start) if start else None, "to": str(end) if end else None},
    }


def mortality(db: Session, start: date | None, end: date | None) -> Dict[str, Any]:
    q = (
        db.query(
            models.PigHealthRecord.diagnosis,
            func.count().label("cases")
        )
        .filter(models.PigHealthRecord.mortality == True)  # noqa: E712
        .filter(_between(cast(models.PigHealthRecord.recorded_at, Date), start, end))
        .group_by(models.PigHealthRecord.diagnosis)
        .all()
    )
    total = sum(r.cases for r in q) if q else 0
    return {
        "total_mortalities": int(total),
        "by_cause": [{"diagnosis": d or "Unknown", "cases": int(c)} for d, c in q],
        "window": {"from": str(start) if start else None, "to": str(end) if end else None},
    }


def feed_consumption(db: Session, start: date | None, end: date | None) -> Dict[str, Any]:
    q = (
        db.query(
            models.FeedingLog.feed_type,
            func.coalesce(func.sum(models.FeedingLog.quantity_kg), 0.0).label("kg")
        )
        .filter(_between(cast(models.FeedingLog.feeding_time, Date), start, end))
        .group_by(models.FeedingLog.feed_type)
        .all()
    )
    total = sum(float(kg) for _, kg in q) if q else 0.0
    return {
        "total_kg": float(total),
        "by_feed_type": [{"feed_type": t or "Unknown", "kg": float(kg)} for t, kg in q],
        "window": {"from": str(start) if start else None, "to": str(end) if end else None},
    }


def inventory(db: Session, threshold: float | None) -> Dict[str, Any]:
    rows = (
        db.query(
            models.Supply.item_name,
            models.Supply.category,
            models.Supply.quantity,
            models.Supply.unit,
            models.Supply.updated_at,
        ).all()
    )
    items = [
        {
            "item_name": r.item_name,
            "category": r.category,
            "quantity": float(r.quantity) if r.quantity is not None else None,
            "unit": r.unit,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    low = []
    if threshold is not None:
        for it in items:
            q = it["quantity"]
            if isinstance(q, (int, float)) and q <= threshold:
                low.append(it)

    return {"items": items, "low_stock": low, "threshold": threshold}
    

_GENERATORS = {
    schemas.ReportType.SALES: sales,
    schemas.ReportType.MORTALITY: mortality,
    schemas.ReportType.FEED_CONSUMPTION: feed_consumption,
    schemas.ReportType.INVENTORY: inventory,
}



# ----- endpoints -----

@router.post("/generate", response_model=schemas.ReportOut)
def generate_report(
    payload: schemas.ReportCreateIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.SALES, UserRole.PROCUREMENT)),
):
    start, end = _date_window(payload.filters)
    if payload.report_type == schemas.ReportType.INVENTORY:
        data = inventory(db, (payload.filters or schemas.ReportFilters()).low_stock_threshold)
    else:
        data = _GENERATORS[payload.report_type](db, start, end)

    # Save snapshot?
    if payload.snapshot:
        rep = models.Report(
            report_type=payload.report_type.value,
            generated_by=user.user_id if hasattr(user, "user_id") else None,
            data=data,
        )
        db.add(rep)
        db.commit()
        db.refresh(rep)
        return schemas.ReportOut(
            id=rep.id,
            report_type=schemas.ReportType(rep.report_type),
            generated_by=rep.generated_by,
            generated_at=rep.generated_at,
            data=rep.data,
        )

    # Ephemeral response (not stored)
    now = datetime.utcnow()
    return schemas.ReportOut(
        id=0,
        report_type=payload.report_type,
        generated_by=getattr(user, "user_id", None),
        generated_at=now,
        data=data,
    )
    

@router.get("", response_model=list[schemas.ReportOut])
def list_reports(
    report_type: schemas.ReportType | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(require_roles(UserRole.ADMIN, UserRole.SALES, UserRole.PROCUREMENT)),
):
    q = db.query(models.Report)
    if report_type:
        q = q.filter(models.Report.report_type == report_type.value)
    rows = q.order_by(models.Report.generated_at.desc()).limit(200).all()
    return [
        schemas.ReportOut(
            id=r.id,
            report_type=_safe_report_type(getattr(r, "report_type", None)),
            generated_by=r.generated_by,
            generated_at=r.generated_at,
            data=r.data,
        )
        for r in rows
    ]


@router.get("/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(UserRole.ADMIN, UserRole.SALES, UserRole.PROCUREMENT)),
):
    r = db.get(models.Report, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return schemas.ReportOut(
        id=r.id,
        report_type=schemas.ReportType(r.report_type),
        generated_by=r.generated_by,
        generated_at=r.generated_at,
        data=r.data,
    )
