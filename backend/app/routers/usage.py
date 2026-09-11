import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.routers.auth import is_user_pro
from app import models, schemas
from app.routers.conversation import FREE_DAILY_LIMIT

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=schemas.UsageStatusOut)
def get_usage(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = dt.date.today()
    if current_user.last_message_date != today:
        current_user.daily_messages_count = 0
        current_user.last_message_date = today
        db.commit()

    is_pro = is_user_pro(current_user)
    remaining = 9999 if is_pro else max(0, FREE_DAILY_LIMIT - (current_user.daily_messages_count or 0))

    return schemas.UsageStatusOut(
        tier="pro" if is_pro else "free",
        is_pro=is_pro,
        messages_today=current_user.daily_messages_count or 0,
        daily_limit=9999 if is_pro else FREE_DAILY_LIMIT,
        messages_remaining=remaining,
        can_send=is_pro or remaining > 0,
    )


@router.post("/upgrade")
def legacy_upgrade_attempt():
    """Reject unverified client-side upgrade requests."""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Direct tier upgrades are disabled. Please use /api/billing/create-checkout-session to upgrade.",
    )
