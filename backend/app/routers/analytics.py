import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app import models, schemas

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.post("/event")
def track_event(
    payload: schemas.AnalyticsEventRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ev = models.AnalyticsEvent(
        user_id=current_user.id,
        event_name=payload.event_name,
        properties=json.dumps(payload.properties or {}),
    )
    db.add(ev)
    db.commit()
    return {"status": "ok"}


@router.get("/funnel", response_model=schemas.FunnelStatsOut)
def get_funnel(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def count_event(name: str) -> int:
        return db.query(models.AnalyticsEvent).filter_by(event_name=name).count()

    total_users = db.query(models.User).count()
    onboarded_users = db.query(models.User).filter_by(onboarding_completed=True).count()
    pro_users = db.query(models.User).filter_by(subscription_tier="pro").count()

    return schemas.FunnelStatsOut(
        signups=max(total_users, count_event("signup")),
        onboarding_completed=max(onboarded_users, count_event("onboarding_complete")),
        first_user_message=count_event("first_user_message"),
        message_5=count_event("message_5"),
        message_10=count_event("message_10"),
        hit_limit=count_event("hit_limit"),
        upgrade_clicked=count_event("upgrade_clicked"),
        upgraded=max(pro_users, count_event("upgrade_completed")),
    )
