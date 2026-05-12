"""
Download router — generate and serve JSON, CSV, XLSX files.
"""

import os
from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.config import EXPORTS_DIR
from app.services.export_service import export_to_json, export_to_csv, export_to_xlsx
from app.utils.file_storage import load_all_leads, load_lead_file, get_export_files
from app.utils.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/downloads", response_class=HTMLResponse)
async def downloads_page(request: Request):
    """Render the downloads page."""
    export_files = get_export_files()
    return templates.TemplateResponse("downloads.html", {
        "request": request,
        "page": "downloads",
        "export_files": export_files,
    })


@router.get("/download/json/{search_id}")
async def download_json(search_id: str):
    """Generate and download leads as JSON for a specific search."""
    lead_file = load_lead_file(search_id)
    if not lead_file:
        return JSONResponse(status_code=404, content={"error": "Search not found"})

    filepath = export_to_json(
        lead_file.get("leads", []),
        lead_file.get("search_keyword", ""),
        lead_file.get("location", ""),
    )

    logger.info(f"JSON download: {filepath}")
    return FileResponse(
        filepath,
        media_type="application/json",
        filename=os.path.basename(filepath),
    )


@router.get("/download/csv/{search_id}")
async def download_csv(search_id: str):
    """Generate and download leads as CSV for a specific search."""
    lead_file = load_lead_file(search_id)
    if not lead_file:
        return JSONResponse(status_code=404, content={"error": "Search not found"})

    filepath = export_to_csv(
        lead_file.get("leads", []),
        lead_file.get("search_keyword", ""),
        lead_file.get("location", ""),
    )

    logger.info(f"CSV download: {filepath}")
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=os.path.basename(filepath),
    )


@router.get("/download/xlsx/{search_id}")
async def download_xlsx(search_id: str):
    """Generate and download leads as Excel for a specific search."""
    lead_file = load_lead_file(search_id)
    if not lead_file:
        return JSONResponse(status_code=404, content={"error": "Search not found"})

    filepath = export_to_xlsx(
        lead_file.get("leads", []),
        lead_file.get("search_keyword", ""),
        lead_file.get("location", ""),
    )

    logger.info(f"XLSX download: {filepath}")
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(filepath),
    )


@router.get("/download/all/json")
async def download_all_json():
    """Download all leads as a single JSON file."""
    leads = load_all_leads()
    if not leads:
        return JSONResponse(status_code=404, content={"error": "No leads found"})
    filepath = export_to_json(leads, "all", "all")
    return FileResponse(filepath, media_type="application/json", filename=os.path.basename(filepath))


@router.get("/download/all/csv")
async def download_all_csv():
    """Download all leads as a single CSV file."""
    leads = load_all_leads()
    if not leads:
        return JSONResponse(status_code=404, content={"error": "No leads found"})
    filepath = export_to_csv(leads, "all", "all")
    return FileResponse(filepath, media_type="text/csv", filename=os.path.basename(filepath))


@router.get("/download/all/xlsx")
async def download_all_xlsx():
    """Download all leads as a single Excel file."""
    leads = load_all_leads()
    if not leads:
        return JSONResponse(status_code=404, content={"error": "No leads found"})
    filepath = export_to_xlsx(leads, "all", "all")
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(filepath),
    )


@router.get("/download/file/{filename}")
async def download_export_file(filename: str):
    """Download an existing export file by filename."""
    filepath = EXPORTS_DIR / filename
    if not filepath.exists():
        return JSONResponse(status_code=404, content={"error": "File not found"})

    # Determine media type
    media_types = {
        ".json": "application/json",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    media_type = media_types.get(filepath.suffix, "application/octet-stream")

    return FileResponse(filepath, media_type=media_type, filename=filename)


@router.delete("/api/export/{filename}")
async def delete_export_file(filename: str):
    """Delete an export file."""
    filepath = EXPORTS_DIR / filename
    if filepath.exists():
        filepath.unlink()
        logger.info(f"Deleted export file: {filename}")
        return JSONResponse(content={"status": "success"})
    return JSONResponse(status_code=404, content={"error": "File not found"})
