import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.email_service import send_verification_email, send_password_reset_email
from app import models, schemas
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    validate_password_strength,
    generate_verification_code,
    hash_code,
    verify_code_hash,
)

logger = logging.getLogger("texted.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def is_user_pro(user: models.User) -> bool:
    """Verify authoritative server-side Pro status."""
    if user.subscription_tier == "pro" and user.subscription_status in ("active", "trialing"):
        if user.subscription_period_end is None or user.subscription_period_end > dt.datetime.utcnow():
            return True
    return False


def build_user_out(user: models.User) -> schemas.UserOut:
    """Build response model with computed properties like is_pro."""
    pro = is_user_pro(user)
    return schemas.UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        native_language_code=user.native_language_code,
        learning_language_code=user.learning_language_code,
        current_streak=user.current_streak or 0,
        longest_streak=user.longest_streak or 0,
        xp=user.xp or 0,
        proficiency_level=user.proficiency_level or "beginner",
        learning_goal=user.learning_goal or "casual",
        onboarding_completed=user.onboarding_completed or False,
        email_verified=user.email_verified or False,
        subscription_tier=user.subscription_tier or "free",
        subscription_status=user.subscription_status or "inactive",
        is_pro=pro,
        daily_messages_count=user.daily_messages_count or 0,
        auto_translate=user.auto_translate or False,
    )


def set_auth_cookie(response: Response, token: str) -> None:
    """Configure secure HttpOnly session cookie."""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear session cookie on logout."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/register", response_model=schemas.TokenResponse)
async def register(payload: schemas.RegisterRequest, response: Response, db: Session = Depends(get_db)):
    pwd_err = validate_password_strength(payload.password)
    if pwd_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pwd_err)

    clean_email = payload.email.strip().lower()
    existing = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    for code in (payload.native_language_code, payload.learning_language_code):
        if code and not db.query(models.Language).filter(models.Language.code == code).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown language code: {code}")

    user = models.User(
        email=clean_email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        native_language_code=payload.native_language_code,
        learning_language_code=payload.learning_language_code,
        email_verified=False,
    )
    db.add(user)
    db.flush()

    # Generate 6-digit email verification code
    code = generate_verification_code()
    expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=10)
    verif_record = models.EmailVerificationCode(
        user_id=user.id,
        code_hash=hash_code(code),
        expires_at=expires_at,
        attempt_count=0,
    )
    db.add(verif_record)

    # Track signup analytics
    try:
        ev = models.AnalyticsEvent(
            user_id=user.id,
            event_name="signup",
            properties=f'{{"email": "{payload.email}"}}',
        )
        db.add(ev)
        ev_verif = models.AnalyticsEvent(
            user_id=user.id,
            event_name="email_verification_started",
            properties=f'{{"email": "{payload.email}"}}',
        )
        db.add(ev_verif)
    except Exception:
        pass

    db.commit()
    db.refresh(user)

    # Send verification email asynchronously
    await send_verification_email(user.email, code)

    token = create_access_token(subject=user.id)
    set_auth_cookie(response, token)
    return schemas.TokenResponse(access_token=token)


@router.post("/verify-email", response_model=schemas.TokenResponse)
def verify_email(payload: schemas.VerifyEmailRequest, response: Response, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this email address.")

    if user.email_verified:
        token = create_access_token(subject=user.id)
        set_auth_cookie(response, token)
        return schemas.TokenResponse(access_token=token)

    record = (
        db.query(models.EmailVerificationCode)
        .filter(
            models.EmailVerificationCode.user_id == user.id,
            models.EmailVerificationCode.used_at.is_(None),
        )
        .order_by(models.EmailVerificationCode.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new code.",
        )

    if record.attempt_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. Please request a new verification code.",
        )

    if dt.datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code.",
        )

    if not verify_code_hash(payload.code, record.code_hash):
        record.attempt_count += 1
        db.commit()
        remaining = 5 - record.attempt_count
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    # Mark verified
    record.used_at = dt.datetime.utcnow()
    user.email_verified = True

    try:
        ev = models.AnalyticsEvent(
            user_id=user.id,
            event_name="email_verified",
            properties=f'{{"email": "{user.email}"}}',
        )
        db.add(ev)
    except Exception:
        pass

    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id)
    set_auth_cookie(response, token)
    return schemas.TokenResponse(access_token=token)


@router.post("/resend-verification")
async def resend_verification(payload: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address.",
        )

    if user.email_verified:
        return {"message": "This account is already verified. Please sign in."}

    # Rate limiting: 60-second cooldown between resends
    latest = (
        db.query(models.EmailVerificationCode)
        .filter(models.EmailVerificationCode.user_id == user.id)
        .order_by(models.EmailVerificationCode.created_at.desc())
        .first()
    )
    if latest and (dt.datetime.utcnow() - latest.created_at).total_seconds() < 60:
        remaining_secs = int(60 - (dt.datetime.utcnow() - latest.created_at).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining_secs} seconds before requesting a new code.",
        )

    # Invalidate previous unused codes
    db.query(models.EmailVerificationCode).filter(
        models.EmailVerificationCode.user_id == user.id,
        models.EmailVerificationCode.used_at.is_(None),
    ).update({"used_at": dt.datetime.utcnow()})

    # Generate new code
    code = generate_verification_code()
    expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=10)
    new_record = models.EmailVerificationCode(
        user_id=user.id,
        code_hash=hash_code(code),
        expires_at=expires_at,
        attempt_count=0,
    )
    db.add(new_record)
    db.commit()

    await send_verification_email(user.email, code)
    return {"message": "A new verification code has been sent to your email."}


@router.post("/forgot-password")
async def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address.",
        )

    # Rate limit: 60 seconds cooldown
    latest = (
        db.query(models.PasswordResetCode)
        .filter(models.PasswordResetCode.user_id == user.id)
        .order_by(models.PasswordResetCode.created_at.desc())
        .first()
    )
    if latest and (dt.datetime.utcnow() - latest.created_at).total_seconds() < 60:
        remaining_secs = int(60 - (dt.datetime.utcnow() - latest.created_at).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining_secs} seconds before requesting another reset code.",
        )

    # Invalidate old unused codes
    db.query(models.PasswordResetCode).filter(
        models.PasswordResetCode.user_id == user.id,
        models.PasswordResetCode.used_at.is_(None),
    ).update({"used_at": dt.datetime.utcnow()})

    code = generate_verification_code()
    expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=15)
    record = models.PasswordResetCode(
        user_id=user.id,
        code_hash=hash_code(code),
        expires_at=expires_at,
        attempt_count=0,
    )
    db.add(record)

    try:
        ev = models.AnalyticsEvent(
            user_id=user.id,
            event_name="password_reset_requested",
            properties=f'{{"email": "{user.email}"}}',
        )
        db.add(ev)
    except Exception:
        pass

    db.commit()

    await send_password_reset_email(user.email, code)
    return {"message": "A password reset code has been sent to your email."}


@router.post("/reset-password")
def reset_password(payload: schemas.ResetPasswordRequest, response: Response, db: Session = Depends(get_db)):
    pwd_err = validate_password_strength(payload.new_password)
    if pwd_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pwd_err)

    clean_email = payload.email.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this email address.")

    record = (
        db.query(models.PasswordResetCode)
        .filter(
            models.PasswordResetCode.user_id == user.id,
            models.PasswordResetCode.used_at.is_(None),
        )
        .order_by(models.PasswordResetCode.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code.")

    if record.attempt_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed attempts. Please request a new password reset code.",
        )

    if dt.datetime.utcnow() > record.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new one.",
        )

    if not verify_code_hash(payload.code, record.code_hash):
        record.attempt_count += 1
        db.commit()
        remaining = 5 - record.attempt_count
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reset code. {remaining} attempt(s) remaining.",
        )

    # Invalidate token and update password
    record.used_at = dt.datetime.utcnow()
    user.hashed_password = hash_password(payload.new_password)

    try:
        ev = models.AnalyticsEvent(
            user_id=user.id,
            event_name="password_reset_completed",
            properties=f'{{"email": "{user.email}"}}',
        )
        db.add(ev)
    except Exception:
        pass

    db.commit()
    db.refresh(user)

    # Automatically log the user in with new session
    token = create_access_token(subject=user.id)
    set_auth_cookie(response, token)
    return {"message": "Password has been successfully reset. You are now logged in.", "access_token": token}


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    clean_email = form_data.username.strip().lower()
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(subject=user.id)
    set_auth_cookie(response, token)
    return schemas.TokenResponse(access_token=token)


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = dt.date.today()
    if current_user.last_message_date != today:
        current_user.daily_messages_count = 0
        current_user.last_message_date = today
        db.commit()
    return build_user_out(current_user)


@router.post("/onboarding", response_model=schemas.UserOut)
def complete_onboarding(
    payload: schemas.OnboardingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lang = db.query(models.Language).filter_by(code=payload.learning_language_code).first()
    if not lang:
        from app.llm_client import PERSONAS
        p = PERSONAS.get(payload.learning_language_code)
        name = p["language_name"] if p else payload.learning_language_code.upper()
        lang = models.Language(code=payload.learning_language_code, name=name)
        db.add(lang)
        db.commit()

    current_user.learning_language_code = payload.learning_language_code
    if payload.native_language_code:
        current_user.native_language_code = payload.native_language_code
    current_user.proficiency_level = payload.proficiency_level
    current_user.learning_goal = payload.learning_goal
    if payload.display_name:
        current_user.display_name = payload.display_name
    current_user.onboarding_completed = True

    other_convos = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.user_id == current_user.id,
            models.Conversation.status == "active",
            models.Conversation.language_code != payload.learning_language_code,
        )
        .all()
    )
    for c in other_convos:
        c.status = "completed"

    from app.llm_client import get_persona_for_language, get_opening_message
    persona = get_persona_for_language(payload.learning_language_code)
    existing_convo = (
        db.query(models.Conversation)
        .filter_by(user_id=current_user.id, status="active", language_code=payload.learning_language_code)
        .first()
    )
    if not existing_convo:
        new_convo = models.Conversation(
            user_id=current_user.id,
            language_code=payload.learning_language_code,
            persona_name=persona["name"],
            topic=persona["topic"],
            status="active",
        )
        db.add(new_convo)
        db.flush()
        db.add(models.Message(
            conversation_id=new_convo.id,
            sender="ai",
            content=get_opening_message(persona, payload.proficiency_level),
            feedback=None,
        ))

    try:
        ev = models.AnalyticsEvent(
            user_id=current_user.id,
            event_name="onboarding_complete",
            properties=f'{{"language": "{payload.learning_language_code}", "level": "{payload.proficiency_level}", "goal": "{payload.learning_goal}"}}',
        )
        db.add(ev)
    except Exception:
        pass

    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)


@router.put("/profile", response_model=schemas.UserOut)
def update_profile(
    payload: schemas.ProfileUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.native_language_code is not None:
        current_user.native_language_code = payload.native_language_code

    level_changed = (
        payload.proficiency_level is not None
        and payload.proficiency_level.lower() != (current_user.proficiency_level or "").lower()
    )
    if payload.proficiency_level is not None:
        current_user.proficiency_level = payload.proficiency_level

    if payload.learning_goal is not None:
        current_user.learning_goal = payload.learning_goal
    if payload.auto_translate is not None:
        current_user.auto_translate = payload.auto_translate

    lang_changed = (
        payload.learning_language_code is not None
        and payload.learning_language_code != current_user.learning_language_code
    )
    if lang_changed:
        current_user.learning_language_code = payload.learning_language_code

    from app.llm_client import get_persona_for_language, get_opening_message
    target_lang = current_user.learning_language_code or "es"
    persona = get_persona_for_language(target_lang)

    if lang_changed:
        other_convos = (
            db.query(models.Conversation)
            .filter(
                models.Conversation.user_id == current_user.id,
                models.Conversation.status == "active",
                models.Conversation.language_code != target_lang,
            )
            .all()
        )
        for c in other_convos:
            c.status = "completed"

    active_convo = (
        db.query(models.Conversation)
        .filter_by(user_id=current_user.id, status="active", language_code=target_lang)
        .first()
    )

    expected_opening = get_opening_message(persona, current_user.proficiency_level)

    if not active_convo:
        new_convo = models.Conversation(
            user_id=current_user.id,
            language_code=target_lang,
            persona_name=persona["name"],
            topic=persona["topic"],
            status="active",
        )
        db.add(new_convo)
        db.flush()
        db.add(models.Message(
            conversation_id=new_convo.id,
            sender="ai",
            content=expected_opening,
            feedback=None,
        ))
    elif level_changed:
        msgs = db.query(models.Message).filter_by(conversation_id=active_convo.id).all()
        user_msgs = [m for m in msgs if m.sender == "user"]
        if len(user_msgs) == 0 and len(msgs) > 0:
            msgs[0].content = expected_opening
        else:
            active_convo.status = "completed"
            active_convo.completed_at = dt.datetime.utcnow()
            new_convo = models.Conversation(
                user_id=current_user.id,
                language_code=target_lang,
                persona_name=persona["name"],
                topic=persona["topic"],
                status="active",
            )
            db.add(new_convo)
            db.flush()
            db.add(models.Message(
                conversation_id=new_convo.id,
                sender="ai",
                content=expected_opening,
                feedback=None,
            ))

    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)
