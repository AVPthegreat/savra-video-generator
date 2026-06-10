"""Agent 4: VisualDesigner — suggests on-screen visuals and fetches SVGs."""

from __future__ import annotations

import logging

from backend.agents.base import llm_call, parse_json

logger = logging.getLogger("backend.agents.visual_designer")

PROMPT = """For an educational video scene, suggest if a visual would help.

Scene context:
- Narration: {narration}
- Visual hint from planning: {visual_hint}
- Teaching goal: {teaching_goal}

Decide:
- style: "icon" (simple symbol matching the concept), "diagram" (relationship/flow), "abstract" (decorative shapes), "code" (code block), "none" (text-only)
- description: Describe briefly what appears on screen. (max 8 words)
- search_term: A keyword to search for an icon/image (e.g. "brain", "server", "network"). Empty string if style is "none" or "abstract".

Prefer adding visuals over text-only. A simple icon makes the scene more engaging.
When in doubt, choose "icon" with a relevant search_term.

Respond with JSON: {{"style": "...", "description": "...", "search_term": "..."}}"""


class VisualDesign:
    def __init__(self, style: str, description: str, search_term: str = ""):
        self.style = style
        self.description = description
        self.search_term = search_term


VALID_STYLES = ("icon", "diagram", "abstract", "code", "none")


def design(narration: str, visual_hint: str, teaching_goal: str) -> VisualDesign:
    try:
        content = llm_call(
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": f"Return JSON only.\n\nNarration: {narration}\nVisual hint: {visual_hint}\nTeaching goal: {teaching_goal}"},
            ],
            max_tokens=100,
        )
        data = parse_json(content)
        style = data.get("style", "icon")
        if style not in VALID_STYLES:
            style = "icon"
        return VisualDesign(
            style=style,
            description=data.get("description", "")[:60],
            search_term=data.get("search_term", ""),
        )
    except Exception:
        return VisualDesign(style="none", description="", search_term="")


def fetch_svg(style: str, search_term: str) -> str:
    """Fetch an SVG for the given visual style and search term. Returns empty string on failure."""
    if style == "none" or not search_term:
        return ""
    try:
        from backend.services.icon_fetcher import fetch_icon_svg
        result = fetch_icon_svg(search_term)
        if result and isinstance(result, tuple) and len(result) == 2:
            return result[1]
        return result or ""
    except Exception:
        logger.warning("Failed to fetch SVG for '%s' (%s)", search_term, style)
        return ""
