"""
Home Router - Landing page with tutorial section
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")
    return templates.TemplateResponse("home.html", {
        "request": request,
        "user": user
    })
