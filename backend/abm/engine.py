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
from .personalizer import init_ai_client, research_and_personalize


def _visitor_from_payload(payload: dict) -> VisitorInfo | None:
    """Try to build a VisitorInfo directly from structured payload fields."""
    email = payload.get("email") or payload.get("Business Email")
    company = payload.get("company_name") or payload.get("company") or payload.get("Company Name")
    if not email and not company:
        return None

    first = payload.get("first_name") or payload.get("First Name", "")
    last = payload.get("last_name") or payload.get("Last Name", "")
    name = f"{first} {last}".strip() if first or last else payload.get("name")

    location_parts = [
        payload.get("city") or payload.get("City"),
        payload.get("state") or payload.get("State"),
        payload.get("country"),
    ]
    location = ", ".join(p for p in location_parts if p) or payload.get("location")

    return VisitorInfo(
        name=name,
        email=email,
        company=company,
        role=payload.get("title") or payload.get("role") or payload.get("Title"),
        industry=payload.get("company_industry") or payload.get("industry") or payload.get("Industry"),
        company_size=str(payload.get("company_size") or payload.get("Employee Count") or ""),
        linkedin_url=payload.get("linkedin_url") or payload.get("LinkedIn URL"),
        location=location,
    )


class PersonalizationEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.abm_ai_model
        self.identity = create_identity_provider(
            settings.tomba_api_key,
            settings.tomba_api_secret,
            settings.apify_token,
        )
        self.cache = create_cache(
            settings.storage_type,
            settings.cache_ttl,
            settings.cache_dir,
        )
        init_ai_client(settings.openai_api_key)
        print(f"[Engine] Initialized with provider=apollo, model={settings.abm_ai_model}")

    async def identify_and_personalize(
        self,
        payload: dict,
        elements: list[PageElement],
        site_id: str | None = None,
    ) -> IdentifyResponse:
        """Full pipeline: identify -> cache check -> personalize -> cache -> respond."""
        print(f"[Engine] Starting pipeline with {len(elements)} elements")

        visitor = await self.identity.identify(payload)

        # Fall back to extracting visitor info directly from payload
        if not visitor:
            print("[Engine] Provider returned None, trying payload fallback")
            visitor = _visitor_from_payload(payload)

        if not visitor:
            print("[Engine] Could not identify visitor, returning original text")
            return IdentifyResponse(
                components={e.id: e.current_text for e in elements},
                cached=False,
            )

        print(f"[Engine] Visitor identified: {visitor.name} ({visitor.email}) @ {visitor.company}")
        visitor_id = visitor.email or visitor.company or "anonymous"

        # Check cache
        cached = await self.cache.get(visitor_id)
        if cached:
            print(f"[Engine] Cache hit for {visitor_id}")
            return IdentifyResponse(
                visitor=cached.visitor,
                components=cached.components,
                cached=True,
            )

        print(f"[Engine] Cache miss for {visitor_id}, calling AI personalizer")

        # AI personalize using visitor data
        result = await research_and_personalize(
            visitor, elements, model=self.model,
        )

        # Build component map, fall back to original text for any missing elements
        components = {e.id: e.content for e in result}
        for el in elements:
            if el.id not in components:
                components[el.id] = el.current_text

        print(f"[Engine] Personalized {len(components)} components")

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
        print(f"[Engine] Cached result for {visitor_id}")

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
