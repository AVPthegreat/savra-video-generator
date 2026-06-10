"""Multi-stage LLM pipeline — delegates to modular agents in backend/agents/."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.agents.content_analyzer import ContentAnalysis, analyze as _analyze, fallback_analysis
from backend.agents.narrative_planner import NarrativePlan, ScenePlan, plan as _plan, fallback_plan
from backend.agents.narration_writer import write_narration, truncate_narration
from backend.agents.visual_designer import VisualDesign, design as _design, fetch_svg
from backend.agents.orchestrator import generate_scenes
from backend.core.schemas import SceneChoreography

logger = logging.getLogger("backend.services.multi_model_director")


def generate_enhanced_scenes(
    text_chunk: str,
    target_count: int = 5,
    max_words_per_narration: int = 37,
    audio_durations: dict[int, int] | None = None,
    precomputed_analysis: tuple[ContentAnalysis, NarrativePlan] | None = None,
) -> list[SceneChoreography]:
    """
    Generate scenes using the 4-agent pipeline (delegates to orchestrator).

    Args:
        text_chunk: Input text to generate scenes from
        target_count: Target number of scenes
        max_words_per_narration: Max words per spoken narration
        audio_durations: Optional {scene_id: ms} for timing
        precomputed_analysis: Optional cached (ContentAnalysis, NarrativePlan)

    Returns:
        List of SceneChoreography objects
    """
    return generate_scenes(
        text_chunk=text_chunk,
        target_count=target_count,
        max_words_per_narration=max_words_per_narration,
        audio_durations=audio_durations,
        precomputed_analysis=precomputed_analysis,
    )


# ── Backward-compatible aliases ───────────────────────────────────────────────

class ContextualAnalyzer:
    """Retained for backward compatibility with pipeline_service."""
    def analyze(self, text_chunk: str, target_count: int = 5) -> tuple:
        analysis = _analyze(text_chunk)
        plan = _plan(analysis, target_count)
        return analysis, plan
