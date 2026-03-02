import httpx

from ..models import VisitorInfo


class IPAPIProvider:
    """Resolve visitor identity from IP using ip-api.com.

    Free service, no API key required.  Returns geolocation,
    ISP, and organization data which can serve as a rough
    company identifier — useful for demos.

    Rate limit: 45 requests/minute on the free tier.
    """

    name = "ip-api"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient()

    async def identify(self, payload: dict) -> VisitorInfo | None:
        ip = payload.get("ip")
        if not ip:
            return None

        resp = await self._client.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,org,isp,country,regionName,city,timezone"},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("status") != "success":
            return None

        org = data.get("org") or data.get("isp")
        if not org:
            return None

        location_parts = [data.get("city"), data.get("regionName"), data.get("country")]
        location = ", ".join(p for p in location_parts if p) or None

        return VisitorInfo(
            company=org,
            location=location,
        )
