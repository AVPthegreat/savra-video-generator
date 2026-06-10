"""Agent 2: NarrativePlanner — designs teaching arc with per-scene metaphors."""

from __future__ import annotations

import logging

from backend.agents.content_analyzer import ContentAnalysis
from backend.agents.base import llm_call, parse_json

logger = logging.getLogger("backend.agents.narrative_planner")

PROMPT = """You are designing a teaching arc for an educational video.

Domain: {domain}
Key concepts: {concepts}
Audience: {audience_level}
Core insight: {core_insight}

You have {scene_count} scenes. Each scene covers ONE idea.

Design a conversational teaching arc:

1. HOOK (1 sentence): A relatable problem or question that grabs attention
2. Scenes: For each scene, provide:
   - teaching_goal: What the learner will understand (1 sentence)
   - metaphor: An everyday analogy that makes the concept click
   - visual_hint: What could appear on screen — can be abstract or concrete
3. CONCLUSION (1 sentence): The final takeaway

Rules:
- Teach like a friend explaining over coffee, not a textbook
- Use relatable analogies the audience already understands
- Each scene builds on the previous one
- Avoid jargon unless you plan to explain it
- visual_hint can be abstract (e.g. "glowing network lines", "stacking blocks") — no asset fetching

Respond with JSON:
{{"hook": "...", "scenes": [{{"teaching_goal": "...", "metaphor": "...", "visual_hint": "..."}}], "conclusion": "..."}}"""


class ScenePlan:
    def __init__(self, teaching_goal: str, metaphor: str, visual_hint: str):
        self.teaching_goal = teaching_goal
        self.metaphor = metaphor
        self.visual_hint = visual_hint


class NarrativePlan:
    def __init__(self, hook: str, scene_plans: list[ScenePlan], conclusion: str):
        self.hook = hook
        self.scene_plans = scene_plans
        self.conclusion = conclusion


def plan(analysis: ContentAnalysis, scene_count: int) -> NarrativePlan:
    prompt = PROMPT.format(
        domain=analysis.domain or "this topic",
        concepts=", ".join(analysis.concepts),
        audience_level=analysis.audience_level,
        core_insight=analysis.core_insight,
        scene_count=scene_count,
    )
    content = llm_call(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Return JSON only.\n\nDesign a teaching arc for these concepts: {analysis.concepts}"},
        ],
        max_tokens=1200,
    )
    data = parse_json(content)
    scenes_data = data.get("scenes", [])
    scene_plans = [
        ScenePlan(
            teaching_goal=s.get("teaching_goal", ""),
            metaphor=s.get("metaphor", ""),
            visual_hint=s.get("visual_hint", ""),
        )
        for s in scenes_data[:scene_count]
    ]
    while len(scene_plans) < scene_count:
        i = len(scene_plans)
        scene_plans.append(ScenePlan(
            teaching_goal=f"Explore concept {i+1}",
            metaphor="",
            visual_hint="",
        ))
    return NarrativePlan(
        hook=data.get("hook", ""),
        scene_plans=scene_plans,
        conclusion=data.get("conclusion", ""),
    )


def fallback_plan(analysis: ContentAnalysis, scene_count: int) -> NarrativePlan:
    return NarrativePlan(
        hook=f"Let's learn about {analysis.domain or 'this topic'}.",
        scene_plans=[
            ScenePlan(
                teaching_goal=c,
                metaphor="",
                visual_hint="",
            )
            for c in (analysis.concepts[:scene_count] or [f"Concept {i+1}" for i in range(scene_count)])
        ],
        conclusion="That's the key idea to remember.",
    )
