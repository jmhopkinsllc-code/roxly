from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/voice", tags=["voice"])

LIVEKIT_URL    = os.getenv("LIVEKIT_URL")
LIVEKIT_KEY    = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_SECRET = os.getenv("LIVEKIT_API_SECRET")

class JoinVoiceForm(BaseModel):
    username: str
    channel_name: str

@router.post("/token")
def get_voice_token(form: JoinVoiceForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        from livekit.api import AccessToken, VideoGrants
        token = AccessToken(LIVEKIT_KEY, LIVEKIT_SECRET) \
            .with_identity(form.username) \
            .with_name(form.username) \
            .with_grants(VideoGrants(
                room_join=True,
                room=form.channel_name,
                can_publish=True,
                can_subscribe=True,
            ))
        return {
            "token": token.to_jwt(),
            "livekit_url": LIVEKIT_URL,
            "room": form.channel_name,
            "username": form.username
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/server")
def get_server():
    return {
        "livekit_url": LIVEKIT_URL,
        "status": "ready"
    }