import logging
from typing import Optional
import httpx

from app.config import get_settings

logger = logging.getLogger("texted.email")
settings = get_settings()


async def send_emailjs_email(to_email: str, subject: str, code: str, purpose: str) -> bool:
    """
    Send email using EmailJS REST API or fallback to logging in dev/test.
    """
    if settings.emailjs_service_id and settings.emailjs_template_id and settings.emailjs_public_key:
        payload = {
            "service_id": settings.emailjs_service_id,
            "template_id": settings.emailjs_template_id,
            "user_id": settings.emailjs_public_key,
            "template_params": {
                "to_email": to_email,
                "subject": subject,
                "code": code,
                "purpose": purpose,
            },
        }
        if settings.emailjs_private_key:
            payload["accessToken"] = settings.emailjs_private_key
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.emailjs.com/api/v1.0/email/send",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    logger.info("Email dispatched successfully to %s for %s", to_email, purpose)
                    return True
                else:
                    logger.error("EmailJS failed with status %d: %s", response.status_code, response.text)
                    if settings.environment != "production":
                        print(f"\n=======================================================\n[DEV CODE FALLBACK] Verification Code for {to_email}: {code}\n=======================================================\n", flush=True)
                    return False
        except Exception as exc:
            logger.error("Failed to connect to EmailJS: %s", exc)
            if settings.environment != "production":
                print(f"\n=======================================================\n[DEV CODE FALLBACK] Verification Code for {to_email}: {code}\n=======================================================\n", flush=True)
            return False
    else:
        # Development / Testing fallback
        logger.info("[DEV_EMAIL] Purpose: %s | To: %s | Code: %s", purpose, to_email, code)
        return True


async def send_verification_email(to_email: str, code: str) -> bool:
    return await send_emailjs_email(
        to_email=to_email,
        subject="Your Texted Verification Code",
        code=code,
        purpose="email_verification",
    )


async def send_password_reset_email(to_email: str, code: str) -> bool:
    return await send_emailjs_email(
        to_email=to_email,
        subject="Your Texted Password Reset Code",
        code=code,
        purpose="password_reset",
    )
