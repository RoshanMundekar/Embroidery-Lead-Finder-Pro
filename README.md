# Embroidery Lead Finder Pro

A production-ready FastAPI web application for embroidery digitizing lead generation. Searches USA-based custom embroidery and apparel companies, scrapes leads from Google Maps, extracts emails from company websites, and stores everything in JSON files.

## Features

- **Google Maps Scraping SERPAPI_API_KEY** — Find embroidery & apparel companies via Playwright browser automation
- **Email Extraction** — Automatically visit websites and extract emails from contact/about pages
- **JSON File Storage** — No database required; all data stored in local JSON files
- **Export System** — Download leads as JSON, CSV, or Excel files
- **Dark SaaS Dashboard** — Modern analytics dashboard with TailwindCSS
- **Search & Filter** — Advanced lead table with sorting, pagination, and filtering

## Tech Stack

- FastAPI + Uvicorn
- Jinja2 Templates + TailwindCSS
- Playwright (headless Chromium)
- BeautifulSoup4 + httpx
- Pandas + openpyxl

## Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd Webscaping

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Copy environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Run the app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open: [http://localhost:8000](http://localhost:8000)

### Docker

```bash
# Copy environment file
copy .env.example .env

# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f
```

## Project Structure

```
app/
├── main.py              # FastAPI entry point
├── config.py            # Settings & env config
├── routers/             # API route handlers
│   ├── dashboard_router.py
│   ├── search_router.py
│   ├── leads_router.py
│   ├── download_router.py
│   ├── analytics_router.py
│   └── settings_router.py
├── services/            # Business logic
│   ├── google_scraper.py
│   ├── email_scraper.py
│   └── export_service.py
├── utils/               # Helpers
│   ├── file_storage.py
│   ├── user_agents.py
│   └── logger.py
├── templates/           # Jinja2 HTML templates
└── static/              # CSS & JS
data/
├── searches/            # Search logs (JSON)
├── leads/               # Scraped leads (JSON)
├── exports/             # Generated export files
└── logs/                # Application logs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard |
| GET | `/search` | Search page |
| POST | `/api/search` | Execute search |
| GET | `/leads` | Leads table |
| GET | `/api/leads` | Leads API (paginated) |
| GET | `/downloads` | Downloads page |
| GET | `/download/json/{id}` | Download JSON |
| GET | `/download/csv/{id}` | Download CSV |
| GET | `/download/xlsx/{id}` | Download Excel |
| GET | `/api/analytics` | Analytics data |
| GET | `/settings` | Settings page |
| POST | `/api/settings` | Update settings |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | App secret key |
| `SCRAPE_DELAY_MIN` | `2` | Minimum delay between requests (s) |
| `SCRAPE_DELAY_MAX` | `5` | Maximum delay between requests (s) |
| `MAX_RESULTS_PER_SEARCH` | `20` | Max results per search |
| `SERPAPI_API_KEY` | — | Optional SERPAPI_API_KEY |

## License

MIT
