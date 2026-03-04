import time
from urllib.parse import urlparse

from ..models import VisitorInfo

# In-memory store for visitors pushed via RB2B webhook
# Keyed by email (lowercase) AND by captured URL (normalized)
_visitor_store_by_email: dict[str, tuple[VisitorInfo, float]] = {}
_visitor_store_by_url: dict[str, tuple[VisitorInfo, float]] = {}

STORE_TTL = 86400  # 24 hours


def _normalize_url(url: str) -> str:
    """Normalize a URL for matching (strip trailing slash, query params, fragment)."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def store_webhook_visitor(visitor: VisitorInfo, captured_url: str | None = None) -> None:
    """Store a visitor received from the RB2B webhook."""
    now = time.time()
    if visitor.email:
        key = visitor.email.lower()
        _visitor_store_by_email[key] = (visitor, now)
        print(f"[RB2B Store] Stored by email: {key}")

    if captured_url:
        key = _normalize_url(captured_url)
        _visitor_store_by_url[key] = (visitor, now)
        print(f"[RB2B Store] Stored by URL: {key}")


def get_stored_visitor(email: str | None = None, page_url: str | None = None) -> VisitorInfo | None:
    """Look up a visitor previously received via webhook, by email or page URL."""
    now = time.time()

    # Try email first
    if email:
        key = email.lower()
        entry = _visitor_store_by_email.get(key)
        if entry:
            visitor, ts = entry
            if now - ts > STORE_TTL:
                del _visitor_store_by_email[key]
                print(f"[RB2B Store] Expired by email: {key}")
            else:
                print(f"[RB2B Store] Found by email: {key}")
                return visitor

    # Try page URL
    if page_url:
        key = _normalize_url(page_url)
        entry = _visitor_store_by_url.get(key)
        if entry:
            visitor, ts = entry
            if now - ts > STORE_TTL:
                del _visitor_store_by_url[key]
                print(f"[RB2B Store] Expired by URL: {key}")
            else:
                print(f"[RB2B Store] Found by URL: {key}")
                return visitor

    return None


def parse_rb2b_webhook(data: dict) -> VisitorInfo:
    """Parse an RB2B webhook payload into a VisitorInfo.

    RB2B sends fields like "First Name", "Company Name", etc.
    We also support snake_case keys from the demo form.
    """
    first = data.get("First Name") or data.get("first_name", "")
    last = data.get("Last Name") or data.get("last_name", "")
    name = f"{first} {last}".strip() if first or last else None

    email = data.get("Business Email") or data.get("email")

    company = data.get("Company Name") or data.get("company_name")
    industry = data.get("Industry") or data.get("company_industry")
    title = data.get("Title") or data.get("title")
    linkedin = data.get("LinkedIn URL") or data.get("linkedin_url")

    # Employee count can be int or string
    emp_count = data.get("Employee Count") or data.get("company_size")
    company_size = str(emp_count) if emp_count else None

    # Location
    city = data.get("City") or data.get("city")
    state = data.get("State") or data.get("state")
    zipcode = data.get("Zipcode") or data.get("zipcode")
    location_parts = [city, state, zipcode]
    location = ", ".join(p for p in location_parts if p) or None

    return VisitorInfo(
        name=name,
        email=email,
        company=company,
        role=title,
        industry=industry,
        company_size=company_size,
        linkedin_url=linkedin,
        location=location,
    )


class RB2BProvider:
    name = "rb2b"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def identify(self, payload: dict) -> VisitorInfo | None:
        print(f"[RB2B] Identifying visitor from payload keys: {list(payload.keys())}")

        # If the payload has real identity fields (form submission or webhook),
        # parse them directly — don't fall through to URL-based store lookup
        has_identity = (
            payload.get("email") or payload.get("Business Email")
            or payload.get("company_name") or payload.get("Company Name")
        )

        if has_identity:
            visitor = parse_rb2b_webhook(payload)
            print(f"[RB2B] Identified from payload: {visitor.name} @ {visitor.company}")
            return visitor

        # No identity in payload — check the webhook store (by page URL)
        page_url = payload.get("page_url")
        if page_url:
            stored = get_stored_visitor(page_url=page_url)
            if stored:
                print(f"[RB2B] Found webhook visitor for {page_url}: {stored.name} @ {stored.company}")
                return stored

        print("[RB2B] Could not identify visitor: no identity data in payload or store")
        return None
