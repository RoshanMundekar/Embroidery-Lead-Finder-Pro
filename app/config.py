"""
Configuration module — loads settings from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")

# App settings
APP_NAME = os.getenv("APP_NAME", "Embroidery Lead Finder Pro")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-abc123")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Scraping settings
SCRAPE_DELAY_MIN = int(os.getenv("SCRAPE_DELAY_MIN", "2"))
SCRAPE_DELAY_MAX = int(os.getenv("SCRAPE_DELAY_MAX", "5"))
MAX_RESULTS_PER_SEARCH = int(os.getenv("MAX_RESULTS_PER_SEARCH", "20"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
EMAIL_SCRAPE_TIMEOUT = int(os.getenv("EMAIL_SCRAPE_TIMEOUT", "15"))

# Rate limiting
RATE_LIMIT = os.getenv("RATE_LIMIT", "10/minute")

# SerpAPI (Google Maps Search)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Data subdirectories
SEARCHES_DIR = DATA_DIR / "searches"
LEADS_DIR = DATA_DIR / "leads"
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = DATA_DIR / "logs"


def ensure_data_dirs():
    """Create all required data directories if they don't exist."""
    for directory in [SEARCHES_DIR, LEADS_DIR, EXPORTS_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
