# app/emailer.py
from fastapi.concurrency import run_in_threadpool
import resend
from app.config import settings


resend.api_key = settings.RESEND_API_KEY  # make sure this is set

async def send_otp_email(to_email: str, code: str):
    params = {
        "from": "onboarding@resend.dev",         # works without a verified domain
        "to": [to_email],
        "subject": "Your SwineTech verification code",
        "text": f"Your code is {code}. It expires in 5 minutes.",
        # (optional) "reply_to": "no-reply@yourapp.com",
    }
    # Emails.send is SYNC; run it in threadpool so we can await safely
    result = await run_in_threadpool(resend.Emails.send, params)
    return result
