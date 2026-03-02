import httpx

from ..models import VisitorInfo


class ClearbitProvider:
    name = "clearbit-reveal"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient()

    async def identify(self, payload: dict) -> VisitorInfo | None:
        ip = payload.get("ip")
        if not ip:
            return None

        resp = await self._client.get(
            f"https://reveal.clearbit.com/v1/companies/find?ip={ip}",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        company = data.get("company", {})
        if not company.get("name"):
            return None

        return VisitorInfo(
            company=company["name"],
            industry=company.get("industry"),
            company_size=company.get("employeesRange"),
            location=company.get("location"),
        )
