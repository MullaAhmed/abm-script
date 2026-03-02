from typing import Protocol

from ..models import VisitorInfo


class IdentityProvider(Protocol):
    name: str

    async def identify(self, payload: dict) -> VisitorInfo | None: ...
