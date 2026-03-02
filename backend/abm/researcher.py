import json

import anthropic

from .models import ResearchResponse, VisitorInfo


async def research_visitor(
    client: anthropic.AsyncAnthropic,
    visitor: VisitorInfo,
    model: str = "claude-sonnet-4-6",
) -> ResearchResponse:
    """Research a visitor and produce actionable intelligence for personalization."""

    visitor_context = _build_visitor_context(visitor)

    message = await client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are an ABM research analyst. Given the following visitor information,
produce a research brief that will help personalize a landing page for them.

{visitor_context}

Respond in this exact JSON format (no markdown, no code fences):
{{
  "summary": "2-3 sentence overview of who this person is and what they likely care about",
  "talking_points": ["point 1", "point 2", "point 3"],
  "pain_points": ["pain 1", "pain 2", "pain 3"],
  "recommended_tone": "professional | casual | technical | executive"
}}""",
            }
        ],
    )

    raw = message.content[0].text
    data = json.loads(raw)
    return ResearchResponse(**data)


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
