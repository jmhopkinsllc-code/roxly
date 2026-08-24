# ================================
# ROXLY User Routes
# Handles signup and login
# ================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from database import get_db
from models import User

# This handles all user-related routes
router = APIRouter(prefix="/users", tags=["users"])

# This is what scrambles passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── SIGNUP FORM ──────────────────────────────
# This defines what info we need to create an account
class SignupForm(BaseModel):
    username: str
    email: str
    password: str

# ── LOGIN FORM ───────────────────────────────
class LoginForm(BaseModel):
    username: str
    password: str

# ── SIGNUP ROUTE ─────────────────────────────
# When someone creates an account this runs
@router.post("/signup")
def signup(form: SignupForm, db: Session = Depends(get_db)):

    # Check if username is already taken
    existing = db.query(User).filter(User.username == form.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check if email is already registered
    existing_email = db.query(User).filter(User.email == form.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Scramble their password before saving
    hashed = pwd_context.hash(form.password)

    # Create the new user
    new_user = User(
        username=form.username,
        email=form.email,
        hashed_password=hashed
    )

    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Account created successfully",
        "username": new_user.username,
        "id": new_user.id
    }

# ── LOGIN ROUTE ──────────────────────────────
@router.post("/login")
def login(form: LoginForm, db: Session = Depends(get_db)):

    # Find the user
    user = db.query(User).filter(User.username == form.username).first()

    # If user not found or password wrong
    if not user or not pwd_context.verify(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong username or password")

    return {
        "message": "Login successful",
        "username": user.username,
        "is_pro": user.is_pro,
        "dot_color": user.dot_color
    }