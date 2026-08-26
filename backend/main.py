from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import users
from routes import proximity
from routes import channels
from routes import voice
from routes import payments
from routes.channels import Channel
from models import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ROXLY API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://roxlyfive.com",
        "https://www.roxlyfive.com",
        "https://roaring-kangaroo-aee155.netlify.app",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(proximity.router)
app.include_router(channels.router)
app.include_router(voice.router)
app.include_router(payments.router)

@app.get("/")
def home():
    return {
        "app": "ROXLY",
        "tagline": "proximity social",
        "status": "server is running",
        "version": "1.1.0"
    }

@app.get("/health")
def health():
    return {"status": "alive"}