"""
NSFW Content Classifier - Main Application
Built with FastAPI + MySQL + Jinja2 Templates
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.routers import auth, classify, home
from app.database import engine, Base

import os
from dotenv import load_dotenv

load_dotenv()

# Create all tables on startup (if DB is available)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[WARNING] Could not connect to MySQL: {e}")
    print("  The app will start, but DB features won't work until MySQL is running.")

app = FastAPI(
    title="NSFW Content Classifier",
    description="Classify and blur NSFW content from images and videos",
    version="1.0.0"
)

# Session middleware for login state
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-this")
)

# CORS (needed for Google OAuth redirects)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Register routers
app.include_router(home.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(classify.router, prefix="/classify")


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "NSFW Classifier is running"}
