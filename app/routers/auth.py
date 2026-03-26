"""
Auth Router
Handles:
  - POST /auth/signup   → create account
  - POST /auth/login    → login with email+password
  - GET  /auth/logout   → clear session
  - GET  /auth/google   → redirect to Google OAuth
  - GET  /auth/google/callback → handle Google OAuth return
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth_utils import (
    hash_password, verify_password,
    create_access_token,
    get_google_auth_url, exchange_google_code
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/classify/lab")
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/classify/lab")
    return templates.TemplateResponse("auth/signup.html", {"request": request})


@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("auth/signup.html", {
            "request": request,
            "error": "An account with this email already exists."
        })

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session["user"] = {"id": user.id, "email": user.email, "username": user.username}
    return RedirectResponse("/classify/lab", status_code=303)


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.hashed_password:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email or password."
        })

    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Invalid email or password."
        })

    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "username": user.username or email.split("@")[0],
        "avatar": user.avatar_url
    }
    return RedirectResponse("/classify/lab", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/google")
async def google_login():
    url = get_google_auth_url()
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str, db: Session = Depends(get_db)):
    try:
        userinfo = await exchange_google_code(code)
    except Exception:
        return RedirectResponse("/auth/login?error=google_failed")

    email = userinfo.get("email")
    google_id = userinfo.get("id")
    name = userinfo.get("name", email.split("@")[0])
    avatar = userinfo.get("picture")

    # find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            username=name,
            google_id=google_id,
            avatar_url=avatar
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.google_id:
        user.google_id = google_id
        user.avatar_url = avatar
        db.commit()

    request.session["user"] = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar": user.avatar_url
    }
    return RedirectResponse("/classify/lab", status_code=303)
