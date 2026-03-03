import json

import httpx
import litellm

from .models import PageElement, PersonalizedElement, VisitorInfo

_brave_client = httpx.AsyncClient()


async def _brave_search(query: str, api_key: str, count: int = 3) -> str:
    """Hit Brave Search API and return a compact summary of top results."""
    resp = await _brave_client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": count},
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        timeout=5.0,
    )
    if resp.status_code != 200:
        return ""

    results = resp.json().get("web", {}).get("results", [])
    snippets: list[str] = []
    for r in results:
        title = r.get("title", "")
        desc = r.get("description", "")
        snippets.append(f"- {title}: {desc}")
    return "\n".join(snippets)


def _build_company_context(visitor: VisitorInfo) -> str:
    parts: list[str] = []
    if visitor.company:
        parts.append(f"Company: {visitor.company}")
    if visitor.industry:
        parts.append(f"Industry: {visitor.industry}")
    if visitor.company_size:
        parts.append(f"Company Size: {visitor.company_size}")
    if visitor.role:
        parts.append(f"Visitor Role: {visitor.role}")
    if visitor.location:
        parts.append(f"Location: {visitor.location}")
    return "\n".join(parts) if parts else "Unknown company"


async def research_and_personalize(
    visitor: VisitorInfo,
    elements: list[PageElement],
    model: str = "openai/gpt-5-nano",
    brave_api_key: str = "",
) -> list[PersonalizedElement]:
    """Search for the visitor's company via Brave, then personalize page elements."""

    company_context = _build_company_context(visitor)

    # Brave search for company intel
    research = ""
    if brave_api_key and visitor.company:
        query = f"{visitor.company} company"
        if visitor.industry:
            query += f" {visitor.industry}"
        research = await _brave_search(query, brave_api_key)

    research_block = ""
    if research:
        research_block = f"\nCOMPANY RESEARCH:\n{research}\n"

    elements_spec = "\n".join(
        f'- id="{e.id}" tag=<{e.tag}> current: "{e.current_text}"'
        for e in elements
    )

    response = await litellm.acompletion(
        model=model,
        messages=[{
            "role": "user",
            "content": f"""Rewrite these landing page elements for a visitor from this company. Sell DummyOps (AI landing page personalization) to their specific industry and company.

COMPANY:
{company_context}
{research_block}
RULES:
- Use the company name naturally in headlines and copy
- Focus on their industry's pain points and how DummyOps solves them
- Keep each element's purpose and approximate length
- Sound confident, not salesy. Write like a top SaaS marketer.
- For trust/proof: reference relevant industry metrics or companies

ELEMENTS:
{elements_spec}

Respond with ONLY JSON, no markdown fences:
{{"elements": [{{"id": "...", "content": "..."}}]}}""",
        }],
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return [PersonalizedElement(**e) for e in data["elements"]]
