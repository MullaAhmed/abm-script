from ..models import VisitorInfo


class RB2BProvider:
    name = "rb2b"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def identify(self, payload: dict) -> VisitorInfo | None:
        email = payload.get("email")
        if not email:
            return None

        first = payload.get("first_name", "")
        last = payload.get("last_name", "")
        name = f"{first} {last}".strip() if first or last else None

        location_parts = [
            payload.get("city"),
            payload.get("state"),
            payload.get("country"),
        ]
        location = ", ".join(p for p in location_parts if p) or None

        return VisitorInfo(
            name=name,
            email=email,
            company=payload.get("company_name"),
            role=payload.get("title"),
            industry=payload.get("company_industry"),
            company_size=payload.get("company_size"),
            linkedin_url=payload.get("linkedin_url"),
            location=location,
        )
