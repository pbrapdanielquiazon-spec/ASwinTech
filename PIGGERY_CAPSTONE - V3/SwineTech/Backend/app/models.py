from __future__ import annotations
from datetime import date, datetime
from sqlalchemy import Integer, String, Date, Text, ForeignKey, Numeric, DateTime, func, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional
from decimal import Decimal
from enum import Enum
from sqlalchemy import Enum as SqlEnum, JSON
from enum import Enum as PyEnum
from sqlalchemy.types import Enum as SAEnum
import enum


# 1) Define the declarative base
class Base(DeclarativeBase):
    pass

class Role(str, Enum):
    ADMIN = "ADMIN"
    SALES = "SALES"
    PROCUREMENT = "PROCUREMENT"
    CARETAKER = "CARETAKER"
    CLIENT = "CLIENT"

class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

# ---- users table mapping (column names match your DB) ----
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # store HASH in this column (never plaintext)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.CLIENT.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE.value)

    profile_picture: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    updated_by_user: Mapped["User | None"] = relationship(remote_side=[user_id])


# 2) Your model mapped to the existing DB columns
class Pig(Base):
    __tablename__ = "pigs"

    id: Mapped[int] = mapped_column("pigs_id", Integer, primary_key=True, autoincrement=True)
    litter_id: Mapped[int | None] = mapped_column(ForeignKey("litters.litter_id", ondelete="SET NULL"), nullable=True)
    litter: Mapped[Optional["Litter"]] = relationship(back_populates="pigs")

    sow_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # relationship to health records
    health_records: Mapped[list["PigHealthRecord"]] = relationship(
    "PigHealthRecord",
    back_populates="pig",
    cascade="all, delete-orphan",
    passive_deletes=True,
    )

class Litter(Base):
    __tablename__ = "litters"

    litter_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    litter_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_date: Mapped[date]
    sow_identifier: Mapped[int | None] = mapped_column(Integer, nullable=True)
    caretaker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # backref to pigs
    pigs: Mapped[list["Pig"]] = relationship(
        back_populates="litter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    # relationship to feeding logs
    feeding_logs: Mapped[list["FeedingLog"]] = relationship(
        back_populates="litter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FeedingLog(Base):
    __tablename__ = "feeding_logs"

    id: Mapped[int] = mapped_column("feeding_log_id", Integer, primary_key=True, autoincrement=True)
    litter_id: Mapped[int] = mapped_column(ForeignKey("litters.litter_id", ondelete="CASCADE"), nullable=False)
    caretaker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    feed_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    feeding_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    litter: Mapped["Litter"] = relationship(back_populates="feeding_logs")

class Expense(Base):
    __tablename__ = "expenses"

    # DB column is expense_id; Python attribute is id
    id: Mapped[int] = mapped_column("expense_id", Integer, primary_key=True, autoincrement=True)

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False) 
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_spent: Mapped[date] = mapped_column(Date, nullable=False)

    recorded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )

#supplies

class Supply(Base):
    __tablename__ = "supplies"

    id: Mapped[int] = mapped_column("supply_id", Integer, primary_key=True, autoincrement=True)
    item_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category:  Mapped[Optional[str]] = mapped_column(String(50), nullable=False, index=True)
    # If your MySQL column is INT, change Numeric(12, 3) -> Integer
    quantity:  Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=0)

    unit:       Mapped[str] = mapped_column(String(20), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"),nullable=True,index=True,)
    # auto-maintain timestamp
    updated_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.now(),server_onupdate=func.now(),)

#sales

class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column("sale_id", Integer, primary_key=True, autoincrement=True)

    booking_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bookings.booking_id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    item_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)

    recorded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True
    )

class PigHealthRecord(Base):
    __tablename__ = "pig_health_records"

    health_record_id: Mapped[int] = mapped_column("health_record_id", Integer, primary_key=True, autoincrement=True)

    # FK to pigs.pigs_id (note the column name)
    pig_id: Mapped[int] = mapped_column(
        "pigs_id",
        ForeignKey("pigs.pigs_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symptoms:  Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    treatment_supply_id: Mapped[int] = mapped_column(
    ForeignKey("supplies.supply_id", onupdate="CASCADE", ondelete="RESTRICT"),
    nullable=False,
    index=True
    )
    mortality: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    caretaker_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # relationship back to Pig
    pig: Mapped["Pig"] = relationship("Pig", back_populates="health_records")

# Bookings

class BookingPig(Base):
    __tablename__ = "booking_pigs"
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.booking_id", ondelete="CASCADE"), primary_key=True)
    pigs_id:    Mapped[int] = mapped_column(ForeignKey("pigs.pigs_id", ondelete="RESTRICT"), primary_key=True)

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column("booking_id", Integer, primary_key=True, autoincrement=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False, index=True
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    item_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    booking_date: Mapped[date] = mapped_column(Date, nullable=False)

    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True, index=True
    )    


class ReservationReceipt(Base):
    __tablename__ = "reservation_receipts"
    __table_args__ = (UniqueConstraint("booking_id", name="uq_receipt_booking"),)

    id: Mapped[int] = mapped_column("receipt_id", Integer, primary_key=True, autoincrement=True)

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.booking_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # store as TEXT (you can keep JSON in here as a string)
    receipt_data: Mapped[str] = mapped_column(Text, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Optional, only if you have a Booking class
    booking: Mapped["Booking"] = relationship("Booking")
    
class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column("feedback_id", Integer, primary_key=True, autoincrement=True)

    # nullable=True lets you record feedback even if the client isn't in the clients table.
    # If you want to force an existing client, set nullable=False and use ON DELETE RESTRICT.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

#inquiries

# --- Inquiry status enum ---
class InquiryStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    RESPONDED = "responded"

# --- Inquiry model (matches your table names/columns) ---
class Inquiry(Base):
    __tablename__ = "inquiry"  # matches your phpMyAdmin screenshot

    id: Mapped[int] = mapped_column("inquiry_id", Integer, primary_key=True, autoincrement=True)

    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unread", server_default="unread", index=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    responded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    response: Mapped[str | None] = mapped_column(String(1000), nullable=True)

#reports

try:
    # If using MySQL, this is nicer than Text
    from sqlalchemy.dialects.mysql import JSON as MySQLJSON
    JSONType = MySQLJSON
except Exception:
    JSONType = Text  # fallback

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column("report_id", Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "PROFIT_AND_LOSS"
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    generated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    # Store JSON snapshot; Text fallback stores a JSON string
    data: Mapped[dict | str] = mapped_column(JSONType, nullable=False)

#available pigs

class SaleType(str, PyEnum):
    market = "market"   # market-weight pigs
    lechon = "lechon"   # lechon-size pigs

class ListingStatus(str, PyEnum):
    available = "available"
    reserved  = "reserved"
    sold      = "sold"
    removed   = "removed"   # manually unlisted

class AvailablePig(Base):
    __tablename__ = "available_pigs"

    id: Mapped[int] = mapped_column("available_pigs_id",Integer, primary_key=True, autoincrement=True)
    pigs_id: Mapped[int] = mapped_column(ForeignKey("pigs.pigs_id", ondelete="CASCADE"), index=True, nullable=False)

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    sale_type: Mapped[str] = mapped_column(SqlEnum(SaleType, name="sale_type", native_enum=True), nullable=False)  # 'market' | 'lechon'
    status: Mapped[str]    = mapped_column(SqlEnum(ListingStatus, name="listing_status", native_enum=True), nullable=False, default=ListingStatus.available)

    listed_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), server_onupdate=func.now(), nullable=False)


# sows


class SowStatus(str, enum.Enum):
    pregnant = "pregnant"
    nonpregnant = "nonpregnant"
    miscarriage = "miscarriage"
    gave_birth = "gave_birth"
    nursing = "nursing"

class Sow(Base):
    __tablename__ = "sows"

    sow_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sow_identifier: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Use SQLAlchemy Enum here (aliased as SAEnum)
    status: Mapped[str] = mapped_column(
        SAEnum(SowStatus, name="sow_status", native_enum=True),  # OK for MySQL too
        nullable=False,
        default=SowStatus.nonpregnant.value
    )

    mating_date: Mapped[Date | None] = mapped_column(Date)
    expected_birth: Mapped[Date | None] = mapped_column(Date)
    last_birth_date: Mapped[Date | None] = mapped_column(Date)

    caretaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", onupdate="CASCADE", ondelete="SET NULL")
    )
    caretaker = relationship("User", lazy="joined")

Index("idx_sows_status", Sow.status)
Index("idx_sows_expected_birth", Sow.expected_birth)
Index("idx_sows_caretaker", Sow.caretaker_id)


# ---------- AUDIT EVENTS (new table; no changes to existing tables) ----------

class AuditEntity(str, enum.Enum):
    LITTER = "litter"
    PIG = "pig"
    HEALTH = "health"
    SOW = "sow"
    FEED_LOG = "feed_log"
    SUPPLY = "supply"
    SALE    = "sale"      # <-- add
    EXPENSE = "expense" 

class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    RECORD = "record"  # for health-specific actions, but can be used elsewhere too

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    entity_type: Mapped[str] = mapped_column(SAEnum(AuditEntity, name="audit_entity"), nullable=False, index=True)
    entity_id:   Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    action:      Mapped[str] = mapped_column(SAEnum(AuditAction, name="audit_action"), nullable=False, index=True)

    # who/when (we do not alter existing tables)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"), nullable=True, index=True)

    # optional JSON summary of changes (e.g., {"status": {"from": "healthy","to":"sick"}})
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    Index("idx_audit_entity", "entity_type", "entity_id")
