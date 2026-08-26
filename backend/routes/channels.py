from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Base
from models import User
import math

router = APIRouter(prefix="/channels", tags=["channels"])

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_by = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    is_private = Column(Boolean, default=False)
    password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CreateChannelForm(BaseModel):
    name: str
    username: str
    latitude: float
    longitude: float
    is_private: bool = False
    password: str = None

class NearbyChannelsRequest(BaseModel):
    latitude: float
    longitude: float
    range_miles: float = 0.25

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

@router.post("/create")
def create_channel(form: CreateChannelForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_pro:
        raise HTTPException(status_code=403, detail="Pro feature only")
    existing = db.query(Channel).filter(Channel.name == form.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Channel name already exists")
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

@router.get("/list")
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(
        Channel.is_active == True
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