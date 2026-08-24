# ================================
# ROXLY Channels
# Voice rooms people join to talk
# ================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Base
from models import User
import math

router = APIRouter(prefix="/channels", tags=["channels"])

# ── CHANNEL MODEL ────────────────────────────────
# What a channel looks like in the database
class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_by = Column(String)  # username of creator

    # Location of the channel
    latitude = Column(Float)
    longitude = Column(Float)

    # Is it private? (Pro only)
    is_private = Column(Boolean, default=False)
    password = Column(String, nullable=True)

    # Is the channel active?
    is_active = Column(Boolean, default=True)

    # When was it created?
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ── FORMS ────────────────────────────────────────
class CreateChannelForm(BaseModel):
    name: str
    username: str        # who's creating it
    latitude: float
    longitude: float
    is_private: bool = False
    password: str = None

class JoinChannelForm(BaseModel):
    channel_id: int
    username: str
    password: str = None  # only needed for private channels

class NearbyChannelsRequest(BaseModel):
    latitude: float
    longitude: float
    range_miles: float = 0.25

# ── DISTANCE HELPER ──────────────────────────────
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# ── CREATE A CHANNEL ─────────────────────────────
# Pro users only can create channels
@router.post("/create")
def create_channel(form: CreateChannelForm, db: Session = Depends(get_db)):

    # Find the user
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only Pro users can create channels
    if not user.is_pro:
        raise HTTPException(
            status_code=403,
            detail="Channel creation is a Pro feature. Upgrade to ROXLY Pro."
        )

    # Create the channel
    new_channel = Channel(
        name=form.name,
        created_by=form.username,
        latitude=form.latitude,
        longitude=form.longitude,
        is_private=form.is_private,
        password=form.password
    )

    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    return {
        "message": "Channel created",
        "channel_id": new_channel.id,
        "name": new_channel.name,
        "is_private": new_channel.is_private,
        "created_by": new_channel.created_by
    }

# ── FIND NEARBY CHANNELS ─────────────────────────
@router.post("/nearby")
def nearby_channels(data: NearbyChannelsRequest, db: Session = Depends(get_db)):

    all_channels = db.query(Channel).filter(Channel.is_active == True).all()

    nearby = []
    for channel in all_channels:
        distance = calculate_distance(
            data.latitude, data.longitude,
            channel.latitude, channel.longitude
        )

        if distance <= data.range_miles:
            nearby.append({
                "channel_id": channel.id,
                "name": channel.name,
                "created_by": channel.created_by,
                "distance_miles": round(distance, 3),
                "is_private": channel.is_private,
            })

    nearby.sort(key=lambda x: x["distance_miles"])

    return {
        "range_miles": data.range_miles,
        "channels_found": len(nearby),
        "channels": nearby
    }

# ── GET ALL PUBLIC CHANNELS ──────────────────────
@router.get("/list")
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(
        Channel.is_active == True,
        Channel.is_private == False
    ).all()

    return {
        "total": len(channels),
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "created_by": c.created_by,
                "is_private": c.is_private
            }
            for c in channels
        ]
    }