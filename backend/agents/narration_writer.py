"""Agent 3: NarrationWriter — writes conversational per-scene narration with heading."""

from __future__ import annotations

import logging

from backend.agents.base import llm_call, parse_json

logger = logging.getLogger("backend.agents.narration_writer")

PROMPT = """Write narration for ONE scene of an educational video.

Context:
- Video domain: {domain}
- Teaching goal for this scene: {teaching_goal}
- Metaphor to use: {metaphor}

Rules:
- Explain like talking to a curious 12 year old who knows nothing
- Start with a relatable everyday example or story, THEN explain
- Use simple words. No jargon. If you must use a technical term, explain it right after.
- Short sentences. One idea per sentence. Like telling a friend at a coffee shop.
- NEVER start with "Imagine", "In this section", "This refers to", or "It is important to note"
- Vary sentence starters: "Here is the cool part...", "So basically...", "Think about...", "Here is how...", "This happens because..."
- STRICT LIMIT: body must be exactly {word_guidance} words. Count carefully.
- End naturally — the video flows to the next scene

Return JSON:
{{"heading": "A short 3-5 word title for this scene", "body": "The narration text..."}}"""


def write_narration(
    domain: str,
    teaching_goal: str,
    metaphor: str,
    max_words: int,
) -> tuple[str, str]:
    prompt = PROMPT.format(
        domain=domain or "this topic",
        teaching_goal=teaching_goal,
        metaphor=metaphor,
        word_guidance=max_words,
    )
    token_budget = int(max_words * 1.8) + 5
    content = llm_call(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Write the narration for this scene. Teaching goal: {teaching_goal}"},
        ],
        max_tokens=token_budget,
        json_mode=False,
    )
    data = parse_json(content)
    heading = data.get("heading", "").strip()
    body = data.get("body", "").strip().strip('"').strip()
    if not heading:
        heading = teaching_goal or "Let's explore"
    if not body:
        body = teaching_goal or "Let's explore this concept."
    return heading, body


def truncate_narration(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    truncated = " ".join(words[:max_words])
    last_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )
    if last_end > 0:
        return truncated[:last_end + 1]
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )
    if last_period > 0:
        return truncated[:last_period + 1]
    return truncated + "."
