import datetime as dt
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session
import stripe

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_verified_user, get_current_user
from app.routers.auth import is_user_pro
from app import models, schemas

logger = logging.getLogger("texted.billing")
router = APIRouter(prefix="/api/billing", tags=["billing"])
settings = get_settings()

if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


@router.post("/create-checkout-session", response_model=schemas.CheckoutSessionResponse)
def create_checkout_session(
    payload: Optional[schemas.CreateCheckoutSessionRequest] = None,
    current_user: models.User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscription purchase.
    Strictly requires an authenticated, email-verified user.
    """
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not configured on this server.",
        )

    price_id = (payload and payload.price_id) or settings.stripe_price_id
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe price ID is missing or not configured.",
        )

    # Ensure Stripe customer exists
    if not current_user.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.display_name or current_user.email,
                metadata={"user_id": current_user.id},
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
            db.refresh(current_user)
        except Exception as e:
            logger.error("Failed to create Stripe customer: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize billing profile with Stripe.",
            )

    success_url = (payload and payload.success_url) or settings.stripe_success_url
    cancel_url = (payload and payload.cancel_url) or settings.stripe_cancel_url

    try:
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"user_id": current_user.id},
            subscription_data={"metadata": {"user_id": current_user.id}},
        )

        try:
            ev = models.AnalyticsEvent(
                user_id=current_user.id,
                event_name="checkout_started",
                properties=f'{{"price_id": "{price_id}"}}',
            )
            db.add(ev)
            db.commit()
        except Exception:
            pass

        return schemas.CheckoutSessionResponse(checkout_url=session.url)
    except Exception as e:
        logger.error("Failed to create Stripe Checkout session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to start checkout session. Please try again.",
        )


@router.post("/create-portal-session", response_model=schemas.PortalSessionResponse)
def create_portal_session(
    current_user: models.User = Depends(get_current_verified_user),
):
    """Allow active Pro subscribers to manage their Stripe subscription/billing details."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not configured.",
        )

    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No associated Stripe customer profile found.",
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=settings.stripe_success_url,
        )
        return schemas.PortalSessionResponse(portal_url=portal_session.url)
    except Exception as e:
        logger.error("Failed to create Stripe billing portal session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to access billing portal.",
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """
    Authoritative Stripe Webhook listener.
    Verifies cryptographic signature using STRIPE_WEBHOOK_SECRET.
    Guarantees idempotent subscription synchronization.
    """
    if not stripe_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing stripe-signature header.")

    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not configured.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook not configured.")

    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=body,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Invalid Stripe webhook signature: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature.")

    event_type = event["type"]
    data_object = event["data"]["object"]

    logger.info("Processing Stripe webhook event: %s", event_type)

    if event_type == "checkout.session.completed":
        user_id = data_object.get("metadata", {}).get("user_id")
        customer_id = data_object.get("customer")
        subscription_id = data_object.get("subscription")

        user = None
        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user and customer_id:
            user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()

        if user:
            user.subscription_tier = "pro"
            user.subscription_status = "active"
            if customer_id:
                user.stripe_customer_id = customer_id
            if subscription_id:
                user.stripe_subscription_id = subscription_id

            try:
                ev = models.AnalyticsEvent(
                    user_id=user.id,
                    event_name="checkout_completed",
                    properties=f'{{"subscription_id": "{subscription_id}"}}',
                )
                db.add(ev)
                ev_sub = models.AnalyticsEvent(
                    user_id=user.id,
                    event_name="subscription_active",
                    properties=f'{{"subscription_id": "{subscription_id}"}}',
                )
                db.add(ev_sub)
            except Exception:
                pass

            db.commit()

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        customer_id = data_object.get("customer")
        sub_id = data_object.get("id")
        sub_status = data_object.get("status", "inactive")
        period_end_timestamp = data_object.get("current_period_end")

        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if not user:
            user_id = data_object.get("metadata", {}).get("user_id")
            if user_id:
                user = db.query(models.User).filter(models.User.id == user_id).first()

        if user:
            user.stripe_subscription_id = sub_id
            user.subscription_status = sub_status
            if period_end_timestamp:
                user.subscription_period_end = dt.datetime.utcfromtimestamp(period_end_timestamp)

            if sub_status in ("active", "trialing"):
                user.subscription_tier = "pro"
            else:
                user.subscription_tier = "free"

            db.commit()

    elif event_type == "customer.subscription.deleted":
        customer_id = data_object.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = "free"
            user.subscription_status = "canceled"

            try:
                ev = models.AnalyticsEvent(
                    user_id=user.id,
                    event_name="subscription_canceled",
                    properties=f'{{"subscription_id": "{data_object.get("id")}"}}',
                )
                db.add(ev)
            except Exception:
                pass

            db.commit()

    elif event_type == "invoice.payment_failed":
        customer_id = data_object.get("customer")
        user = db.query(models.User).filter(models.User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "past_due"
            db.commit()

    return {"status": "success", "event": event_type}
