from .cache import create_cache
from .timing import timed
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

    @timed
    async def identify_and_personalize(
        self,
        payload: dict,
        elements: list[PageElement],
        site_id: str | None = None,
    ) -> IdentifyResponse:
        visitor = await self.identity.identify(payload)

        if not visitor:
            visitor = _visitor_from_payload(payload)

        if not visitor:
            return IdentifyResponse(
                components={e.id: e.current_text for e in elements},
                cached=False,
            )

        visitor_id = visitor.email or visitor.company or "anonymous"

        cached = await self._cache_get(visitor_id)
        if cached:
            return IdentifyResponse(
                visitor=cached.visitor,
                components=cached.components,
                cached=True,
            )

        result = await research_and_personalize(
            visitor, elements, model=self.model,
        )

        components = {e.id: e.content for e in result}
        for el in elements:
            if el.id not in components:
                components[el.id] = el.current_text

        await self._cache_set(visitor_id, visitor, components)

        return IdentifyResponse(
            visitor=visitor,
            components=components,
            cached=False,
        )

    @timed
    async def _cache_get(self, visitor_id: str) -> PersonalizationCache | None:
        return await self.cache.get(visitor_id)

    @timed
    async def _cache_set(self, visitor_id: str, visitor: VisitorInfo, components: dict) -> None:
        import time
        await self.cache.set(
            visitor_id,
            PersonalizationCache(
                visitor_id=visitor_id,
                visitor=visitor,
                components=components,
                created_at=time.time(),
            ),
        )


_engine: PersonalizationEngine | None = None


def get_engine(site_id: str | None = None) -> PersonalizationEngine:
    global _engine
    if _engine is None:
        _engine = PersonalizationEngine(get_settings())
    return _engine
