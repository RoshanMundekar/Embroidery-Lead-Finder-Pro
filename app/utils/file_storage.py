"""
JSON file storage — read/write leads, searches, and settings to local JSON files.
"""

import json
import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import LEADS_DIR, SEARCHES_DIR, EXPORTS_DIR, DATA_DIR
from app.utils.logger import logger


async def save_leads(search_keyword: str, location: str, leads: list[dict]) -> str:
    """Save scraped leads to a JSON file. Returns the search_id."""
    search_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_{timestamp}_{search_id}.json"

    data = {
        "search_id": search_id,
        "search_keyword": search_keyword,
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "total_results": len(leads),
        "leads": leads,
    }

    filepath = LEADS_DIR / filename
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    logger.info(f"Saved {len(leads)} leads to {filename}")
    return search_id


async def save_search_log(
    search_keyword: str, location: str, total_results: int, search_id: str
) -> None:
    """Save search metadata to searches directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_{timestamp}_{search_id}.json"

    data = {
        "search_id": search_id,
        "search_keyword": search_keyword,
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "total_results": total_results,
    }

    filepath = SEARCHES_DIR / filename
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    logger.info(f"Logged search: '{search_keyword}' in '{location}' — {total_results} results")


def load_all_leads() -> list[dict]:
    """Load and merge all lead files. Returns flat list of lead entries with search metadata."""
    all_leads = []
    if not LEADS_DIR.exists():
        return all_leads

    for file in sorted(LEADS_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for lead in data.get("leads", []):
                    lead["_search_id"] = data.get("search_id", "")
                    lead["_search_keyword"] = data.get("search_keyword", "")
                    lead["_search_location"] = data.get("location", "")
                    lead["_search_timestamp"] = data.get("timestamp", "")
                    all_leads.append(lead)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading lead file {file.name}: {e}")

    return all_leads


def load_all_searches() -> list[dict]:
    """Load all search log files."""
    searches = []
    if not SEARCHES_DIR.exists():
        return searches

    for file in sorted(SEARCHES_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                searches.append(json.load(f))
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading search file {file.name}: {e}")

    return searches


def load_lead_file(search_id: str) -> Optional[dict]:
    """Load a specific lead file by search_id."""
    if not LEADS_DIR.exists():
        return None

    for file in LEADS_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("search_id") == search_id:
                    return data
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading lead file {file.name}: {e}")

    return None


def load_all_lead_files() -> list[dict]:
    """Load all lead files as complete objects (with metadata)."""
    lead_files = []
    if not LEADS_DIR.exists():
        return lead_files

    for file in sorted(LEADS_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_filename"] = file.name
                lead_files.append(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error reading lead file {file.name}: {e}")

    return lead_files


def get_analytics_data() -> dict:
    """Compute analytics from all stored data."""
    leads = load_all_leads()
    searches = load_all_searches()
    lead_files = load_all_lead_files()

    # Total counts
    total_leads = len(leads)
    total_searches = len(searches)
    total_emails = sum(1 for lead in leads if lead.get("email"))

    # Email success rate
    email_rate = round((total_emails / total_leads * 100), 1) if total_leads > 0 else 0

    # Leads per state
    state_counts = {}
    for lead in leads:
        state = lead.get("state", "Unknown")
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
    # Sort by count descending, top 10
    top_states = dict(sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    # Most searched keywords
    keyword_counts = {}
    for search in searches:
        kw = search.get("search_keyword", "")
        if kw:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
    top_keywords = dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    # Daily stats (last 7 days)
    daily_stats = {}
    for search in searches:
        ts = search.get("timestamp", "")
        if ts:
            day = ts[:10]  # YYYY-MM-DD
            if day not in daily_stats:
                daily_stats[day] = {"searches": 0, "leads": 0}
            daily_stats[day]["searches"] += 1
            daily_stats[day]["leads"] += search.get("total_results", 0)
    # Sort and take last 7
    daily_stats = dict(sorted(daily_stats.items(), reverse=True)[:7])

    # Recent searches (last 10)
    recent_searches = searches[:10]

    return {
        "total_leads": total_leads,
        "total_searches": total_searches,
        "total_emails": total_emails,
        "email_rate": email_rate,
        "top_states": top_states,
        "top_keywords": top_keywords,
        "daily_stats": daily_stats,
        "recent_searches": recent_searches,
    }


def load_settings() -> dict:
    """Load application settings from JSON file."""
    settings_file = DATA_DIR / "settings.json"
    defaults = {
        "scrape_delay_min": 2,
        "scrape_delay_max": 5,
        "max_results": 20,
        "request_timeout": 30,
        "email_timeout": 15,
        "user_agent_rotation": True,
    }
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(settings: dict) -> None:
    """Save application settings to JSON file."""
    settings_file = DATA_DIR / "settings.json"
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def get_export_files() -> list[dict]:
    """List all export files with metadata."""
    files = []
    if not EXPORTS_DIR.exists():
        return files

    for file in sorted(EXPORTS_DIR.iterdir(), reverse=True):
        if file.is_file():
            stat = file.stat()
            files.append({
                "filename": file.name,
                "size": stat.st_size,
                "size_display": _format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "format": file.suffix.lstrip(".").upper(),
            })
    return files


def _format_size(size_bytes: int) -> str:
    """Format file size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
