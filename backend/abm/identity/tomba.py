import httpx

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

    async def identify(self, payload: dict) -> VisitorInfo | None:
        email = payload.get("email") or payload.get("Business Email")
        if not email:
            return None

        # Step 1: Tomba — email → person data + company domain
        print(f"[Tomba] Enriching {email}")
        resp = await self._tomba.get(_TOMBA_ENRICH_URL, params={"email": email})

        if resp.status_code != 200:
            print(f"[Tomba] Failed: {resp.status_code} {resp.text[:200]}")
            return None

        data = resp.json().get("data", {})

        name = data.get("full_name")
        role = data.get("position")
        linkedin = data.get("linkedin")
        company_name = data.get("company")
        website_url = data.get("website_url")
        country = data.get("country")

        if not company_name and not name:
            print(f"[Tomba] No useful data for {email}")
            return None

        print(f"[Tomba] Found: {name}, {role} @ {company_name} ({website_url})")

        # Step 2: Apify company enricher — domain → description, industry, etc.
        company_desc = None
        industry = None
        if website_url and self._apify_token:
            company_data = await self._enrich_company(website_url)
            if company_data:
                company_desc = company_data.get("description")
                industry = company_data.get("industry")
                # Use enriched company name if Tomba didn't have one
                if not company_name:
                    company_name = company_data.get("companyName")

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

    async def _enrich_company(self, domain: str) -> dict | None:
        """Call Apify website-company-enricher for company details."""
        print(f"[Apify] Enriching company: {domain}")
        try:
            resp = await self._apify.post(
                _APIFY_COMPANY_URL,
                params={"token": self._apify_token},
                headers={"Content-Type": "application/json"},
                json={"domains": [domain]},
            )
            if resp.status_code not in (200, 201):
                print(f"[Apify] Failed: {resp.status_code} {resp.text[:200]}")
                return None

            results = resp.json()
            if results and isinstance(results, list) and len(results) > 0:
                data = results[0]
                print(f"[Apify] Company: {data.get('companyName')} — {data.get('description', '')[:80]}")
                return data
        except Exception as e:
            print(f"[Apify] Error: {e}")
        return None
