from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY")
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY")
STRIPE_PUB_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


class CheckoutForm(BaseModel):
    username: str
    plan: str
    success_url: str = "https://roxlyfive.com"
    cancel_url: str = "https://roxlyfive.com"


class WebhookForm(BaseModel):
    username: str


@router.get("/config")
def get_stripe_config():
    return {
        "publishable_key": STRIPE_PUB_KEY,
        "monthly_price": STRIPE_PRICE_MONTHLY,
        "yearly_price": STRIPE_PRICE_YEARLY
    }


@router.post("/create-checkout")
def create_checkout(form: CheckoutForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    price_id = STRIPE_PRICE_MONTHLY if form.plan == "monthly" else STRIPE_PRICE_YEARLY
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=form.success_url + "?upgraded=true",
            cancel_url=form.cancel_url,
            client_reference_id=form.username,
            metadata={"username": form.username}
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── STRIPE WEBHOOK — automatically upgrades/downgrades users ──
@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            import json
            event = json.loads(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    event_type = event["type"] if isinstance(event, dict) else event.type
    data_object = event["data"]["object"] if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        username = data_object.get("client_reference_id") or (data_object.get("metadata") or {}).get("username")
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        if username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user.is_pro = True
                user.dot_color = user.dot_color or "#BF00FF"
                if hasattr(user, "stripe_subscription_id"):
                    user.stripe_subscription_id = subscription_id
                if hasattr(user, "stripe_customer_id"):
                    user.stripe_customer_id = customer_id
                db.commit()

    elif event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        status = data_object.get("status")
        subscription_id = data_object.get("id")
        if status in ("canceled", "unpaid", "incomplete_expired"):
            user = db.query(User).filter(User.stripe_subscription_id == subscription_id).first() if hasattr(User, "stripe_subscription_id") else None
            if user:
                user.is_pro = False
                user.dot_color = "#39FF14"
                db.commit()

    return {"received": True}


@router.post("/upgrade-to-pro")
def upgrade_to_pro(form: WebhookForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_pro = True
    user.dot_color = "#BF00FF"
    db.commit()
    return {"message": "Upgraded to ROXLY Pro", "username": user.username, "is_pro": True, "dot_color": "#BF00FF"}


@router.post("/downgrade")
def downgrade(form: WebhookForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_pro = False
    user.dot_color = "#39FF14"
    db.commit()
    return {"message": "Downgraded to Free", "username": user.username, "is_pro": False}


@router.post("/cancel-subscription")
def cancel_subscription(form: WebhookForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub_id = getattr(user, "stripe_subscription_id", None)
    if sub_id:
        try:
            stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        except Exception:
            pass

    user.is_pro = False
    user.dot_color = "#39FF14"
    db.commit()
    return {"message": "Subscription canceled", "username": user.username, "is_pro": False}


@router.get("/status/{username}")
def check_status(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.username, "is_pro": user.is_pro, "dot_color": user.dot_color}