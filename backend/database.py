# ================================
# ROXLY Database Setup
# This creates and connects to
# your database (like setting up
# a filing cabinet for your app)
# ================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# This creates a simple database file on your computer
# called roxly.db — it stores all your users
DATABASE_URL = "sqlite:///./roxly.db"

# Create the connection to the database
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# This is like a "session" — a conversation with the database
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class that all our data models will inherit from
Base = declarative_base()

# This function hands out database sessions to our routes
# Think of it like opening a drawer, using it, then closing it
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()