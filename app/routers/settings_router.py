"""
Settings router — application configuration and data management.
"""

import shutil
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import LEADS_DIR, SEARCHES_DIR, EXPORTS_DIR, LOGS_DIR
from app.utils.file_storage import load_settings, save_settings
from app.utils.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class SettingsUpdate(BaseModel):
    scrape_delay_min: int = 2
    scrape_delay_max: int = 5
    max_results: int = 20
    request_timeout: int = 30
    email_timeout: int = 15
    user_agent_rotation: bool = True


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the settings page."""
    settings = load_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page": "settings",
        "settings": settings,
    })


@router.post("/api/settings")
async def update_settings(settings_update: SettingsUpdate):
    """Update application settings."""
    settings = settings_update.model_dump()
    save_settings(settings)
    logger.info(f"Settings updated: {settings}")
    return JSONResponse(content={"status": "success", "message": "Settings saved!"})


@router.post("/api/settings/clear-leads")
async def clear_leads():
    """Delete all lead files."""
    count = 0
    for file in LEADS_DIR.glob("*.json"):
        file.unlink()
        count += 1
    logger.info(f"Cleared {count} lead files")
    return JSONResponse(content={"status": "success", "message": f"Deleted {count} lead files."})


@router.post("/api/settings/clear-searches")
async def clear_searches():
    """Delete all search log files."""
    count = 0
    for file in SEARCHES_DIR.glob("*.json"):
        file.unlink()
        count += 1
    logger.info(f"Cleared {count} search files")
    return JSONResponse(content={"status": "success", "message": f"Deleted {count} search files."})


@router.post("/api/settings/clear-exports")
async def clear_exports():
    """Delete all export files."""
    count = 0
    for file in EXPORTS_DIR.iterdir():
        if file.is_file():
            file.unlink()
            count += 1
    logger.info(f"Cleared {count} export files")
    return JSONResponse(content={"status": "success", "message": f"Deleted {count} export files."})


@router.post("/api/settings/clear-logs")
async def clear_logs():
    """Clear the log file."""
    log_file = LOGS_DIR / "app.log"
    if log_file.exists():
        with open(log_file, "w") as f:
            f.write("")
    logger.info("Logs cleared")
    return JSONResponse(content={"status": "success", "message": "Logs cleared."})


@router.post("/api/settings/clear-all")
async def clear_all_data():
    """Delete all data (leads, searches, exports, logs)."""
    for directory in [LEADS_DIR, SEARCHES_DIR, EXPORTS_DIR]:
        for file in directory.iterdir():
            if file.is_file():
                file.unlink()
    # Clear log
    log_file = LOGS_DIR / "app.log"
    if log_file.exists():
        with open(log_file, "w") as f:
            f.write("")
    logger.info("All data cleared")
    return JSONResponse(content={"status": "success", "message": "All data cleared successfully."})
