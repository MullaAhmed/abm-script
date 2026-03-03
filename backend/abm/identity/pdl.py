import httpx

from ..models import VisitorInfo

_PDL_IP_URL = "https://api.peopledatalabs.com/v5/ip/enrich"


class PDLProvider:
    name = "pdl"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient()

    async def identify(self, payload: dict) -> VisitorInfo | None:
        ip = payload.get("ip")
        if not ip:
            return None

        resp = await self._client.get(
            _PDL_IP_URL,
            params={"ip": ip},
            headers={"X-Api-Key": self.api_key},
        )
        if resp.status_code != 200:
            return None

        data = resp.json().get("data", {})
        person = data.get("person") or {}
        company = data.get("company") or {}

        # Prefer person-level email; fall back to nothing
        email = None
        emails = person.get("emails") or []
        if emails:
            email = emails[0].get("address")

        name = person.get("full_name")
        role = person.get("job_title")
        linkedin = person.get("linkedin_url")

        company_name = company.get("name") or person.get("job_company_name")
        industry = company.get("industry") or person.get("industry")
        company_size = company.get("size") or person.get("job_company_size")

        loc = company.get("location") or {}
        location_parts = [loc.get("locality"), loc.get("region"), loc.get("country")]
        location = ", ".join(p for p in location_parts if p) or person.get("location_name") or None

        if not company_name:
            return None

        return VisitorInfo(
            name=name,
            email=email,
            company=company_name,
            role=role,
            industry=industry,
            company_size=company_size,
            linkedin_url=linkedin,
            location=location,
        )
