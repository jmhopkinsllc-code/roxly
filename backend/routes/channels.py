from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from database import get_db, Base
from models import User
import math

router = APIRouter(prefix="/channels", tags=["channels"])

class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_by = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    is_private = Column(Boolean, default=False)
    password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChannelMember(Base):
    __tablename__ = "channel_members"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer)
    username = Column(String)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class CreateChannelForm(BaseModel):
    name: str
    username: str
    latitude: float
    longitude: float
    is_private: bool = False
    password: str = None

class JoinChannelForm(BaseModel):
    channel_id: int
    username: str

class KickForm(BaseModel):
    channel_id: int
    owner_username: str
    kick_username: str

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
    return R * 2 * math.asin(math.sqrt(a))

@router.post("/create")
def create_channel(form: CreateChannelForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_pro:
        raise HTTPException(status_code=403, detail="Only Pro members can create channels")

    clean_name = form.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Channel name cannot be empty")
    if clean_name.lower() == "general":
        raise HTTPException(status_code=400, detail="'General' is a reserved channel name")

    existing = db.query(Channel).filter(Channel.name == clean_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A channel named '{clean_name}' already exists")

    try:
        new_channel = Channel(
            name=clean_name,
            created_by=form.username,
            latitude=form.latitude,
            longitude=form.longitude,
            is_private=form.is_private,
            password=form.password
        )
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)

        member = ChannelMember(channel_id=new_channel.id, username=form.username)
        db.add(member)
        db.commit()

        return {
            "message": "Channel created",
            "channel_id": new_channel.id,
            "name": new_channel.name,
            "is_private": new_channel.is_private,
            "created_by": new_channel.created_by
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A channel with that name already exists")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/list")
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(Channel.is_active == True).all()
    result = []
    for c in channels:
        members = db.query(ChannelMember).filter(ChannelMember.channel_id == c.id).all()
        result.append({
            "id": c.id,
            "name": c.name,
            "created_by": c.created_by,
            "is_private": c.is_private,
            "member_count": len(members),
            "members": [m.username for m in members]
        })
    return {"total": len(result), "channels": result}

@router.post("/join")
def join_channel(form: JoinChannelForm, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == form.channel_id, Channel.is_active == True).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    existing = db.query(ChannelMember).filter(
        ChannelMember.channel_id == form.channel_id,
        ChannelMember.username == form.username
    ).first()
    if not existing:
        member = ChannelMember(channel_id=form.channel_id, username=form.username)
        db.add(member)
        db.commit()
    return {"message": "Joined channel", "channel": channel.name}

@router.post("/leave")
def leave_channel(form: JoinChannelForm, db: Session = Depends(get_db)):
    member = db.query(ChannelMember).filter(
        ChannelMember.channel_id == form.channel_id,
        ChannelMember.username == form.username
    ).first()
    if member:
        db.delete(member)
        db.commit()
    return {"message": "Left channel"}

@router.post("/kick")
def kick_member(form: KickForm, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == form.channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not channel.is_private:
        raise HTTPException(status_code=403, detail="Only private channels allow kicking members")
    if channel.created_by != form.owner_username:
        raise HTTPException(status_code=403, detail="Only the channel creator can kick members")
    member = db.query(ChannelMember).filter(
        ChannelMember.channel_id == form.channel_id,
        ChannelMember.username == form.kick_username
    ).first()
    if member:
        db.delete(member)
        db.commit()
    return {"message": f"Kicked {form.kick_username}"}

@router.delete("/delete/{channel_id}")
def delete_channel(channel_id: int, username: str, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.created_by != username:
        raise HTTPException(status_code=403, detail="Only the creator can delete this channel")
    db.query(ChannelMember).filter(ChannelMember.channel_id == channel_id).delete()
    channel.is_active = False
    db.commit()
    return {"message": "Channel deleted"}

@router.post("/nearby")
def nearby_channels(data: NearbyChannelsRequest, db: Session = Depends(get_db)):
    all_channels = db.query(Channel).filter(Channel.is_active == True).all()
    nearby = []
    for channel in all_channels:
        distance = calculate_distance(data.latitude, data.longitude, channel.latitude, channel.longitude)
        if distance <= data.range_miles:
            nearby.append({
                "channel_id": channel.id,
                "name": channel.name,
                "created_by": channel.created_by,
                "distance_miles": round(distance, 3),
                "is_private": channel.is_private,
            })
    nearby.sort(key=lambda x: x["distance_miles"])
    return {"range_miles": data.range_miles, "channels_found": len(nearby), "channels": nearby}