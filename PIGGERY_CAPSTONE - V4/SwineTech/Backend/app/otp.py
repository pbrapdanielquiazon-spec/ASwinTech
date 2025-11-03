# models/otp.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from .models import Base  # your declarative base

class EmailOTP(Base):
    __tablename__ = "email_otp"

    id          = Column(Integer, primary_key=True)
    email       = Column(String(255), index=True, nullable=False)
    purpose     = Column(String(64), nullable=False)      # 'register'
    hashed_code = Column(String(255), nullable=False)
    expires_at  = Column(DateTime(timezone=False), nullable=False)
    attempts    = Column(Integer, default=0, nullable=False)
    resend_after= Column(DateTime(timezone=False), nullable=True)
    superseded  = Column(Boolean, default=False, nullable=False)
    last_sent_at= Column(DateTime(timezone=False), nullable=True)
    created_at  = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

class EmailVerification(Base):
    __tablename__ = "email_verification"

    id         = Column(Integer, primary_key=True)
    email      = Column(String(255), index=True, nullable=False)
    purpose    = Column(String(50), nullable=False)       # 'register'
    jti        = Column(String(64), unique=True, nullable=False)
    issued_at  = Column(DateTime(timezone=False), nullable=False)
    expires_at = Column(DateTime(timezone=False), nullable=False)
    used       = Column(Boolean, default=False, nullable=False)
    used_at    = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)