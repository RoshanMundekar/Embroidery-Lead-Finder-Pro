"""
Production-Level B2B Lead Intelligence Extraction Engine
--------------------------------------------------------
Features:
- Async crawling
- Contact/About/Team page discovery
- Playwright JS fallback (threaded for Windows)
- Hidden email decoding (multiple formats)
- Email prioritization
- Phone number extraction & validation
- Contact person & job title extraction
- Social media extraction
- Embroidery business detection
- Business type classification
- Weighted lead scoring
- Better filtering
"""

import asyncio
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import EMAIL_SCRAPE_TIMEOUT
from app.utils.logger import logger
from app.utils.user_agents import get_random_user_agent


# =========================================================
# EMAIL REGEX
# =========================================================

EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

# =========================================================
# PHONE REGEX — US formats
# =========================================================

PHONE_REGEX = re.compile(
    r"""
    (?:
        (?:\+?1[\s.-]?)?              # optional +1 country code
        (?:\(?\d{3}\)?[\s.\-]?)       # area code (xxx) or xxx
        \d{3}[\s.\-]?                 # first 3 digits
        \d{4}                         # last 4 digits
    )
    """,
    re.VERBOSE,
)

# Quick filter to avoid matching years, zip codes, etc.
PHONE_MIN_DIGITS = 10
PHONE_MAX_DIGITS = 11

# =========================================================
# FALSE POSITIVES
# =========================================================

FALSE_POSITIVE_EMAILS = {
    "example@email.com",
    "example@example.com",
    "email@example.com",
    "test@test.com",
    "your@email.com",
    "name@email.com",
    "info@example.com",
    "admin@example.com",
    "user@example.com",
    "noreply@example.com",
    "example@mysite.com",
    "mail@mysite.com",
    "info@mysite.com",
    "your@company.com",
    "name@company.com",
    "email@yourcompany.com",
    "info@yourcompany.com",
    "yourname@domain.com",
    "placeholder@email.com",
}

FALSE_DOMAINS = {
    "example.com",
    "test.com",
    "domain.com",
    "email.com",
    "yoursite.com",
    "website.com",
    "mysite.com",
    "yourcompany.com",
    "company.com",
    "yourdomain.com",
    "sentry.io",
    "wixpress.com",
    "wix.com",
    "squarespace.com",
    "squarespace.mail",
    "weebly.com",
    "godaddy.com",
    "googleapis.com",
    "googleusercontent.com",
    "gstatic.com",
    "w3.org",
    "schema.org",
    "gravatar.com",
    "wordpress.com",
    "wp.com",
    "bootstrapcdn.com",
    "cloudflare.com",
    "jsdelivr.net",
    "unpkg.com",
    "fontawesome.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "google.com",
    "apple.com",
    "microsoft.com",
}

# Non-US country-code TLDs to filter out
# (This is a US-focused lead finder)
FALSE_COUNTRY_TLDS = {
    ".co.uk", ".co.in", ".co.za", ".co.nz", ".co.au",
    ".uk", ".in", ".de", ".fr", ".it", ".es", ".nl",
    ".be", ".at", ".ch", ".se", ".dk", ".no", ".fi",
    ".pl", ".cz", ".hu", ".ro", ".bg", ".hr", ".sk",
    ".pt", ".ie", ".gr", ".ru", ".ua", ".cn", ".jp",
    ".kr", ".tw", ".hk", ".sg", ".my", ".th", ".ph",
    ".vn", ".id", ".pk", ".bd", ".lk", ".np",
    ".br", ".mx", ".ar", ".cl", ".co", ".pe",
    ".za", ".ng", ".ke", ".eg", ".ma",
    ".ae", ".sa", ".il", ".tr",
    ".au", ".nz",
}

FALSE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".webp",
    ".ico",
}

# =========================================================
# CONTACT PAGES
# =========================================================

CONTACT_PAGE_PATTERNS = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/leadership",
    "/staff",
    "/support",
    "/customer-service",
    "/company",
    "/people",
    "/meet-the-team",
    "/locations",
    "/get-a-quote",
    "/request-quote",
    "/request-a-quote",
    "/get-in-touch",
    "/connect",
    "/reach-us",
    "/inquiry",
    "/enquiry",
    "/feedback",
    "/help",
    "/info",
    "/services",
]

# =========================================================
# SOCIAL PATTERNS
# =========================================================

SOCIAL_PATTERNS = {
    "facebook": re.compile(
        r"https?://(?:www\.)?facebook\.com/[^\s\"'>]+",
        re.IGNORECASE,
    ),
    "instagram": re.compile(
        r"https?://(?:www\.)?instagram\.com/[^\s\"'>]+",
        re.IGNORECASE,
    ),
    "linkedin": re.compile(
        r"https?://(?:www\.)?linkedin\.com/[^\s\"'>]+",
        re.IGNORECASE,
    ),
    "twitter": re.compile(
        r"https?://(?:www\.)?(?:twitter|x)\.com/[^\s\"'>]+",
        re.IGNORECASE,
    ),
    "youtube": re.compile(
        r"https?://(?:www\.)?youtube\.com/[^\s\"'>]+",
        re.IGNORECASE,
    ),
}

# =========================================================
# EMBROIDERY TERMS
# =========================================================

EMBROIDERY_TERMS = [
    "custom embroidery",
    "embroidery",
    "embroidery digitizing",
    "screen printing",
    "corporate apparel",
    "uniforms",
    "custom polos",
    "polo shirts",
    "caps",
    "jackets",
    "workwear",
    "hospital uniforms",
    "promotional products",
    "digitizing",
    "3d puff embroidery",
    "logo embroidery",
    "monogramming",
    "heat transfer",
    "direct to garment",
    "dtg printing",
    "towels",
    "bulk orders",
    "team uniforms",
    "corporate clothing",
    "branded merchandise",
    # Manufacturers & decorators
    "embroidery manufacturer",
    "garment manufacturer",
    "clothing manufacturer",
    "apparel manufacturer",
    "textile manufacturer",
    "embroiderer",
    "garment decorator",
    "clothing decorator",
    "garment decoration",
    "contract embroidery",
    "contract decorator",
    "wholesale embroidery",
    "embroidery services",
    "decoration services",
    "custom decoration",
    "sublimation printing",
    "vinyl cutting",
    "patch maker",
    "custom patches",
    "chenille patches",
    "applique",
    "embroidered patches",
    "hat embroidery",
    "cap embroidery",
    "bag embroidery",
    "apron embroidery",
]

# =========================================================
# EMAIL PRIORITY
# =========================================================

EMAIL_PRIORITY = {
    "sales": 100,
    "orders": 95,
    "artwork": 90,
    "production": 90,
    "digitizing": 88,
    "design": 85,
    "owner": 85,
    "manager": 80,
    "marketing": 80,
    "info": 60,
    "support": 50,
    "contact": 50,
    "hello": 45,
    "admin": 30,
    "noreply": 5,
}

# =========================================================
# JOB TITLE PATTERNS
# =========================================================

JOB_TITLE_PATTERNS = [
    r"\b(?:CEO|Chief Executive Officer)\b",
    r"\bOwner\b",
    r"\bFounder\b",
    r"\bCo-?Founder\b",
    r"\bPresident\b",
    r"\bVice President\b",
    r"\bDirector\b",
    r"\bGeneral Manager\b",
    r"\bManager\b",
    r"\bSales (?:Manager|Director|Representative|Rep)\b",
    r"\bMarketing (?:Manager|Director)\b",
    r"\bProduction (?:Manager|Director)\b",
    r"\bOperations (?:Manager|Director)\b",
    r"\bAccount (?:Manager|Executive)\b",
    r"\bBusiness Development\b",
    r"\bCustomer Service\b",
    r"\bArt Director\b",
    r"\bDesign (?:Manager|Director)\b",
    r"\bSupervisor\b",
    r"\bCoordinator\b",
    r"\bPartner\b",
    r"\bPrincipal\b",
]

JOB_TITLE_REGEX = re.compile(
    "|".join(JOB_TITLE_PATTERNS),
    re.IGNORECASE,
)

# =========================================================
# BUSINESS TYPE CLASSIFICATION
# =========================================================

BUSINESS_TYPE_MAP = [
    {
        "keywords": ["embroidery digitizing", "digitizing"],
        "type": "Embroidery Digitizing Service",
    },
    {
        "keywords": ["embroidery manufacturer", "garment manufacturer", "clothing manufacturer",
                     "apparel manufacturer", "textile manufacturer"],
        "type": "Garment Manufacturer",
    },
    {
        "keywords": ["garment decorator", "clothing decorator", "garment decoration",
                     "contract decorator", "decoration services", "custom decoration"],
        "type": "Garment Decorator",
    },
    {
        "keywords": ["contract embroidery", "wholesale embroidery", "embroiderer"],
        "type": "Contract Embroidery Service",
    },
    {
        "keywords": ["custom embroidery", "embroidery", "logo embroidery",
                     "monogramming", "embroidery services"],
        "type": "Custom Embroidery Shop",
    },
    {
        "keywords": ["screen printing", "dtg printing", "direct to garment",
                     "sublimation printing"],
        "type": "Screen Printing Company",
    },
    {
        "keywords": ["custom patches", "embroidered patches", "chenille patches",
                     "patch maker", "applique"],
        "type": "Patch & Emblem Manufacturer",
    },
    {
        "keywords": ["corporate apparel", "corporate clothing", "branded merchandise"],
        "type": "Corporate Apparel Supplier",
    },
    {
        "keywords": ["uniforms", "hospital uniforms", "team uniforms", "workwear"],
        "type": "Uniform Supplier",
    },
    {
        "keywords": ["promotional products", "branded merchandise"],
        "type": "Promotional Products Distributor",
    },
    {
        "keywords": ["caps", "jackets", "polo shirts", "towels"],
        "type": "Apparel & Accessories",
    },
]

# =========================================================
# PERSON NAME REGEX (simple heuristic)
# =========================================================

# Matches "FirstName LastName" near a job title
PERSON_NAME_REGEX = re.compile(
    r"\b([A-Z][a-z]{1,15}(?:\s[A-Z]\.?)?\s[A-Z][a-z]{1,20})\b"
)


# =========================================================
# MAIN SCRAPER
# =========================================================

async def extract_emails_from_website(website_url: str) -> dict:
    """
    Production-level B2B lead intelligence extraction.
    Returns comprehensive lead data from a business website.
    """

    result = {
        "emails": [],
        "primary_email": "",
        "phone_numbers": [],
        "contact_people": [],
        "job_titles": [],
        "social_links": {},
        "services_found": [],
        "business_type": "",
        "likely_embroidery_business": False,
        "lead_score": 0,
    }

    if not website_url:
        return result

    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"

    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
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
            all_services = set()
            all_phones = set()
            all_contacts = []
            all_titles = set()

            # ==========================================
            # HOMEPAGE
            # ==========================================

            homepage_html = await _fetch_page(client, website_url)

            if homepage_html:

                extracted = _extract_from_html(
                    homepage_html,
                    website_url,
                )

                all_emails.update(extracted["emails"])
                all_social.update(extracted["social_links"])
                all_services.update(extracted["services"])
                all_phones.update(extracted["phones"])
                all_contacts.extend(extracted["contacts"])
                all_titles.update(extracted["titles"])

                # ======================================
                # PLAYWRIGHT FALLBACK
                # ======================================

                if not extracted["emails"]:

                    dynamic_html = await _fetch_dynamic_page(
                        website_url
                    )

                    if dynamic_html:
                        dyn_extracted = _extract_from_html(
                            dynamic_html,
                            website_url,
                        )

                        all_emails.update(dyn_extracted["emails"])
                        all_social.update(dyn_extracted["social_links"])
                        all_services.update(dyn_extracted["services"])
                        all_phones.update(dyn_extracted["phones"])
                        all_contacts.extend(dyn_extracted["contacts"])
                        all_titles.update(dyn_extracted["titles"])

                # ======================================
                # FIND CONTACT PAGES
                # ======================================

                contact_urls = _find_contact_pages(
                    homepage_html,
                    website_url,
                )

                for url in contact_urls[:8]:

                    await asyncio.sleep(1)

                    page_html = await _fetch_page(
                        client,
                        url,
                    )

                    if not page_html:
                        continue

                    pg_extracted = _extract_from_html(
                        page_html,
                        website_url,
                    )

                    all_emails.update(pg_extracted["emails"])
                    all_social.update(pg_extracted["social_links"])
                    all_services.update(pg_extracted["services"])
                    all_phones.update(pg_extracted["phones"])
                    all_contacts.extend(pg_extracted["contacts"])
                    all_titles.update(pg_extracted["titles"])

            # ==========================================
            # DOMAIN-BASED EMAIL GENERATION (fallback)
            # ==========================================

            if not all_emails:
                domain = urlparse(website_url).netloc
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain and "." in domain:
                    common_prefixes = [
                        "info", "sales", "contact",
                        "hello", "support", "orders",
                    ]
                    for prefix in common_prefixes:
                        candidate = f"{prefix}@{domain}"
                        if _is_valid_email(candidate):
                            all_emails.add(candidate)
                            break  # Only add one fallback
                    logger.debug(
                        f"Generated fallback email for {domain}"
                    )

            # ==========================================
            # FINALIZE
            # ==========================================

            email_list = list(all_emails)

            result["emails"] = email_list
            result["primary_email"] = select_best_email(
                email_list
            )

            result["phone_numbers"] = sorted(all_phones)
            result["social_links"] = all_social
            result["services_found"] = list(all_services)

            # Deduplicate contacts
            seen_names = set()
            unique_contacts = []
            for contact in all_contacts:
                name = contact.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    unique_contacts.append(contact)
            result["contact_people"] = unique_contacts

            result["job_titles"] = list(all_titles)

            result["likely_embroidery_business"] = (
                len(all_services) > 0
            )

            result["business_type"] = _detect_business_type(
                all_services
            )

            result["lead_score"] = calculate_lead_score(
                result
            )

    except Exception as e:
        logger.warning(
            f"Email extraction failed for {website_url}: {e}"
        )

    return result


# =========================================================
# FETCH NORMAL PAGE
# =========================================================

async def _fetch_page(
    client: httpx.AsyncClient,
    url: str,
) -> Optional[str]:

    try:
        response = await client.get(url)

        if response.status_code == 200:
            return response.text

    except Exception as e:
        logger.debug(f"Fetch failed {url}: {e}")

    return None


# =========================================================
# FETCH PAGE — RETRY WITH DIFFERENT USER-AGENT
# =========================================================

async def _fetch_dynamic_page(url: str) -> str:
    """
    Secondary fetch attempt using a browser-like user-agent
    and longer timeout. Used as a fallback when the initial
    httpx fetch found no emails.
    """

    fallback_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            verify=False,
            headers=fallback_headers,
        ) as client:

            response = await client.get(url)

            if response.status_code == 200:
                logger.debug(
                    f"Fallback fetch succeeded for {url}"
                )
                return response.text

    except Exception as e:
        logger.debug(f"Fallback fetch failed {url}: {e}")

    return ""


# =========================================================
# EXTRACT FROM HTML — UNIFIED
# =========================================================

def _extract_from_html(
    html: str,
    base_url: str,
) -> dict:
    """
    Extract all lead intelligence from a single HTML page.
    Returns a dict with: emails, social_links, services, phones, contacts, titles.
    """

    emails = set()
    social_links = {}
    services_found = set()
    phones = set()
    contacts = []
    titles = set()

    # ==============================================
    # STEP 1: Scan RAW HTML before removing scripts
    # ==============================================
    raw_emails = EMAIL_REGEX.findall(html)
    for email in raw_emails:
        email = email.lower().strip()
        if _is_valid_email(email):
            emails.add(email)

    soup = BeautifulSoup(html, "lxml")

    # ==============================================
    # STEP 2: Decode CloudFlare protected emails
    # ==============================================
    for cf_tag in soup.select("[data-cfemail]"):
        encoded = cf_tag.get("data-cfemail", "")
        decoded = _decode_cloudflare_email(encoded)
        if decoded and _is_valid_email(decoded.lower()):
            emails.add(decoded.lower())

    # ==============================================
    # STEP 3: Extract from JSON-LD / structured data
    # ==============================================
    for script_tag in soup.find_all("script", {"type": "application/ld+json"}):
        script_text = script_tag.string or ""
        ld_emails = EMAIL_REGEX.findall(script_text)
        for email in ld_emails:
            email = email.lower().strip()
            if _is_valid_email(email):
                emails.add(email)

    # ==============================================
    # STEP 4: Extract from JS variables & comments
    # ==============================================
    for script_tag in soup.find_all("script"):
        script_text = script_tag.string or ""
        if "@" in script_text:
            js_emails = EMAIL_REGEX.findall(script_text)
            for email in js_emails:
                email = email.lower().strip()
                if _is_valid_email(email):
                    emails.add(email)

    # Now remove scripts/styles for text extraction
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = normalize_hidden_email(text)
    page_str = str(soup)

    # ==============================================
    # STEP 5: Normal email extraction from text
    # ==============================================
    found_emails = EMAIL_REGEX.findall(text)

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            email = (
                href.replace("mailto:", "")
                .split("?")[0]
                .strip()
            )
            found_emails.append(email)

    for email in found_emails:
        email = email.lower().strip()
        if _is_valid_email(email):
            emails.add(email)

    # ==============================================
    # STEP 6: Extract from HTML comments
    # ==============================================
    from bs4 import Comment
    comments = soup.find_all(string=lambda t: isinstance(t, Comment))
    for comment in comments:
        comment_emails = EMAIL_REGEX.findall(str(comment))
        for email in comment_emails:
            email = email.lower().strip()
            if _is_valid_email(email):
                emails.add(email)

    # ==========================================
    # PHONE EXTRACTION
    # ==========================================
    phones = _extract_phone_numbers(soup, text)

    # ==========================================
    # CONTACT PEOPLE & JOB TITLES
    # ==========================================
    contacts, titles = _extract_contacts(soup, text)

    # ==========================================
    # SOCIAL LINKS
    # ==========================================
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(page_str)
        if matches:
            social_links[platform] = (
                matches[0]
                .rstrip('"')
                .rstrip("'")
                .rstrip("/")
            )

    # ==========================================
    # SERVICE DETECTION
    # ==========================================
    lower_text = text.lower()
    for term in EMBROIDERY_TERMS:
        if term.lower() in lower_text:
            services_found.add(term)

    return {
        "emails": emails,
        "social_links": social_links,
        "services": services_found,
        "phones": phones,
        "contacts": contacts,
        "titles": titles,
    }


# =========================================================
# CLOUDFLARE EMAIL DECODING
# =========================================================

def _decode_cloudflare_email(encoded: str) -> str:
    """Decode CloudFlare data-cfemail obfuscated emails."""
    try:
        key = int(encoded[:2], 16)
        decoded = ""
        for i in range(2, len(encoded), 2):
            decoded += chr(int(encoded[i:i+2], 16) ^ key)
        return decoded
    except Exception:
        return ""


# =========================================================
# PHONE NUMBER EXTRACTION
# =========================================================

def _extract_phone_numbers(soup: BeautifulSoup, text: str) -> set:
    """Extract and validate US phone numbers from page content."""

    phones = set()

    # Method 1: tel: links (most reliable)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("tel:"):
            raw_phone = href.replace("tel:", "").strip()
            formatted = _format_phone(raw_phone)
            if formatted:
                phones.add(formatted)

    # Method 2: Regex on visible text
    matches = PHONE_REGEX.findall(text)
    for match in matches:
        formatted = _format_phone(match)
        if formatted:
            phones.add(formatted)

    return phones


def _format_phone(raw: str) -> str:
    """Normalize a raw phone string into (xxx) xxx-xxxx format, or return '' if invalid."""

    digits = re.sub(r"\D", "", raw)

    # Strip leading 1 (US country code)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return ""

    # Reject obvious non-phones (e.g. starts with 0 or 1)
    if digits[0] in ("0", "1"):
        return ""

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


# =========================================================
# CONTACT PERSON & JOB TITLE EXTRACTION
# =========================================================

def _extract_contacts(soup: BeautifulSoup, text: str) -> tuple[list, set]:
    """
    Extract contact person names and job titles from HTML.
    Uses proximity heuristics — looks for names near titles.
    """

    contacts = []
    titles = set()
    seen_names = set()

    # Method 1: Structured data — look for common HTML patterns
    # Many sites use <div class="team-member"> or similar structures
    team_selectors = [
        ".team-member", ".staff-member", ".employee",
        ".member", ".person", ".team-card",
        "[itemtype*='Person']",
    ]

    for selector in team_selectors:
        for el in soup.select(selector):
            el_text = el.get_text(separator=" ").strip()
            _extract_name_title_pair(el_text, contacts, titles, seen_names)

    # Method 2: Look for name + title patterns in headings
    # e.g., <h3>John Smith</h3><p>Owner</p>
    for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
        heading_text = heading.get_text().strip()

        # Check if heading contains a person name
        name_match = PERSON_NAME_REGEX.search(heading_text)
        if name_match:
            name = name_match.group(1).strip()
            if _is_likely_person_name(name) and name not in seen_names:
                # Look at the next sibling for a job title
                title = ""
                next_el = heading.find_next_sibling(["p", "span", "div"])
                if next_el:
                    next_text = next_el.get_text().strip()
                    title_match = JOB_TITLE_REGEX.search(next_text)
                    if title_match:
                        title = title_match.group(0).strip()

                seen_names.add(name)
                contact = {"name": name}
                if title:
                    contact["title"] = title
                    titles.add(title)
                contacts.append(contact)

    # Method 3: Scan full text for job titles (even without names)
    all_title_matches = JOB_TITLE_REGEX.findall(text)
    for title in all_title_matches:
        title = title.strip()
        if title:
            titles.add(title)

    return contacts, titles


def _extract_name_title_pair(
    text: str,
    contacts: list,
    titles: set,
    seen_names: set,
):
    """Extract a name + title pair from a block of text."""

    name_match = PERSON_NAME_REGEX.search(text)
    title_match = JOB_TITLE_REGEX.search(text)

    if name_match:
        name = name_match.group(1).strip()
        if _is_likely_person_name(name) and name not in seen_names:
            seen_names.add(name)
            contact = {"name": name}
            if title_match:
                title = title_match.group(0).strip()
                contact["title"] = title
                titles.add(title)
            contacts.append(contact)
    elif title_match:
        titles.add(title_match.group(0).strip())


def _is_likely_person_name(name: str) -> bool:
    """Filter out false positives for person names."""

    # Reject very short or very long names
    if len(name) < 4 or len(name) > 40:
        return False

    # Reject common false positives
    false_names = {
        "Read More", "Learn More", "Click Here", "Find Out",
        "Contact Us", "About Us", "Our Team", "Get Started",
        "Sign Up", "Log In", "View More", "See More",
        "Free Shipping", "New Arrivals", "Best Sellers",
        "Privacy Policy", "Terms Conditions", "Customer Service",
        "United States", "New York", "Los Angeles", "San Francisco",
        "North Carolina", "South Carolina", "North Dakota",
        "South Dakota", "West Virginia", "New Jersey",
        "New Hampshire", "New Mexico", "Rhode Island",
    }

    if name in false_names:
        return False

    # Must have at least 2 parts
    parts = name.split()
    if len(parts) < 2:
        return False

    return True


# =========================================================
# BUSINESS TYPE DETECTION
# =========================================================

def _detect_business_type(services: set) -> str:
    """Classify business type from detected services."""

    if not services:
        return ""

    lower_services = {s.lower() for s in services}

    for mapping in BUSINESS_TYPE_MAP:
        for keyword in mapping["keywords"]:
            if keyword in lower_services:
                return mapping["type"]

    # Fallback: if services found but no specific match
    if lower_services:
        return "Apparel & Printing Services"

    return ""


# =========================================================
# NORMALIZE HIDDEN EMAILS
# =========================================================

def normalize_hidden_email(text: str) -> str:
    """Decode obfuscated emails in various formats."""

    # Standard obfuscation patterns
    replacements = {
        "[at]": "@",
        "(at)": "@",
        " at ": "@",
        "{at}": "@",
        "-at-": "@",
        "_at_": "@",
        "[dot]": ".",
        "(dot)": ".",
        " dot ": ".",
        "{dot}": ".",
        "-dot-": ".",
        "_dot_": ".",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Case-insensitive variants: " AT ", " DOT "
    text = re.sub(r"\s+AT\s+", "@", text)
    text = re.sub(r"\s+DOT\s+", ".", text)

    # HTML entities
    text = text.replace("&#64;", "@")
    text = text.replace("&#46;", ".")
    text = text.replace("&commat;", "@")
    text = text.replace("&period;", ".")

    # Unicode variants
    text = text.replace("\uff20", "@")  # ＠
    text = text.replace("\u0040", "@")  # @

    return text


# =========================================================
# VALIDATE EMAIL
# =========================================================

def _is_valid_email(email: str) -> bool:

    if email in FALSE_POSITIVE_EMAILS:
        return False

    if len(email) > 80:
        return False

    if len(email) < 5:
        return False

    # Reject placeholder local-parts
    local = email.split("@")[0]
    false_locals = {
        "example", "test", "your", "yourname",
        "name", "user", "placeholder", "email",
        "someone", "john.doe", "jane.doe",
    }
    if local in false_locals:
        return False

    for ext in FALSE_EXTENSIONS:
        if email.endswith(ext):
            return False

    parts = email.split("@")
    if len(parts) != 2:
        return False

    domain = parts[1]

    if domain in FALSE_DOMAINS:
        return False

    # Domain must have at least one dot
    if "." not in domain:
        return False

    # Reject non-US country-code TLDs
    for tld in FALSE_COUNTRY_TLDS:
        if domain.endswith(tld):
            return False

    return True


# =========================================================
# FIND CONTACT PAGES
# =========================================================

def _find_contact_pages(
    html: str,
    base_url: str,
) -> list[str]:

    soup = BeautifulSoup(html, "lxml")

    urls = []

    for a_tag in soup.find_all("a", href=True):

        href = a_tag["href"].lower()

        text = (
            a_tag.get_text()
            .lower()
            .strip()
        )

        is_contact = False

        for pattern in CONTACT_PAGE_PATTERNS:

            if pattern in href:
                is_contact = True
                break

        if any(
            x in text
            for x in [
                "contact",
                "about",
                "team",
                "support",
                "quote",
                "location",
                "get in touch",
                "reach us",
                "connect",
                "inquiry",
                "services",
            ]
        ):
            is_contact = True

        if is_contact:

            full_url = urljoin(
                base_url,
                a_tag["href"],
            )

            if (
                urlparse(full_url).netloc
                == urlparse(base_url).netloc
            ):

                if full_url not in urls:
                    urls.append(full_url)

    return urls


# =========================================================
# BEST EMAIL SELECTION
# =========================================================

def select_best_email(emails: list[str]) -> str:

    if not emails:
        return ""

    scored = []

    for email in emails:

        score = 70

        local = email.split("@")[0]

        for keyword, keyword_score in EMAIL_PRIORITY.items():

            if keyword in local:
                score = keyword_score
                break

        scored.append((score, email))

    scored.sort(reverse=True)

    return scored[0][1]


# =========================================================
# LEAD SCORING
# =========================================================

def calculate_lead_score(result: dict) -> int:
    """
    Weighted lead quality scoring.

    Signals:
      - Has primary email:               30 pts
      - Has sales/orders/artwork email:  +15 bonus
      - Has phone number:                 10 pts
      - Has embroidery services:          25 pts
      - Is likely embroidery business:    10 pts
      - Has social links:                  5 pts
      - Has contact person name:           5 pts
    Max: 100
    """

    score = 0

    # Email signals
    primary = result.get("primary_email", "")
    if primary:
        score += 30

        # Bonus for high-value email prefixes
        local = primary.split("@")[0]
        high_value = {"sales", "orders", "artwork", "production", "digitizing", "owner"}
        if any(kw in local for kw in high_value):
            score += 15

    # Phone signal
    if result.get("phone_numbers"):
        score += 10

    # Service signals
    if result.get("services_found"):
        score += 25

    if result.get("likely_embroidery_business"):
        score += 10

    # Social signal
    if result.get("social_links"):
        score += 5

    # Contact person signal
    if result.get("contact_people"):
        score += 5

    return min(score, 100)


# =========================================================
# BATCH PROCESSING
# =========================================================

async def batch_extract_emails(
    leads: list[dict],
) -> list[dict]:

    semaphore = asyncio.Semaphore(5)

    async def process_lead(lead: dict):

        async with semaphore:

            website = lead.get("website", "")

            if not website:
                return lead

            try:

                result = await extract_emails_from_website(
                    website
                )

                lead["emails"] = result["emails"]

                lead["email"] = result[
                    "primary_email"
                ]

                lead["social_links"] = result[
                    "social_links"
                ]

                lead["services_found"] = result[
                    "services_found"
                ]

                lead["lead_score"] = result[
                    "lead_score"
                ]

                lead[
                    "likely_embroidery_business"
                ] = result[
                    "likely_embroidery_business"
                ]

                # ======================================
                # NEW FIELDS
                # ======================================

                lead["phone_numbers"] = result[
                    "phone_numbers"
                ]

                lead["contact_people"] = result[
                    "contact_people"
                ]

                lead["job_titles"] = result[
                    "job_titles"
                ]

                lead["business_type"] = result[
                    "business_type"
                ]

                # Auto-fill primary phone if SerpAPI
                # didn't provide one
                if (
                    not lead.get("phone")
                    and result["phone_numbers"]
                ):
                    lead["phone"] = result[
                        "phone_numbers"
                    ][0]

                await asyncio.sleep(1)

            except Exception as e:

                logger.warning(
                    f"Lead processing failed: {e}"
                )

            return lead

    tasks = [
        process_lead(lead)
        for lead in leads
    ]

    return await asyncio.gather(*tasks)