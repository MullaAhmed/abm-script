from .base import IdentityProvider
from .clearbit import ClearbitProvider
from .rb2b import RB2BProvider


def create_identity_provider(
    provider: str, api_key: str
) -> IdentityProvider:
    match provider:
        case "rb2b":
            return RB2BProvider(api_key)
        case "clearbit-reveal":
            return ClearbitProvider(api_key)
        case _:
            raise ValueError(f"Unknown identity provider: {provider}")
