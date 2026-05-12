"""
Leads router — leads table with filtering, pagination, sorting.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from app.utils.file_storage import load_all_leads, load_lead_file, load_all_lead_files
from app.utils.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/leads", response_class=HTMLResponse)
async def leads_page(request: Request):
    """Render the leads management page."""
    lead_files = load_all_lead_files()
    return templates.TemplateResponse("leads.html", {
        "request": request,
        "page": "leads",
        "lead_files": lead_files,
    })


@router.get("/api/leads")
async def get_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=5, le=100),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("asc"),
    state_filter: Optional[str] = Query(None),
    search_id: Optional[str] = Query(None),
):
    """
    API endpoint: get leads with pagination, filtering, sorting.
    """
    # Load leads
    if search_id:
        lead_file = load_lead_file(search_id)
        if not lead_file:
            return JSONResponse(content={"leads": [], "total": 0, "pages": 0})
        all_leads = lead_file.get("leads", [])
        for lead in all_leads:
            lead["_search_id"] = lead_file.get("search_id", "")
            lead["_search_keyword"] = lead_file.get("search_keyword", "")
            lead["_search_location"] = lead_file.get("location", "")
    else:
        all_leads = load_all_leads()

    # Collect all unique states (before filtering) for the dropdown
    all_leads_unfiltered = load_all_leads() if not search_id else all_leads
    available_states = sorted(set(
        (lead.get("state", "") or "").strip()
        for lead in all_leads_unfiltered
        if (lead.get("state", "") or "").strip()
    ))

    # Filter by search term
    if search:
        search_lower = search.lower()
        all_leads = [
            lead for lead in all_leads
            if search_lower in (lead.get("company_name", "") or "").lower()
            or search_lower in (lead.get("email", "") or "").lower()
            or search_lower in (lead.get("city", "") or "").lower()
            or search_lower in (lead.get("address", "") or "").lower()
            or search_lower in (lead.get("phone", "") or "").lower()
        ]

    # Filter by state
    if state_filter:
        all_leads = [
            lead for lead in all_leads
            if (lead.get("state", "") or "").lower() == state_filter.lower()
        ]

    # Sort
    if sort_by:
        reverse = sort_order == "desc"
        all_leads.sort(key=lambda x: (x.get(sort_by, "") or "").lower(), reverse=reverse)

    # Pagination
    total = len(all_leads)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_leads[start:end]

    return JSONResponse(content={
        "leads": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": total_pages,
        "available_states": available_states,
    })


@router.get("/api/leads/{search_id}")
async def get_leads_by_search(search_id: str):
    """Get all leads from a specific search."""
    lead_file = load_lead_file(search_id)
    if not lead_file:
        return JSONResponse(status_code=404, content={"error": "Search not found"})
    return JSONResponse(content=lead_file)
