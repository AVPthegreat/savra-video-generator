"""Orchestrator — runs all 4 agents in sync, parallelizing narration and visual design."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.agents.content_analyzer import ContentAnalysis, analyze as _analyze, fallback_analysis
from backend.agents.narrative_planner import NarrativePlan, ScenePlan, plan as _plan, fallback_plan
from backend.agents.narration_writer import write_narration, truncate_narration
from backend.agents.visual_designer import VisualDesign, design as _design, fetch_svg
from backend.core.schemas import SceneChoreography

logger = logging.getLogger("backend.agents.orchestrator")


def generate_scenes(
    text_chunk: str,
    target_count: int = 5,
    max_words_per_narration: int = 37,
    audio_durations: dict[int, int] | None = None,
    precomputed_analysis: tuple[ContentAnalysis, NarrativePlan] | None = None,
) -> list[SceneChoreography]:
    """
    Run all 4 agents in sync:
      1. ContentAnalyzer  — extract domain, concepts, audience level
      2. NarrativePlanner — design teaching arc with metaphors
      3. NarrationWriter  — write per-scene narration (parallelized)
      4. VisualDesigner   — suggest + fetch visuals (parallelized with narration)
    """
    logger.info("orchestrator: len=%d, target=%d, cached=%s", len(text_chunk), target_count, precomputed_analysis is not None)
    scene_count = max(1, min(target_count, 12))

    try:
        # ── Stages 1-2 (sequential, required) ──────────────────────────
        if precomputed_analysis:
            analysis, narrative_plan = precomputed_analysis
            logger.info("Stages 1-2: using cached analysis")
        else:
            try:
                analysis = _analyze(text_chunk)
            except Exception:
                logger.warning("ContentAnalyzer failed, using fallback")
                analysis = fallback_analysis(text_chunk)

            try:
                narrative_plan = _plan(analysis, scene_count)
            except Exception:
                logger.warning("NarrativePlanner failed, using fallback")
                narrative_plan = fallback_plan(analysis, scene_count)

            logger.info("Stages 1-2: domain=%s, %d scenes", analysis.domain, len(narrative_plan.scene_plans))

        # ── Stages 3+4: parallel per-scene narration + visual ──────────
        words_per_scene = max(15, max_words_per_narration)
        scene_futures: list[dict] = []
        provided_durations = audio_durations or {}

        with ThreadPoolExecutor(max_workers=min(scene_count, 8)) as pool:
            for i in range(scene_count):
                plan = narrative_plan.scene_plans[i] if i < len(narrative_plan.scene_plans) else ScenePlan(
                    teaching_goal=f"Scene {i+1}", metaphor="", visual_hint="",
                )
                sid = i + 1

                # Submit narration writing to the thread pool
                narration_future = pool.submit(
                    _safe_write_narration, analysis.domain, plan.teaching_goal, plan.metaphor, words_per_scene,
                )

                scene_futures.append({
                    "scene_id": sid,
                    "narration_future": narration_future,
                    "plan": plan,
                })

            # Collect results
            scene_data = []
            for sf in scene_futures:
                sid = sf["scene_id"]
                plan = sf["plan"]
                heading, narration = sf["narration_future"].result()
                narration = truncate_narration(narration, words_per_scene)

                # Visual design
                try:
                    visual = _design(narration, plan.visual_hint, plan.teaching_goal)
                except Exception:
                    visual = VisualDesign(style="none", description="", search_term="")

                # Fetch SVG if visual style recommends it
                svg_content = fetch_svg(visual.style, visual.search_term) if visual.style != "none" else ""
                svg_path = f"iconify://{visual.search_term}" if svg_content else "none://"

                scene_data.append({
                    "scene_id": sid,
                    "scene_title": heading,
                    "narration": narration,
                    "on_screen_text": narration,
                    "svg_content": svg_content,
                    "svg_path": svg_path,
                    "metaphor_hint": plan.metaphor or plan.teaching_goal,
                })

        # ── Assemble SceneChoreography list ──────────────────────────
        scenes: list[SceneChoreography] = []
        for sd in scene_data:
            sid = sd["scene_id"]
            audio_duration_ms = provided_durations.get(sid, 15000)

            scene = SceneChoreography(
                scene_id=sid,
                scene_title=sd["scene_title"],
                narration=sd["narration"],
                on_screen_text=sd["on_screen_text"],
                svg_markup=sd["svg_content"],
                metaphor_hint=sd["metaphor_hint"],
                audio_path=f"audio/scene_{sid}.mp3",
                svg_path=sd["svg_path"],
                svg_content=sd["svg_content"],
                audio_duration_ms=audio_duration_ms,
                draw_start_ms=0,
                draw_duration_ms=audio_duration_ms,
                hold_ms=0,
                canvas_x=0,
                canvas_y=0,
                canvas_width=1920,
                canvas_height=1080,
                layout_direction="right",
                kinetic_words=[],
                svg_content_secondary=None,
                svg_path_secondary=None,
            )
            scenes.append(scene)

        logger.info("orchestrator: %d scenes generated", len(scenes))
        return scenes

    except Exception as e:
        logger.error("orchestrator failed: %s", e, exc_info=True)
        return []


def _safe_write_narration(domain: str, teaching_goal: str, metaphor: str, max_words: int) -> tuple[str, str]:
    try:
        return write_narration(domain, teaching_goal, metaphor, max_words)
    except Exception:
        logger.warning("NarrationWriter failed for scene, using fallback")
        return teaching_goal or "Let's explore", teaching_goal or "Let's explore this concept."
