import json

import litellm

from .models import (
    PageElement,
    PersonalizedElement,
    ResearchResponse,
    VisitorInfo,
)


async def personalize_elements(
    visitor: VisitorInfo,
    research: ResearchResponse,
    elements: list[PageElement],
    model: str = "openai/gpt-5-nano",
) -> list[PersonalizedElement]:
    """Generate personalized content for each page element based on visitor research."""

    elements_spec = "\n".join(
        f'- id="{e.id}" tag=<{e.tag}> current text: "{e.current_text}"'
        for e in elements
    )

    response = await litellm.acompletion(
        model=model,
        max_tokens=2048,
        service_tier="priority",
        messages=[
            {
                "role": "user",
                "content": f"""You are an ABM copywriter personalizing a landing page for a specific visitor.

VISITOR RESEARCH:
{research.summary}

Talking points: {", ".join(research.talking_points)}
Pain points: {", ".join(research.pain_points)}
Recommended tone: {research.recommended_tone}

VISITOR:
Name: {visitor.name or "Unknown"}
Company: {visitor.company or "Unknown"}
Role: {visitor.role or "Unknown"}
Industry: {visitor.industry or "Unknown"}

PAGE ELEMENTS TO PERSONALIZE:
{elements_spec}

For each element, rewrite the text so it speaks directly to this visitor.
Infer the purpose of each element from its tag and current text (e.g. an <h1> is a headline, a <button> is a CTA, a <p> is body copy).
Keep the same general intent but tailor it to the visitor's company, role, and pain points.
Keep text concise — match the approximate length of the original.

Respond in this exact JSON format (no markdown, no code fences):
{{
  "elements": [
    {{"id": "element-id", "content": "personalized text"}}
  ]
}}""",
            }
        ],
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)
    return [PersonalizedElement(**e) for e in data["elements"]]
