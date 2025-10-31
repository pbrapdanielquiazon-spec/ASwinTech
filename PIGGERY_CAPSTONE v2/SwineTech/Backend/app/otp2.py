# app/otp2.py
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import os
import random
import string
import uuid
from sqlalchemy.orm import Session

from .otp import EmailOTP, EmailVerification
from .config import get_settings

settings = get_settings()

# ---------- time helpers (naive UTC everywhere) ----------
def utcnow_naive() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


# ---------- crypto / code helpers ----------
def gen_otp_code(length: int) -> str:
    # numeric code, e.g., "483201"
    return "".join(random.choices(string.digits, k=length))

def hash_otp(code: str) -> str:
    # salt with app secret so DB values are not raw codes
    msg = code.encode("utf-8")
    key = settings.APP_SECRET.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

# =========================================================
#  START OTP  (creates a brand-new row, superseding old)
# =========================================================
def start_otp(db: Session, email: str, purpose: str) -> tuple[str, int]:
    """
    Creates a new OTP row for (email, purpose), supersedes any previous active one,
    and returns (raw_code, resend_cooldown_seconds).
    """
    now = utcnow_naive()

    # 1) Generate code + hash it
    code = gen_otp_code(settings.OTP_CODE_LENGTH)  # e.g., 6
    hashed = hash_otp(code)

    # 2) Compute timestamps (naive UTC)
    expires_at   = now + timedelta(minutes=settings.OTP_EXP_MINUTES)              # e.g., 5
    resend_after = now + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)  # e.g., 60

    # 3) Supersede any older active record for the same (email, purpose)
    # 3) Supersede ALL older active records for the same (email, purpose)
    db.query(EmailOTP).filter(
        EmailOTP.email == email,
        EmailOTP.purpose == purpose,
        EmailOTP.superseded == False,
    ).update({"superseded": True}, synchronize_session=False)


    # 4) Insert new row
    otp = EmailOTP(
        email=email,
        purpose=purpose,
        hashed_code=hashed,
        expires_at=expires_at,
        attempts=0,
        resend_after=resend_after,
        superseded=False,
        last_sent_at=now,
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # Caller will send the *raw* code via email; we never store raw codes.
    return code, settings.OTP_RESEND_COOLDOWN_SECONDS

# =========================================================
#  VERIFY OTP  (checks last active, compares hash, returns token)
# =========================================================
def verify_otp(db: Session, email: str, purpose: str, code: str) -> tuple[bool, dict]:
    code = (code or "").strip()
    if not (code.isdigit() and len(code) == settings.OTP_CODE_LENGTH):
        return False, {"detail": "Invalid code."}

    """
    Verifies the latest non-superseded OTP for (email, purpose).
    On success, returns (True, {"email_verification_token": <jti>}).
    On failure, returns (False, {"detail": "...reason..."})
    """
    now = utcnow_naive()

    # 1) Pull the latest active record
    rec = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.superseded == False,
        )
        .order_by(EmailOTP.id.desc())
        .first()
    )
    if not rec:
        return False, {"detail": "No active code. Please request a new one."}

    # 2) Expiry check (naive vs naive)
    if rec.expires_at < now:
        return False, {"detail": "Code expired. Please request a new one."}

    # (Optional) attempts limit
    if rec.attempts is not None and rec.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False, {"detail": "Too many attempts. Please request a new code."}

    # 3) Compare hashes (constant-time)
    expected = rec.hashed_code
    given = hash_otp(code)
    if not hmac.compare_digest(expected, given):
        # bump attempts on failure
        rec.attempts = (rec.attempts or 0) + 1
        db.add(rec)
        db.commit()
        return False, {"detail": "Invalid code."}

    # 4) Success -> mint a short-lived EmailVerification row (token = jti)
    jti = uuid.uuid4().hex
    ev = EmailVerification(
        email=email,
        purpose=purpose,
        jti=jti,
        issued_at=now,
        expires_at=now + timedelta(minutes=15),  # token lifetime; tune if you want
        used=False,
        used_at=None,
    )
    db.add(ev)
    db.commit()

    return True, {"email_verification_token": jti}


def verify_email_token(db: Session, email: str, purpose: str, token: str) -> tuple[bool, str]:
    """
    Validates a short-lived email verification token (jti) that was created
    by verify_otp(). If valid, mark it used and return (True, "ok").
    Otherwise return (False, reason).
    """
    now = utcnow_naive()

    ev = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.jti == token,
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
            EmailVerification.used == False,
        )
        .order_by(EmailVerification.id.desc())
        .first()
    )

    if not ev:
        return False, "Invalid or already used verification token."
    if ev.expires_at < now:
        return False, "Verification token expired."

    # consume token
    ev.used = True
    ev.used_at = now
    db.add(ev)
    db.commit()

    return True, "ok"
