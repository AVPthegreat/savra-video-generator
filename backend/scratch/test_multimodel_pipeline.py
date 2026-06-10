"""
Diagnostic script for the multi-stage director pipeline.
Runs each stage independently and prints what actually happens.

Usage (from project root):
    python -m backend.scratch.test_multimodel_pipeline
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.WARNING)
logging.getLogger("backend.services.multi_model_director").setLevel(logging.INFO)

TEST_TEXT = """
Machine learning is a branch of artificial intelligence that enables computers to learn
from data without being explicitly programmed. Instead of writing rules by hand,
we feed examples to algorithms and let them discover patterns. Supervised learning
trains models on labeled data — like teaching a child with flashcards. Unsupervised
learning finds hidden structure in unlabeled data. Reinforcement learning rewards
an agent for good decisions over time, like training a dog with treats.
Neural networks, loosely inspired by the brain, stack layers of transformations to
extract increasingly abstract features from raw input.
"""

SEP = "─" * 60
OK  = "✓"
ERR = "✗"


def _key_status(key: str) -> str:
    return f"{OK} set ({key[:8]}…)" if key else f"{ERR} NOT SET"


def run() -> None:
    print(f"\n{SEP}")
    print("MULTI-STAGE DIRECTOR DIAGNOSTIC")
    print(SEP)

    # ── STAGE 0: Provider configuration ──────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 0 — Provider configuration\n{SEP}")
    from backend.core.config import get_settings
    settings = get_settings()
    print(f"  Groq:     {_key_status(settings.groq_api_key)}")
    print(f"  Cerebras: {_key_status(settings.cerebras_api_key)}")
    print(f"  Gemini:   {_key_status(settings.gemini_api_key)}")

    # ── STAGE 1: _call_with_fallback — one call per configured provider ───────
    print(f"\n{SEP}\nSTAGE 1 — Fallback chain (_call_with_fallback per provider)\n{SEP}")
    from backend.services.multi_model_director import (
        _LLMConfig, _GROQ_BASE, _CEREBRAS_BASE, _GEMINI_BASE,
        _call_with_fallback,
    )
    probe_messages = [
        {"role": "system", "content": "Return ONLY valid JSON: {\"ok\": true}"},
        {"role": "user", "content": "ping"},
    ]
    provider_configs: list[tuple[str, _LLMConfig]] = [
        ("Groq",     _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.1-8b-instant")),
        ("Cerebras", _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.1-8b")),
        ("Gemini",   _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.0-flash")),
    ]
    for label, cfg in provider_configs:
        if not cfg.api_key:
            print(f"  {label}: SKIPPED (no key)")
            continue
        try:
            content = _call_with_fallback([cfg], probe_messages, max_tokens=20)
            print(f"  {label}: {OK} responded → {content.strip()[:60]}")
        except Exception as exc:
            print(f"  {label}: {ERR} {exc!r:.80}")

    # ── STAGE 2: Content Analysis (Stage 1 of pipeline) ───────────────────────
    print(f"\n{SEP}\nSTAGE 2 — Content Analysis\n{SEP}")
    from backend.services.multi_model_director import _analyze_content, _fallback_content_analysis
    try:
        analysis = _analyze_content(TEST_TEXT)
        print(f"  {OK} domain={analysis.domain}")
        print(f"     concepts ({len(analysis.concepts)}): {analysis.concepts[:4]}")
        print(f"     audience={analysis.audience_level}")
        print(f"     core_insight={analysis.core_insight[:80]}")
    except Exception as exc:
        print(f"  {ERR} _analyze_content failed: {exc}")
        print(f"  → using fallback")
        analysis = _fallback_content_analysis(TEST_TEXT)
        print(f"  {OK} fallback: {len(analysis.concepts)} concepts")

    # ── STAGE 3: Narrative Planning (Stage 2) ────────────────────────────────
    print(f"\n{SEP}\nSTAGE 3 — Narrative Planning (target=3 scenes)\n{SEP}")
    from backend.services.multi_model_director import _plan_narrative, _fallback_narrative_plan
    try:
        plan = _plan_narrative(analysis, scene_count=3)
        print(f"  {OK} hook={plan.hook[:80]}")
        for i, sp in enumerate(plan.scene_plans):
            print(f"     Scene {i+1}: goal={sp.teaching_goal[:60]}")
            print(f"               metaphor={sp.metaphor[:60]}")
            print(f"               visual_hint={sp.visual_hint[:60]}")
        print(f"  conclusion={plan.conclusion[:60]}")
    except Exception as exc:
        print(f"  {ERR} _plan_narrative failed: {exc}")
        plan = _fallback_narrative_plan(analysis, 3)
        print(f"  → fallback: {len(plan.scene_plans)} scenes")

    # ── STAGE 4: Narration Writing (Stage 3) ─────────────────────────────────
    print(f"\n{SEP}\nSTAGE 4 — Narration Writing (first scene)\n{SEP}")
    from backend.services.multi_model_director import _write_narration
    if plan.scene_plans:
        sp = plan.scene_plans[0]
        try:
            narration = _write_narration(analysis.domain, sp.teaching_goal, sp.metaphor, max_words=30)
            wc = len(narration.split())
            ok_mark = OK if wc <= 35 else ERR  # allow small overage before truncation
            print(f"  {ok_mark} narration ({wc} words): {narration[:120]}")
        except Exception as exc:
            print(f"  {ERR} _write_narration failed: {exc}")

    # ── STAGE 5: Visual Design (Stage 4) ─────────────────────────────────────
    print(f"\n{SEP}\nSTAGE 5 — Visual Design (first scene)\n{SEP}")
    from backend.services.multi_model_director import _design_visual
    try:
        vd = _design_visual("This is a test narration about machine learning.", "neural network", "Understand neural nets")
        print(f"  {OK} style={vd.style}  desc={vd.description}")
    except Exception as exc:
        print(f"  {ERR} _design_visual failed: {exc}")

    # ── STAGE 6: Full end-to-end (2 scenes) ──────────────────────────────────
    print(f"\n{SEP}\nSTAGE 6 — generate_enhanced_scenes end-to-end (target=2)\n{SEP}")
    from backend.services.multi_model_director import generate_enhanced_scenes
    try:
        scenes = generate_enhanced_scenes(TEST_TEXT, target_count=2, max_words_per_narration=30)
        for s in scenes:
            wc = len(s.narration.split())
            print(f"  Scene {s.scene_id}: ({wc} words)")
            print(f"    narration:  {s.narration[:100]}{'...' if len(s.narration) > 100 else ''}")
            print(f"    metaphor:   {s.metaphor_hint[:60]}")
            print(f"    svg_path:   {s.svg_path}")
            print(f"    timing:     draw={s.draw_duration_ms}ms  hold={s.hold_ms}ms")
            print()
    except Exception as exc:
        print(f"  {ERR} FAILED: {exc}")
        import traceback
        traceback.print_exc()

    print(f"\n{SEP}\nDIAGNOSTIC COMPLETE\n{SEP}\n")


if __name__ == "__main__":
    run()
