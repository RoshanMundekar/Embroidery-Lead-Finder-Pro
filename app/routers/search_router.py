"""
Search router — search interface and async scraping pipeline.
"""

import asyncio
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from app.services.google_scraper import scrape_google_maps
from app.services.email_scraper import batch_extract_emails
from app.utils.file_storage import save_leads, save_search_log
from app.utils.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# US States list
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]


class SearchRequest(BaseModel):
    keyword: str
    city: Optional[str] = ""
    state: Optional[str] = ""


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """Render the search page."""
    return templates.TemplateResponse("search.html", {
        "request": request,
        "page": "search",
        "us_states": US_STATES,
    })


@router.post("/api/search")
async def perform_search(search_req: SearchRequest):
    """
    Perform a search: scrape Google Maps, extract emails, save results.
    Returns the results as JSON.
    """
    keyword = search_req.keyword.strip()
    city = search_req.city.strip() if search_req.city else ""
    state = search_req.state.strip() if search_req.state else ""

    if not keyword:
        return JSONResponse(
            status_code=400,
            content={"error": "Keyword is required"}
        )

    # Build location string
    location_parts = [p for p in [city, state] if p]
    location = ", ".join(location_parts) if location_parts else "USA"

    logger.info(f"Starting search: '{keyword}' in '{location}'")

    try:
        # Step 1: Scrape Google Maps
        leads = await scrape_google_maps(keyword, location)

        if not leads:
            logger.warning(f"No results found for '{keyword}' in '{location}'")
            # Save empty search log
            search_id = await save_leads(keyword, location, [])
            await save_search_log(keyword, location, 0, search_id)
            return JSONResponse(content={
                "status": "success",
                "message": "No results found. Try different keywords or location.",
                "search_id": search_id,
                "total_results": 0,
                "leads": [],
            })

        # Step 2: Extract emails from websites
        logger.info(f"Extracting emails for {len(leads)} leads...")
        leads = await batch_extract_emails(leads)

        # Step 3: Save results
        search_id = await save_leads(keyword, location, leads)
        await save_search_log(keyword, location, len(leads), search_id)

        logger.info(f"Search complete: {len(leads)} leads saved with ID {search_id}")

        return JSONResponse(content={
            "status": "success",
            "message": f"Found {len(leads)} leads!",
            "search_id": search_id,
            "total_results": len(leads),
            "leads": leads,
        })

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Search failed: {str(e)}"}
        )
