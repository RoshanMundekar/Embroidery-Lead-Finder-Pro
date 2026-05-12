"""
Dashboard router — landing page with analytics overview.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.utils.file_storage import get_analytics_data

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect root to dashboard."""
    analytics = get_analytics_data()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page": "dashboard",
        "analytics": analytics,
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard with analytics data."""
    analytics = get_analytics_data()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page": "dashboard",
        "analytics": analytics,
    })
