import json

import litellm

from .models import PageElement, PersonalizedElement, VisitorInfo


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
) -> list[PersonalizedElement]:
    """Personalize page elements using visitor data from RB2B."""

    company_context = _build_company_context(visitor)
    print(f"[Personalizer] Company context:\n{company_context}")
    print(f"[Personalizer] Personalizing {len(elements)} elements with model={model}")

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
    print(f"[Personalizer] AI response: {raw[:200]}...")
    data = json.loads(raw)
    result = [PersonalizedElement(**e) for e in data["elements"]]
    print(f"[Personalizer] Generated {len(result)} personalized elements")
    return result
