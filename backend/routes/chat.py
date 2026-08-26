from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db, Base

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SendMessageForm(BaseModel):
    username: str
    message: str

@router.post("/send")
def send_message(form: SendMessageForm, db: Session = Depends(get_db)):
    if not form.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    msg = ChatMessage(username=form.username, message=form.message.strip()[:500])
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "username": msg.username, "message": msg.message}

@router.get("/messages")
def get_messages(db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(50).all()
    messages.reverse()
    return {
        "messages": [
            {"id": m.id, "username": m.username, "message": m.message,
             "time": m.created_at.isoformat() if m.created_at else None}
            for m in messages
        ]
    }