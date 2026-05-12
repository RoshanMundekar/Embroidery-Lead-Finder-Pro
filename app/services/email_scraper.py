"""
Email scraper — visits company websites and extracts emails + social media links.
Checks homepage, contact page, about page, and footer.
"""

import asyncio
import re
from urllib.parse import urljoin, urlparse
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import EMAIL_SCRAPE_TIMEOUT
from app.utils.user_agents import get_random_user_agent
from app.utils.logger import logger

# Email regex
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Common false positive emails to filter out
FALSE_POSITIVE_EMAILS = {
    "example@email.com",
    "example@example.com",
    "email@example.com",
    "name@email.com",
    "your@email.com",
    "info@example.com",
    "test@test.com",
    "user@example.com",
    "yourname@domain.com",
    "someone@example.com",
}

# File extensions that look like emails but aren't
FALSE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js", ".woff", ".woff2", ".ttf"}

# Social media patterns
SOCIAL_PATTERNS = {
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'>]+", re.IGNORECASE),
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[^\s\"'>]+", re.IGNORECASE),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[^\s\"'>]+", re.IGNORECASE),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\"'>]+", re.IGNORECASE),
    "youtube": re.compile(r"https?://(?:www\.)?youtube\.com/[^\s\"'>]+", re.IGNORECASE),
    "tiktok": re.compile(r"https?://(?:www\.)?tiktok\.com/@[^\s\"'>]+", re.IGNORECASE),
}

# Contact page URL patterns
CONTACT_PAGE_PATTERNS = [
    "/contact", "/contact-us", "/contactus", "/get-in-touch",
    "/about", "/about-us", "/aboutus",
    "/reach-us", "/connect", "/support",
]


async def extract_emails_from_website(website_url: str) -> dict:
    """
    Visit a website, find contact/about pages, extract emails and social links.
    Returns {"emails": [...], "social_links": {...}}
    """
    result = {"emails": [], "social_links": {}}

    if not website_url:
        return result

    # Normalize URL
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    try:
        async with httpx.AsyncClient(
            timeout=EMAIL_SCRAPE_TIMEOUT,
            follow_redirects=True,
            verify=False,
            headers=headers,
        ) as client:
            all_emails = set()
            all_social = {}

            # 1. Scrape homepage
            homepage_html = await _fetch_page(client, website_url)
            if homepage_html:
                emails, social = _extract_from_html(homepage_html, website_url)
                all_emails.update(emails)
                all_social.update(social)

                # 2. Find and scrape contact/about pages
                contact_urls = _find_contact_pages(homepage_html, website_url)
                for url in contact_urls[:3]:  # Limit to 3 sub-pages
                    await asyncio.sleep(0.5)  # Be polite
                    page_html = await _fetch_page(client, url)
                    if page_html:
                        emails, social = _extract_from_html(page_html, website_url)
                        all_emails.update(emails)
                        all_social.update(social)

            result["emails"] = list(all_emails)
            result["social_links"] = all_social

    except Exception as e:
        logger.warning(f"Email extraction failed for {website_url}: {e}")

    return result


async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Fetch a page and return its HTML content."""
    try:
        response = await client.get(url)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
    return None


def _extract_from_html(html: str, base_url: str) -> tuple[set, dict]:
    """Extract emails and social links from HTML content."""
    emails = set()
    social_links = {}

    soup = BeautifulSoup(html, "lxml")

    # Remove script and style tags to reduce false positives
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    page_str = str(soup)

    # Extract emails from text
    found_emails = EMAIL_REGEX.findall(text)
    # Also search in href="mailto:" attributes
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if EMAIL_REGEX.match(email):
                found_emails.append(email)

    # Filter valid emails
    for email in found_emails:
        email = email.lower().strip()
        if _is_valid_email(email):
            emails.add(email)

    # Extract social media links
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(page_str)
        if matches:
            # Clean up the URL
            social_url = matches[0].rstrip('"').rstrip("'").rstrip("/")
            social_links[platform] = social_url

    return emails, social_links


def _is_valid_email(email: str) -> bool:
    """Validate email and filter out false positives."""
    if email in FALSE_POSITIVE_EMAILS:
        return False

    # Check for file extensions masquerading as emails
    for ext in FALSE_EXTENSIONS:
        if email.endswith(ext):
            return False

    # Filter out very long or suspicious emails
    if len(email) > 80:
        return False

    # Filter out emails with common placeholder domains
    domain = email.split("@")[1] if "@" in email else ""
    if domain in {"example.com", "test.com", "email.com", "domain.com", "yoursite.com", "website.com", "sentry.io", "sentry-next.wixpress.com"}:
        return False

    return True


def _find_contact_pages(html: str, base_url: str) -> list[str]:
    """Find links to contact and about pages."""
    soup = BeautifulSoup(html, "lxml")
    contact_urls = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower().strip()
        text = (a_tag.get_text() or "").lower().strip()

        # Check if the link text or URL matches contact page patterns
        is_contact = False

        for pattern in CONTACT_PAGE_PATTERNS:
            if pattern in href or pattern.replace("-", " ").replace("/", "") in text:
                is_contact = True
                break

        # Also check text content
        if any(word in text for word in ["contact", "about", "reach", "get in touch"]):
            is_contact = True

        if is_contact:
            full_url = urljoin(base_url, a_tag["href"])
            # Only include URLs from the same domain
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                if full_url not in contact_urls:
                    contact_urls.append(full_url)

    return contact_urls


async def batch_extract_emails(leads: list[dict]) -> list[dict]:
    """Extract emails for a batch of leads concurrently (limited concurrency)."""
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

    async def extract_with_limit(lead: dict) -> dict:
        async with semaphore:
            website = lead.get("website", "")
            if website and not lead.get("email"):
                result = await extract_emails_from_website(website)
                if result["emails"]:
                    lead["email"] = result["emails"][0]  # Primary email
                if result["social_links"]:
                    lead["social_links"] = result["social_links"]
                # Small delay between requests
                await asyncio.sleep(0.5)
            return lead

    tasks = [extract_with_limit(lead) for lead in leads]
    return await asyncio.gather(*tasks)
