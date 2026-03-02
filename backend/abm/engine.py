import time

from .cache import create_cache
from ..config import Settings, get_settings
from .identity import create_identity_provider
from .models import (
    IdentifyResponse,
    PageElement,
    PersonalizationCache,
)
from .personalizer import personalize_elements
from .researcher import research_visitor


class PersonalizationEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.abm_ai_model
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

        # AI pipeline: research -> personalize
        research = await research_visitor(visitor, model=self.model)
        result = await personalize_elements(
            visitor, research, elements, model=self.model
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
