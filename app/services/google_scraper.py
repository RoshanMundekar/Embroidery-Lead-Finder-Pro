"""
Google Maps scraper — uses SerpAPI to search for businesses on Google Maps.
"""

import asyncio
import re
from typing import Optional

from serpapi import GoogleSearch

from app.config import (
    SERPAPI_API_KEY,
    MAX_RESULTS_PER_SEARCH,
)
from app.utils.logger import logger


async def scrape_google_maps(keyword: str, location: str) -> list[dict]:
    """
    Search Google Maps for business listings using SerpAPI.
    Returns a list of lead dictionaries.
    """
    if not SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEY is not set. Please add it to your .env file.")
        return []

    leads = []
    query = f"{keyword} in {location}"

    try:
        # Run the SerpAPI call in a thread to avoid blocking the event loop
        leads = await asyncio.to_thread(_serpapi_search, query, keyword, location)
    except Exception as e:
        logger.error(f"SerpAPI search failed: {e}", exc_info=True)

    logger.info(f"SerpAPI returned {len(leads)} results for '{keyword}' in '{location}'")
    return leads


def _serpapi_search(query: str, keyword: str, location: str) -> list[dict]:
    """
    Synchronous SerpAPI Google Maps search with pagination support.
    Runs inside asyncio.to_thread().
    """
    leads = []

    params = {
        "engine": "google_maps",
        "q": query,
        "type": "search",
        "api_key": SERPAPI_API_KEY,
        "hl": "en",
        "gl": "us",
    }

    try:
        # First page
        search = GoogleSearch(params)
        results = search.get_dict()

        local_results = results.get("local_results", [])
        logger.info(f"SerpAPI page 1: {len(local_results)} results")

        for place in local_results:
            lead = _parse_place(place)
            if lead:
                leads.append(lead)

            if len(leads) >= MAX_RESULTS_PER_SEARCH:
                break

        # Pagination — fetch more pages if needed
        page = 2
        while len(leads) < MAX_RESULTS_PER_SEARCH:
            next_start = (page - 1) * 20  # SerpAPI uses 20 results per page
            params["start"] = next_start

            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])

            if not local_results:
                break  # No more results

            logger.info(f"SerpAPI page {page}: {len(local_results)} results")

            for place in local_results:
                lead = _parse_place(place)
                if lead:
                    leads.append(lead)

                if len(leads) >= MAX_RESULTS_PER_SEARCH:
                    break

            page += 1

            # Safety: max 5 pages
            if page > 5:
                break

    except Exception as e:
        logger.error(f"SerpAPI search error: {e}", exc_info=True)

    return leads


def _parse_place(place: dict) -> Optional[dict]:
    """Parse a single SerpAPI place result into our lead format."""
    try:
        company_name = place.get("title", "").strip()
        if not company_name:
            return None

        address = place.get("address", "")
        city = ""
        state = ""

        # Extract city/state from address
        if address:
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 2:
                # Last part is usually "State ZIP" or just state
                state_part = parts[-1].strip()
                state_match = re.match(r"([A-Z]{2})\s*\d*", state_part)
                if state_match:
                    state = state_match.group(1)
                # Second to last is usually city
                city = parts[-2].strip() if len(parts) >= 2 else ""
                # If only 2 parts, first part is the street, city might be missing
                if len(parts) == 2:
                    city = parts[0].strip()

        # Get GPS coordinates for reference
        gps = place.get("gps_coordinates", {})

        lead = {
            "company_name": company_name,
            "website": place.get("website", ""),
            "phone": place.get("phone", ""),
            "email": "",  # Will be filled by email scraper
            "address": address,
            "city": city,
            "state": state,
            "rating": str(place.get("rating", "")),
            "reviews": str(place.get("reviews", "")),
            "category": place.get("type", "") or ", ".join(place.get("types", [])[:3]),
            "social_links": {},
            "place_id": place.get("place_id", ""),
            "thumbnail": place.get("thumbnail", ""),
        }

        return lead

    except Exception as e:
        logger.warning(f"Error parsing place '{place.get('title', '?')}': {e}")
        return None
