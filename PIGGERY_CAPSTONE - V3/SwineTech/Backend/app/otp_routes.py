from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.db import get_db           # <- your existing dependency
from .otp2 import start_otp, verify_otp
from .emailer import send_otp_email

router = APIRouter(prefix="/auth/otp", tags=["auth-otp"])

class StartBody(BaseModel):
    email: EmailStr
    purpose: str = "register"

class VerifyBody(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "register"

@router.post("/start")
async def otp_start(body: StartBody, db: Session = Depends(get_db)):
    code, cooldown = start_otp(db, body.email, body.purpose)
    # send the raw code by email (async)
    await send_otp_email(body.email, code)
    return {"resend_in": cooldown}

@router.post("/verify")
def otp_verify(body: VerifyBody, db: Session = Depends(get_db)):
    ok, payload = verify_otp(db, body.email, body.purpose, body.code)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=payload["detail"])
    # payload = {"email_verification_token": <jti>}
    return payload
