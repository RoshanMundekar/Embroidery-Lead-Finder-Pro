"""
Embroidery Lead Finder Pro — Main FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import APP_NAME, SECRET_KEY, RATE_LIMIT, ensure_data_dirs
from app.utils.logger import logger

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    ensure_data_dirs()
    logger.info(f"{APP_NAME} started successfully")
    yield
    # Shutdown
    logger.info(f"{APP_NAME} shutting down")


# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description="Lead generation tool for embroidery digitizing businesses",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Import and include routers
from app.routers import (
    dashboard_router,
    search_router,
    leads_router,
    download_router,
    analytics_router,
    settings_router,
)

app.include_router(dashboard_router.router, tags=["Dashboard"])
app.include_router(search_router.router, tags=["Search"])
app.include_router(leads_router.router, tags=["Leads"])
app.include_router(download_router.router, tags=["Downloads"])
app.include_router(analytics_router.router, tags=["Analytics"])
app.include_router(settings_router.router, tags=["Settings"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred. Please try again."},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
