from typing import Optional, Any, Dict, Literal, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, constr, field_validator
from .models import InquiryStatus
from enum import Enum



class PigIn(BaseModel):
    litter_id: Optional[int] = None          # FK to litters.litter_id
    sow_identifier: Optional[str] = None     # String(50)
    birth_date: Optional[date] = None        # Date
    status: Optional[str] = None             # String(20)
    notes: Optional[str] = None    

class PigOut(PigIn):
    id: int
    class Config:
        from_attributes = True  # Pydantic v2

class PigUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

#litter 

class LitterIn(BaseModel):
    litter_size: Optional[int] = None
    birth_date: date
    sow_identifier: Optional[str] = None

class LitterOut(LitterIn):
    litter_id: int
    sow_identifier: str | None = None
    class Config:
        from_attributes = True  # Pydantic v2

class LitterUpdate(BaseModel):
    sow_identifier: Optional[str] = None   # varchar in DB
    birth_date: Optional[date] = None
    litter_size: Optional[int] = None
    

#feeding log

class FeedingLogIn(BaseModel):
    litter_id: int
    feed_type: str
    quantity_kg: float
    feeding_time: datetime   # e.g. "2025-09-10T07:30:00"

class FeedingLogOut(BaseModel):
    id: int
    litter_id: int
    feed_type: str
    quantity_kg: float
    feeding_time: datetime
    caretaker_id: int | None = None   # <-- add this
    class Config:
        from_attributes = True


class FeedingLogUpdate(BaseModel):
    litter_id: Optional[int] = None
    feed_type: Optional[str] = None
    quantity_kg: Optional[float] = None
    feeding_time: Optional[datetime] = None

#expense

class ExpenseIn(BaseModel):
    description: str
    amount: Decimal
    category: Optional[str] = None
    date_spent: date

class ExpenseOut(ExpenseIn):
    id: int
    class Config:
        from_attributes = True  # Pydantic v2

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    category: Optional[str] = None
    date_spent: Optional[date] = None

#Supplies

class SupplyIn(BaseModel):
    item_name: str
    category: Optional[str] | None = None
    quantity: Decimal = Field(default=0, ge=0)
    unit: str
    

class SupplyOut(SupplyIn):
    id: int
    updated_at: datetime
    updated_by: Optional[int] = None
    class Config:
        from_attributes = True

class SupplyUpdate(BaseModel):
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[Decimal] = Field(default=None, ge=0)
    unit: Optional[str] = None
    

class SupplyAdjustQty(BaseModel):
    quantity: Decimal  # + to add stock, - to consume

#sales

class SaleIn(BaseModel):
    booking_id: Optional[int] = None
    item_type: str
    item_description: Optional[str] = None
    total_amount: Decimal
    payment_date: date
    

class SaleOut(SaleIn):
    id: int
    class Config:
        from_attributes = True  # Pydantic v2

class SaleUpdate(BaseModel):
    booking_id: Optional[int] = None
    item_type: Optional[str] = None
    item_description: Optional[str] = None
    total_amount: Optional[Decimal] = None
    payment_date: Optional[date] = None
    

#pig health record

class PigHealthIn(BaseModel):
    pig_id: int                  # we expose pig_id; maps to column `pigs_id`
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    mortality: bool = False
    recorded_at: datetime | None = None   # optional; server will default to now

    def make_naive(cls, v: datetime | None):
        if v and v.tzinfo is not None:
            return v.replace(tzinfo=None)  # store naive UTC
        return v

class PigHealthOut(PigHealthIn):
    health_record_id: int
    class Config:
        from_attributes = True

class PigHealthUpdate(BaseModel):
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    mortality: Optional[bool] = None
    recorded_at: Optional[datetime] = None
    

#booking

class BookingDecisionIn(BaseModel):
    decision: Literal["approved", "declined"]

class BookingIn(BaseModel):
    type: str 
    item_details: Optional[str] = None
    status: str = "pending"            # optional; default pending
    booking_date: date
    pigs_ids: List[int] = Field(min_items=1)

class BookingOut(BookingIn):
    id: int
    client_id: int
    pigs_ids: list[int] = []
    class Config:
        from_attributes = True

class BookingUpdate(BaseModel):
    client_id: Optional[int] = None
    type: Optional[str] = None
    item_details: Optional[str] = None
    status: Optional[str] = None
    booking_date: Optional[date] = None  

#reservation

class ReceiptIn(BaseModel):
    booking_id: int
    # allow any JSON-like structure; we’ll store as string
    receipt_data: Dict[str, Any] = Field(default_factory=dict)

class ReceiptOut(ReceiptIn):
    id: int
    generated_at: datetime
    class Config:
        from_attributes = True

class ReceiptUpdate(BaseModel):
    receipt_data: Optional[Dict[str, Any]] = None

#Feedback

class FeedbackIn(BaseModel):
    comment: constr(min_length=1, max_length=2000)

class FeedbackOut(FeedbackIn):
    id: int
    client_id: int | None = None 
    submitted_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True  # Pydantic v2

#Inquiry

class InquiryStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    RESPONDED = "responded"

class InquiryCreate(BaseModel):
    subject: constr(min_length=1, max_length=200)
    message: constr(min_length=1, max_length=2000)

class InquiryRespond(BaseModel):
    response: constr(min_length=1, max_length=1000)

class InquiryOut(BaseModel):
    inquiry_id: int = Field(alias="id")
    client_id: int
    subject: str
    message: str
    status: InquiryStatus
    submitted_at: datetime
    responded_by: int | None
    responded_at: datetime | None
    response: str | None    

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,  # allow output using field name (inquiry_id) even though alias is used
    }

class ReportType(str, Enum):
    SALES = "sales"
    MORTALITY = "mortality"
    FEED_CONSUMPTION = "feed_consumption"
    INVENTORY = "inventory"

class ReportFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    low_stock_threshold: Optional[float] = 10  # only used by INVENTORY

class ReportCreateIn(BaseModel):
    report_type: ReportType
    filters: Optional[ReportFilters] = None
    snapshot: bool = True  # save to DB

class ReportOut(BaseModel):
    id: int
    report_type: ReportType
    generated_by: Optional[int] = None
    generated_at: datetime
    data: Any

# Available pigs 

class AvailablePigIn(BaseModel):
    pigs_id: int
    weight_kg: Decimal = Field(gt=0)
    sale_type: Literal["market", "lechon"]
    notes: Optional[str] = None

class AvailablePigUpdate(BaseModel):
    weight_kg: Optional[Decimal] = Field(default=None, gt=0)
    sale_type: Optional[Literal["market", "lechon"]] = None
    status: Optional[Literal["available", "reserved", "sold", "removed"]] = None
    notes: Optional[str] = None

# For staff/admin/caretaker views (full details)
class AvailablePigOut(BaseModel):
    id: int
    pigs_id: int
    weight_kg: Decimal
    sale_type: str
    status: str
    listed_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# For clients (restricted fields)
class AvailablePigPublicOut(BaseModel):
    pigs_id: int
    weight_kg: Decimal
    class Config:
        from_attributes = True


# user count

class UserCountOut(BaseModel):
    total: int
    by_role: Dict[str, int] = {}

class UserOut(BaseModel):
    id: int = Field(alias="user_id")
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    role: str                   # "ADMIN" | "SALES" | "PROCUREMENT" | "CARETAKER" | "CLIENT"
    status: str                 # "ACTIVE" | "INACTIVE"
    profile_picture_url: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2
        allow_population_by_field_name = True


# SOWS

SowStatus = Literal["pregnant","nonpregnant","miscarriage","gave_birth","nursing"]


class SowCreate(BaseModel):
    sow_identifier: constr(min_length=1)
    status: SowStatus
    mating_date: Optional[date] = None
    # optional override; if omitted and mating_date present, backend computes 114 days
    expected_birth: Optional[date] = None

    # Accept "" as None for the two date fields
    @field_validator("mating_date", "expected_birth", mode="before")
    @classmethod
    def _empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

class SowUpdate(BaseModel):
    sow_identifier: Optional[constr(min_length=1)] = None
    status: Optional[SowStatus] = None
    mating_date: Optional[date] = None
    expected_birth: Optional[date] = None
    caretaker_id: Optional[int] = None  # allowed to change on UPDATE

    @field_validator("mating_date", "expected_birth", mode="before")
    @classmethod
    def _empty_string_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

class SowOut(BaseModel):
    sow_id: int
    sow_identifier: str
    status: SowStatus
    mating_date: Optional[date]
    expected_birth: Optional[date]
    caretaker_id: Optional[int]
    is_overdue: bool

    class Config:
        from_attributes = True
# ---------- /SOW SCHEMAS ----------
# ---------- /SOW SCHEMAS ----------

