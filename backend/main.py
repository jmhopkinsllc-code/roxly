# ================================
# ROXLY Backend Server v1.1
# Now with user system
# ================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import users
from routes import proximity
from routes import channels
from routes import voice

# Create all database tables automatically
from routes.channels import Channel
Base.metadata.create_all(bind=engine)

# Create the app
app = FastAPI(title="ROXLY API", version="1.1.0")

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect the user routes
app.include_router(users.router)
app.include_router(proximity.router)
app.include_router(channels.router)
app.include_router(voice.router)
# Home route
@app.get("/")
def home():
    return {
        "app": "ROXLY",
        "tagline": "proximity social",
        "status": "server is running",
        "version": "1.1.0"
    }

# Health check
@app.get("/health")
def health():
    return {"status": "alive"}