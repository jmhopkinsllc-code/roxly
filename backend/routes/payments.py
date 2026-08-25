from fastapi import APIRouter, Depends, HTTPException
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


class CheckoutForm(BaseModel):
    username: str
    plan: str
    success_url: str = "http://127.0.0.1:5500/success.html"
    cancel_url: str = "http://127.0.0.1:5500/cancel.html"


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
            success_url=form.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=form.cancel_url,
            metadata={"username": form.username}
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upgrade-to-pro")
def upgrade_to_pro(form: WebhookForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_pro = True
    user.dot_color = "#BF00FF"
    db.commit()
    return {
        "message": "Upgraded to ROXLY Pro",
        "username": user.username,
        "is_pro": True,
        "dot_color": "#BF00FF"
    }


@router.post("/downgrade")
def downgrade(form: WebhookForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_pro = False
    user.dot_color = "#39FF14"
    db.commit()
    return {
        "message": "Downgraded to Free",
        "username": user.username,
        "is_pro": False
    }


@router.get("/status/{username}")
def check_status(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "username": user.username,
        "is_pro": user.is_pro,
        "dot_color": user.dot_color
    }