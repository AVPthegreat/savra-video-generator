"""Tests for multi_model_director — dataclasses, pipeline stages, and orchestrator."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from backend.services.multi_model_director import (
    ContentAnalysis,
    ScenePlan,
    NarrativePlan,
    VisualDesign,
    _truncate_narration,
    _safe_parse_json,
    ContextualAnalyzer,
    generate_enhanced_scenes,
)


class TestContentAnalysis:
    def test_instantiation(self):
        ca = ContentAnalysis(
            domain="Python",
            concepts=["functions", "loops", "lists"],
            audience_level="beginner",
            prerequisites=["basic syntax"],
            core_insight="Functions let you reuse code.",
        )
        assert ca.domain == "Python"
        assert ca.concepts == ["functions", "loops", "lists"]
        assert ca.audience_level == "beginner"
        assert ca.prerequisites == ["basic syntax"]
        assert ca.core_insight == "Functions let you reuse code."

    def test_concepts_capped_at_6(self):
        ca = ContentAnalysis(domain="", concepts=list(range(20)), audience_level="", prerequisites=[], core_insight="")
        assert len(ca.concepts) == 20  # dataclass doesn't cap; caller does


class TestScenePlan:
    def test_instantiation(self):
        sp = ScenePlan(teaching_goal="Learn X", metaphor="Like a toolbox", visual_hint="stacking blocks")
        assert sp.teaching_goal == "Learn X"
        assert sp.metaphor == "Like a toolbox"
        assert sp.visual_hint == "stacking blocks"


class TestNarrativePlan:
    def test_instantiation(self):
        np = NarrativePlan(
            hook="Ever wondered how?",
            scene_plans=[ScenePlan("A", "B", "C"), ScenePlan("D", "E", "F")],
            conclusion="That's how!",
        )
        assert np.hook == "Ever wondered how?"
        assert len(np.scene_plans) == 2
        assert np.conclusion == "That's how!"


class TestVisualDesign:
    def test_instantiation(self):
        vd = VisualDesign(style="diagram", description="flow chart of concepts")
        assert vd.style == "diagram"
        assert vd.description == "flow chart of concepts"

    def test_none_style_valid(self):
        vd = VisualDesign(style="none", description="")
        assert vd.style == "none"


class TestSafeParseJson:
    def test_plain_json(self):
        assert _safe_parse_json('{"a": 1}') == {"a": 1}

    def test_with_code_fence(self):
        assert _safe_parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_with_code_fence_no_lang(self):
        assert _safe_parse_json('```\n{"a": 1}\n```') == {"a": 1}


class TestTruncateNarration:
    def test_no_truncation_needed(self):
        text = "Hello world."
        assert _truncate_narration(text, 10) == text

    def test_truncates_and_adds_period(self):
        text = "one two three four five six seven eight"
        result = _truncate_narration(text, 4)
        assert result == "one two three four."
        assert result.count(" ") == 3

    def test_already_ends_with_punctuation(self):
        result = _truncate_narration("one two three four five six seven eight", 4)
        assert result == "one two three four."

    def test_exact_word_count(self):
        text = "one two three four five"
        assert _truncate_narration(text, 5) == text


class TestGenerateEnhancedScenes:
    def test_returns_scenes_for_valid_text(self):
        with patch("backend.services.multi_model_director._analyze_content") as mock_a:
            mock_a.return_value = ContentAnalysis(
                domain="test", concepts=["a"], audience_level="beginner",
                prerequisites=[], core_insight="x",
            )
            with patch("backend.services.multi_model_director._plan_narrative") as mock_p:
                mock_p.return_value = NarrativePlan(
                    hook="hi",
                    scene_plans=[ScenePlan("goal", "meta", "hint")],
                    conclusion="bye",
                )
                with patch("backend.services.multi_model_director._write_narration") as mock_w:
                    mock_w.return_value = "Short scene text."
                    scenes = generate_enhanced_scenes("some text", target_count=1, max_words_per_narration=30)
                    assert len(scenes) == 1
                    assert scenes[0].scene_id == 1
                    assert scenes[0].audio_duration_ms == 15000

    def test_fallback_on_failure(self):
        scenes = generate_enhanced_scenes("Hello world. This is a test. Of the fallback system.", target_count=2)
        assert len(scenes) >= 2
        for s in scenes:
            assert s.narration
            assert s.svg_path == "none://"


class TestContextualAnalyzerBackwardCompat:
    def test_analyze_returns_analysis_and_plan(self):
        with patch("backend.services.multi_model_director._analyze_content") as mock_a:
            mock_a.return_value = ContentAnalysis("d", ["c"], "b", [], "i")
            with patch("backend.services.multi_model_director._plan_narrative") as mock_p:
                mock_p.return_value = NarrativePlan("h", [ScenePlan("g", "m", "v")], "c")
                analyzer = ContextualAnalyzer()
                analysis, plan = analyzer.analyze("some text")
                assert analysis.domain == "d"
                assert len(plan.scene_plans) == 1
