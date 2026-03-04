from pydantic import BaseModel


# --- Visitor ---


class VisitorInfo(BaseModel):
    """Identity data resolved about the visitor."""
    name: str | None = None
    email: str | None = None
    company: str | None = None
    company_description: str | None = None
    role: str | None = None
    industry: str | None = None
    company_size: str | None = None
    linkedin_url: str | None = None
    location: str | None = None


# --- Page Elements ---


class PageElement(BaseModel):
    """An element scraped from the page by the client script."""
    id: str
    tag: str
    current_text: str


# --- AI Pipeline ---


class PersonalizedElement(BaseModel):
    """Result of personalizing a single element."""
    id: str
    content: str


class ResearchRequest(BaseModel):
    """Request to research a visitor."""
    visitor: VisitorInfo


class ResearchResponse(BaseModel):
    """Research results about a visitor."""
    summary: str
    talking_points: list[str]
    pain_points: list[str]
    recommended_tone: str


# --- Cache ---


class PersonalizationCache(BaseModel):
    """Cached personalization result."""
    visitor_id: str
    visitor: VisitorInfo
    components: dict[str, str]
    created_at: float


# --- API ---


class IdentifyRequest(BaseModel):
    """Client request to identify + personalize a visitor."""
    payload: dict
    elements: list[PageElement]
    site_id: str | None = None
    page_url: str | None = None


class IdentifyResponse(BaseModel):
    """Response with personalized component content."""
    visitor: VisitorInfo | None = None
    components: dict[str, str]
    cached: bool = False
