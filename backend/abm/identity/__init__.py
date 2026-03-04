from .tomba import TombaProvider


def create_identity_provider(
    tomba_key: str, tomba_secret: str, apify_token: str,
) -> TombaProvider:
    return TombaProvider(tomba_key, tomba_secret, apify_token)
