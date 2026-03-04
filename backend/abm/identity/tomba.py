import asyncio

import httpx

from ..timing import timed

from ..models import VisitorInfo

_TOMBA_ENRICH_URL = "https://api.tomba.io/v1/enrich"
_APIFY_COMPANY_URL = "https://api.apify.com/v2/acts/great_pistachio~website-company-enricher/run-sync-get-dataset-items"


class TombaProvider:
    name = "tomba"

    def __init__(
        self, tomba_key: str, tomba_secret: str, apify_token: str,
    ) -> None:
        self._tomba = httpx.AsyncClient(
            headers={"X-Tomba-Key": tomba_key, "X-Tomba-Secret": tomba_secret},
        )
        self._apify_token = apify_token
        self._apify = httpx.AsyncClient(timeout=60.0)

    @timed
    async def identify(self, payload: dict) -> VisitorInfo | None:
        email = payload.get("email") or payload.get("Business Email")
        if not email:
            return None

        domain = email.split("@")[1] if "@" in email else None

        tomba_task = self._enrich_person(email)
        company_task = self._enrich_company(domain) if domain and self._apify_token else asyncio.sleep(0)

        tomba_result, company_result = await asyncio.gather(
            tomba_task, company_task, return_exceptions=True,
        )

        if isinstance(tomba_result, Exception) or tomba_result is None:
            return None

        data = tomba_result
        name = data.get("full_name")
        role = data.get("position")
        linkedin = data.get("linkedin")
        company_name = data.get("company")
        country = data.get("country")

        if not company_name and not name:
            return None

        company_desc = None
        industry = None
        if isinstance(company_result, dict):
            company_desc = company_result.get("description")
            industry = company_result.get("industry")
            if not company_name:
                company_name = company_result.get("companyName")

        return VisitorInfo(
            name=name,
            email=email,
            company=company_name,
            company_description=company_desc,
            role=role,
            industry=industry,
            linkedin_url=linkedin,
            location=country,
        )

    @timed
    async def _enrich_person(self, email: str) -> dict | None:
        resp = await self._tomba.get(_TOMBA_ENRICH_URL, params={"email": email})
        if resp.status_code != 200:
            return None
        return resp.json().get("data", {})

    @timed
    async def _enrich_company(self, domain: str) -> dict | None:
        try:
            resp = await self._apify.post(
                _APIFY_COMPANY_URL,
                params={"token": self._apify_token},
                headers={"Content-Type": "application/json"},
                json={"domains": [domain]},
            )
            if resp.status_code not in (200, 201):
                return None

            results = resp.json()
            if results and isinstance(results, list) and len(results) > 0:
                return results[0]
        except Exception:
            pass
        return None
