import asyncio

from openai import AsyncOpenAI

from .timing import timed

from .models import PageElement, PersonalizedElement, VisitorInfo

_client: AsyncOpenAI | None = None


def init_ai_client(api_key: str) -> None:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=api_key)


def _get_client() -> AsyncOpenAI:
    if _client is None:
        raise RuntimeError("AI client not initialized — call init_ai_client() first")
    return _client


def _build_company_context(visitor: VisitorInfo) -> str:
    parts: list[str] = []
    if visitor.company:
        parts.append(f"Company: {visitor.company}")
    if visitor.company_description:
        parts.append(f"About: {visitor.company_description}")
    if visitor.industry:
        parts.append(f"Industry: {visitor.industry}")
    if visitor.company_size:
        parts.append(f"Company Size: {visitor.company_size}")
    if visitor.role:
        parts.append(f"Visitor Role: {visitor.role}")
    if visitor.location:
        parts.append(f"Location: {visitor.location}")
    return "\n".join(parts) if parts else "Unknown company"


@timed
async def _personalize_element(
    element: PageElement,
    company_context: str,
    model: str,
) -> PersonalizedElement:
    response = await _get_client().chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": f"""Rewrite this landing page element for a visitor from this company. Sell DummyOps (AI landing page personalization) to their specific industry and company.

COMPANY:
{company_context}

RULES:
- Use the company name naturally
- Focus on their industry's pain points and how DummyOps solves them
- Keep the element's purpose and approximate length
- Sound confident, not salesy. Write like a top SaaS marketer.
- For trust/proof elements: reference relevant industry metrics

ELEMENT:
id="{element.id}" tag=<{element.tag}> current: "{element.current_text}"

Respond with ONLY the rewritten plain text. No HTML tags, no markdown, no JSON, no quotes, no explanation.""",
        }],
    )

    content = response.choices[0].message.content.strip().strip('"')
    return PersonalizedElement(id=element.id, content=content)


@timed
async def research_and_personalize(
    visitor: VisitorInfo,
    elements: list[PageElement],
    model: str = "gpt-5-nano",
) -> list[PersonalizedElement]:
    company_context = _build_company_context(visitor)

    tasks = [
        _personalize_element(el, company_context, model)
        for el in elements
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    personalized = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            personalized.append(PersonalizedElement(id=elements[i].id, content=elements[i].current_text))
        else:
            personalized.append(result)

    return personalized
