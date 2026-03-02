import json

import litellm

from .models import PageElement, PersonalizedElement, VisitorInfo


def _build_visitor_context(visitor: VisitorInfo) -> str:
    parts: list[str] = []
    if visitor.name:
        parts.append(f"Name: {visitor.name}")
    if visitor.email:
        parts.append(f"Email: {visitor.email}")
    if visitor.company:
        parts.append(f"Company: {visitor.company}")
    if visitor.role:
        parts.append(f"Role: {visitor.role}")
    if visitor.industry:
        parts.append(f"Industry: {visitor.industry}")
    if visitor.company_size:
        parts.append(f"Company Size: {visitor.company_size}")
    if visitor.linkedin_url:
        parts.append(f"LinkedIn: {visitor.linkedin_url}")
    if visitor.location:
        parts.append(f"Location: {visitor.location}")
    return "\n".join(parts) if parts else "No visitor information available."


async def research_and_personalize(
    visitor: VisitorInfo,
    elements: list[PageElement],
    model: str = "openai/gpt-5-nano",
) -> list[PersonalizedElement]:
    """Research a visitor via web search and personalize page elements in a single LLM call."""

    visitor_context = _build_visitor_context(visitor)

    elements_spec = "\n".join(
        f'- id="{e.id}" tag=<{e.tag}> current text: "{e.current_text}"'
        for e in elements
    )

    response = await litellm.aresponses(
        model=model,
        service_tier="priority",
        tools=[{"type": "web_search_preview"}],
        input=f"""You are an expert conversion copywriter for DummyOps, an AI-powered landing page personalization platform. DummyOps lets marketing teams automatically tailor headlines, copy, and CTAs to each website visitor in real time — boosting conversions without manual A/B testing.

A visitor just landed on the DummyOps marketing site. Your job:
1. Research this visitor's company and role to understand their world.
2. Rewrite the landing page copy to sell DummyOps to THIS specific person — connect DummyOps's value to their actual problems.

VISITOR:
{visitor_context}

RESEARCH INSTRUCTIONS:
Search the web for the visitor's company to learn what they do, their industry, scale, and any recent news. Understand what someone in their role cares about (e.g. a VP of Marketing cares about pipeline and conversion rates, a CTO cares about engineering velocity and integration ease).

REWRITING RULES:
- Sell DummyOps by connecting its benefits to the visitor's specific situation
- Reference their company by name where natural (headlines, social proof, testimonials)
- Speak to their role's priorities — what would make THIS person click "Start Free Trial"?
- Keep each element's purpose (headline stays a headline, CTA stays a CTA, etc.)
- Match the approximate length of the original — don't bloat copy
- Sound confident and natural, not salesy or generic. Write like a top SaaS marketer.
- For testimonials: rewrite the quote to reflect a use case relevant to the visitor's industry, and make the attribution someone in a similar role/industry (not the visitor themselves)
- For trust/proof lines: reference companies or metrics relevant to their industry

PAGE ELEMENTS TO PERSONALIZE:
{elements_spec}

Respond with ONLY this JSON (no markdown, no code fences):
{{
  "elements": [
    {{"id": "element-id", "content": "personalized text"}}
  ]
}}""",
    )

    # Extract text from the Responses API output
    raw = ""
    for item in response.output:
        if getattr(item, "type", None) == "message":
            for block in item.content:
                if getattr(block, "type", None) == "output_text":
                    raw = block.text
                    break
            break

    data = json.loads(raw)
    return [PersonalizedElement(**e) for e in data["elements"]]
