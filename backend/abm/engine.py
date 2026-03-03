import time

from .cache import create_cache
from config import Settings, get_settings
from .identity import create_identity_provider
from .models import (
    IdentifyResponse,
    PageElement,
    PersonalizationCache,
    VisitorInfo,
)
from .personalizer import research_and_personalize


def _visitor_from_payload(payload: dict) -> VisitorInfo | None:
    """Try to build a VisitorInfo directly from structured payload fields."""
    email = payload.get("email")
    company = payload.get("company_name") or payload.get("company")
    if not email and not company:
        return None

    first = payload.get("first_name", "")
    last = payload.get("last_name", "")
    name = f"{first} {last}".strip() if first or last else payload.get("name")

    location_parts = [payload.get("city"), payload.get("state"), payload.get("country")]
    location = ", ".join(p for p in location_parts if p) or payload.get("location")

    return VisitorInfo(
        name=name,
        email=email,
        company=company,
        role=payload.get("title") or payload.get("role"),
        industry=payload.get("company_industry") or payload.get("industry"),
        company_size=payload.get("company_size"),
        linkedin_url=payload.get("linkedin_url"),
        location=location,
    )


class PersonalizationEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.abm_ai_model
        self.brave_api_key = settings.brave_api_key
        self.identity = create_identity_provider(
            settings.identity_provider,
            settings.get_identity_api_key(),
        )
        self.cache = create_cache(
            settings.storage_type,
            settings.cache_ttl,
            settings.cache_dir,
        )

    async def identify_and_personalize(
        self,
        payload: dict,
        elements: list[PageElement],
        site_id: str | None = None,
    ) -> IdentifyResponse:
        """Full pipeline: identify -> cache check -> research -> personalize -> cache -> respond."""
        visitor = await self.identity.identify(payload)

        # Fall back to extracting visitor info directly from payload
        if not visitor:
            visitor = _visitor_from_payload(payload)

        if not visitor:
            # Return original text as-is when visitor is unknown
            return IdentifyResponse(
                components={e.id: e.current_text for e in elements},
                cached=False,
            )

        visitor_id = visitor.email or visitor.company or "anonymous"

        # Check cache
        cached = await self.cache.get(visitor_id)
        if cached:
            return IdentifyResponse(
                visitor=cached.visitor,
                components=cached.components,
                cached=True,
            )

        # Brave search + AI personalize
        result = await research_and_personalize(
            visitor, elements, model=self.model, brave_api_key=self.brave_api_key,
        )

        # Build component map, fall back to original text for any missing elements
        components = {e.id: e.content for e in result}
        for el in elements:
            if el.id not in components:
                components[el.id] = el.current_text

        # Cache the result
        await self.cache.set(
            visitor_id,
            PersonalizationCache(
                visitor_id=visitor_id,
                visitor=visitor,
                components=components,
                created_at=time.time(),
            ),
        )

        return IdentifyResponse(
            visitor=visitor,
            components=components,
            cached=False,
        )


_engine: PersonalizationEngine | None = None


def get_engine(site_id: str | None = None) -> PersonalizationEngine:
    global _engine
    if _engine is None:
        _engine = PersonalizationEngine(get_settings())
    return _engine
