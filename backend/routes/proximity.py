# ================================
# ROXLY Proximity Detection
# The core magic — finds who's nearby
# ================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
import math

router = APIRouter(prefix="/proximity", tags=["proximity"])

# ── HOW DISTANCE IS CALCULATED ───────────────────
# We use the Haversine formula
# It calculates the distance between two GPS points
# on the surface of the Earth
# Returns distance in MILES

def calculate_distance(lat1, lon1, lat2, lon2):
    # Earth's radius in miles
    R = 3958.8

    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c  # returns miles

# ── UPDATE LOCATION FORM ─────────────────────────
# What we need from the user to update their location
class LocationUpdate(BaseModel):
    username: str
    latitude: float
    longitude: float
    range_miles: float = 0.25  # default free range

# ── UPDATE MY LOCATION ───────────────────────────
# Called every 30 seconds by the app
# Updates where the user is on the map
@router.post("/update-location")
def update_location(data: LocationUpdate, db: Session = Depends(get_db)):

    # Find the user
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update their location
    user.latitude = data.latitude
    user.longitude = data.longitude
    db.commit()

    return {
        "message": "Location updated",
        "username": user.username,
        "latitude": user.latitude,
        "longitude": user.longitude
    }

# ── FIND NEARBY USERS ────────────────────────────
# The main magic — who's close to me right now?
class NearbyRequest(BaseModel):
    username: str
    latitude: float
    longitude: float
    range_miles: float = 0.25  # free users get 0.25 miles

@router.post("/nearby")
def find_nearby(data: NearbyRequest, db: Session = Depends(get_db)):

    # Get all users who have a location set
    all_users = db.query(User).filter(
        User.latitude != None,
        User.longitude != None,
        User.username != data.username  # exclude yourself
    ).all()

    nearby = []

    for user in all_users:
        # Calculate distance between me and this user
        distance = calculate_distance(
            data.latitude, data.longitude,
            user.latitude, user.longitude
        )

        # Are they within range?
        if distance <= data.range_miles:
            nearby.append({
                "username": user.username,
                "distance_miles": round(distance, 3),
                "dot_color": user.dot_color,
                "is_pro": user.is_pro,
                "latitude": user.latitude,
                "longitude": user.longitude
            })

    # Sort by closest first
    nearby.sort(key=lambda x: x["distance_miles"])

    return {
        "your_location": {
            "latitude": data.latitude,
            "longitude": data.longitude
        },
        "range_miles": data.range_miles,
        "nearby_count": len(nearby),
        "nearby_users": nearby
    }