# ================================
# ROXLY Data Models
# This defines what a USER looks like
# in your database — like designing
# the columns in a spreadsheet
# ================================

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    # The name of the table in your database
    __tablename__ = "users"

    # Every user gets a unique ID number automatically
    id = Column(Integer, primary_key=True, index=True)

    # Their chosen username (must be unique)
    username = Column(String, unique=True, index=True)

    # Their email address (must be unique)
    email = Column(String, unique=True, index=True)

    # Their password — stored scrambled, never plain text
    hashed_password = Column(String)

    # Are they a Pro subscriber?
    is_pro = Column(Boolean, default=False)

    # Their last known location (for the map)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Their chosen dot color on the map
    dot_color = Column(String, default="#39FF14")

    # Is their account active?
    is_active = Column(Boolean, default=True)

    # When did they sign up?
    created_at = Column(DateTime(timezone=True), server_default=func.now())