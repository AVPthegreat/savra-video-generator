"""Pydantic schemas shared across the document-to-video backend."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SceneScript(BaseModel):
    """LLM-authored scene script before timing and asset choreography."""

    scene_id: int = Field(..., ge=1)
    scene_title: str = Field(default="")
    narration: str = Field(..., min_length=1)
    on_screen_text: str = Field(..., min_length=1)
    svg_markup: str = Field(default="")  # populated by icon_fetcher, not the LLM
    metaphor_hint: str = Field(..., min_length=1)


class SceneChoreography(SceneScript):
    """Scene script enriched with resolved assets, timing, and infinite-canvas spatial metadata."""

    audio_path: str = Field(..., min_length=1)
    svg_path: str = Field(..., min_length=1)
    svg_content: str = Field(default="")  # empty string valid for text-only scenes
    audio_duration_ms: int = Field(..., ge=1)
    draw_start_ms: int = Field(..., ge=0)
    draw_duration_ms: int = Field(..., ge=0)
    hold_ms: int = Field(..., ge=0)

    # Infinite-canvas spatial coordinates (pixels in the canvas world)
    canvas_x: int = Field(default=0, ge=0)
    canvas_y: int = Field(default=0, ge=0)
    canvas_width: int = Field(default=1920, ge=1)
    canvas_height: int = Field(default=1080, ge=1)
    layout_direction: str = Field(default="right")
    kinetic_words: list[str] = Field(default_factory=list)

    # Secondary SVG for dual-illustration layout (optional)
    svg_content_secondary: str | None = Field(default=None)
    svg_path_secondary: str | None = Field(default=None)


class RenderProps(BaseModel):
    """Remotion composition props for rendering the final whiteboard video."""

    fps: int = Field(default=30, ge=1)
    width: int = Field(default=1920, ge=1)
    height: int = Field(default=1080, ge=1)
    scenes: list[SceneChoreography] = Field(default_factory=list)
