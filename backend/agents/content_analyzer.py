"""Agent 1: ContentAnalyzer — extracts domain, concepts, audience level, core insight."""

from __future__ import annotations

import logging
import re

from backend.agents.base import llm_call, parse_json

logger = logging.getLogger("backend.agents.content_analyzer")

PROMPT = """You are analyzing educational content for a teaching video.
Identify the following from the text:

- domain: The subject area (e.g. "Docker containers", "Kubernetes", "Python")
- concepts: 3-6 key concepts that need explaining (as short phrases)
- audience_level: "beginner", "intermediate", or "advanced"
- prerequisites: What the learner should already know (list, can be empty)
- core_insight: The single most important "aha" takeaway (one sentence)

Be concise. Just extract what's actually in the text.

Respond with JSON: {{"domain": "...", "concepts": [...], "audience_level": "...", "prerequisites": [...], "core_insight": "..."}}"""


class ContentAnalysis:
    def __init__(self, domain: str, concepts: list[str], audience_level: str, prerequisites: list[str], core_insight: str):
        self.domain = domain
        self.concepts = concepts
        self.audience_level = audience_level
        self.prerequisites = prerequisites
        self.core_insight = core_insight


def analyze(text: str) -> ContentAnalysis:
    content = llm_call(
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Return JSON only.\n\n{text}"},
        ],
        max_tokens=400,
    )
    data = parse_json(content)
    return ContentAnalysis(
        domain=data.get("domain", ""),
        concepts=data.get("concepts", [])[:6],
        audience_level=data.get("audience_level", "beginner"),
        prerequisites=data.get("prerequisites", []),
        core_insight=data.get("core_insight", ""),
    )


def fallback_analysis(text: str) -> ContentAnalysis:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return ContentAnalysis(
        domain="",
        concepts=sentences[:5],
        audience_level="beginner",
        prerequisites=[],
        core_insight=sentences[0] if sentences else "",
    )
