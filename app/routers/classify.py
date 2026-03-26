"""
Classify Router
  GET  /classify/lab              → show the Classifying Lab UI
  POST /classify/run              → classify uploaded media
  POST /classify/blur             → classify + blur uploaded media
  POST /classify/youtube          → classify a YouTube video
"""

import os
import uuid
import json
from pathlib import Path
from fastapi import APIRouter, Request, File, UploadFile, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassificationResult
from app.classifier import classifier

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"}


def require_login(request: Request):
    """Redirect to login if no session"""
    user = request.session.get("user")
    if not user:
        return None
    return user


@router.get("/lab", response_class=HTMLResponse)
async def lab_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/auth/login")
    return templates.TemplateResponse("classify/lab.html", {
        "request": request,
        "user": user
    })


@router.post("/run")
async def classify_media(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Classify an uploaded image or video - no blurring"""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    content_type = file.content_type
    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_video = content_type in ALLOWED_VIDEO_TYPES

    if not is_image and not is_video:
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    # save uploaded file
    ext = Path(file.filename).suffix
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = str(UPLOAD_DIR / saved_name)

    with open(saved_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # run classifier
    if is_image:
        result = classifier.classify_image(saved_path)
        media_type = "image"
    else:
        result = classifier.classify_video(saved_path)
        media_type = "video"

    # save result to db
    db_record = ClassificationResult(
        user_id=user["id"],
        media_type=media_type,
        original_filename=file.filename,
        label=result["label"],
        confidence_score=result["confidence_score"],
        is_safe=result["is_safe"],
        was_blurred=False,
        category_scores=result.get("category_scores", "{}")
    )
    db.add(db_record)
    db.commit()

    return JSONResponse({
        "label": result["label"],
        "confidence_score": result["confidence_score"],
        "is_safe": result["is_safe"],
        "was_blurred": False,
        "file_url": f"/static/uploads/{saved_name}",
        "media_type": media_type,
        "category_scores": json.loads(result.get("category_scores", "{}")),
    })


@router.post("/blur")
async def classify_and_blur(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Classify + blur NSFW regions in uploaded image or video"""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    content_type = file.content_type
    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_video = content_type in ALLOWED_VIDEO_TYPES

    if not is_image and not is_video:
        return JSONResponse({"error": "Unsupported file type"}, status_code=400)

    ext = Path(file.filename).suffix
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = str(UPLOAD_DIR / saved_name)
    blurred_name = f"blurred_{uuid.uuid4().hex}{ext}"
    blurred_path = str(UPLOAD_DIR / blurred_name)

    with open(saved_path, "wb") as f:
        content = await file.read()
        f.write(content)

    if is_image:
        result = classifier.classify_and_blur_image(saved_path, blurred_path)
        media_type = "image"
    else:
        result = classifier.classify_and_blur_video(saved_path, blurred_path)
        media_type = "video"

    db_record = ClassificationResult(
        user_id=user["id"],
        media_type=media_type,
        original_filename=file.filename,
        label=result["label"],
        confidence_score=result["confidence_score"],
        is_safe=result["is_safe"],
        was_blurred=True,
        blurred_file_path=blurred_path,
        category_scores=result.get("category_scores", "{}")
    )
    db.add(db_record)
    db.commit()

    return JSONResponse({
        "label": result["label"],
        "confidence_score": result["confidence_score"],
        "is_safe": result["is_safe"],
        "was_blurred": True,
        "original_url": f"/static/uploads/{saved_name}",
        "blurred_url": f"/static/uploads/{blurred_name}",
        "media_type": media_type,
        "category_scores": json.loads(result.get("category_scores", "{}")),
    })


@router.post("/youtube")
async def classify_youtube(
    request: Request,
    youtube_url: str = Form(...),
    mode: str = Form(...),   # "classify" or "blur"
    db: Session = Depends(get_db)
):
    """Download and classify (or blur) a YouTube video"""
    user = request.session.get("user")
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)

    try:
        video_path = classifier.download_youtube_video(youtube_url)
    except Exception as e:
        return JSONResponse({"error": f"Could not download video: {str(e)}"}, status_code=400)

    video_filename = Path(video_path).name

    if mode == "blur":
        blurred_name = f"blurred_{uuid.uuid4().hex}.mp4"
        blurred_path = str(UPLOAD_DIR / blurred_name)
        result = classifier.classify_and_blur_video(video_path, blurred_path)
        result["blurred_url"] = f"/static/uploads/{blurred_name}"
    else:
        result = classifier.classify_video(video_path)

    result["original_url"] = f"/static/uploads/{video_filename}"
    result["media_type"] = "video"
    result["youtube_url"] = youtube_url

    db_record = ClassificationResult(
        user_id=user["id"],
        media_type="youtube",
        media_url=youtube_url,
        label=result["label"],
        confidence_score=result["confidence_score"],
        is_safe=result["is_safe"],
        was_blurred=(mode == "blur"),
        blurred_file_path=result.get("blurred_url"),
        category_scores=result.get("category_scores", "{}")
    )
    db.add(db_record)
    db.commit()

    return JSONResponse(result)
