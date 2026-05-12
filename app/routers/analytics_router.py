"""
Analytics router — JSON API for real-time analytics data.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.utils.file_storage import get_analytics_data

router = APIRouter()


@router.get("/api/analytics")
async def analytics():
    """Return analytics data as JSON for dashboard charts and cards."""
    data = get_analytics_data()
    return JSONResponse(content=data)
