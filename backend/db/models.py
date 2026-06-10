"""ORM table definitions.

Tables:
  jobs    — one row per pipeline run (replaces the in-memory _job_store dict)
  scenes  — one row per scene within a job
  videos  — one row per rendered MP4
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Represents a registered user with specific access roles."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_beta_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    has_seen_onboarding: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    jobs: Mapped[list[Job]] = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class Job(Base):
    """Represents one end-to-end pipeline run."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)       # uuid hex
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")   # queued|running|completed|failed
    input_filename: Mapped[str] = mapped_column(String(255), default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="jobs")
    scenes: Mapped[list[Scene]] = relationship("Scene", back_populates="job", cascade="all, delete-orphan")
    video: Mapped[Video | None] = relationship("Video", back_populates="job", uselist=False, cascade="all, delete-orphan")


class Scene(Base):
    """One scene within a job — narration, SVG, audio timing, and infinite-canvas spatial data."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    scene_index: Mapped[int] = mapped_column(Integer)                    # 1-based
    narration: Mapped[str] = mapped_column(Text, default="")
    on_screen_text: Mapped[str] = mapped_column(Text, default="")
    svg_markup: Mapped[str] = mapped_column(Text, default="")
    metaphor_hint: Mapped[str] = mapped_column(Text, default="")
    audio_path: Mapped[str] = mapped_column(String(512), default="")
    svg_path: Mapped[str] = mapped_column(String(512), default="")    # illustration:// or inline://
    audio_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    draw_start_ms: Mapped[int] = mapped_column(Integer, default=0)
    draw_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    hold_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Infinite-canvas spatial coordinates
    canvas_x: Mapped[int] = mapped_column(Integer, default=0)
    canvas_y: Mapped[int] = mapped_column(Integer, default=0)
    canvas_width: Mapped[int] = mapped_column(Integer, default=1920)
    canvas_height: Mapped[int] = mapped_column(Integer, default=1080)
    layout_direction: Mapped[str] = mapped_column(String(32), default="right")
    kinetic_words_json: Mapped[str] = mapped_column(Text, default="[]")

    # Secondary SVG for dual-illustration layout
    svg_content_secondary: Mapped[str | None] = mapped_column(Text, nullable=True)
    svg_path_secondary: Mapped[str | None] = mapped_column(String(512), nullable=True)

    job: Mapped[Job] = relationship("Job", back_populates="scenes")


class Video(Base):
    """The rendered MP4 output for a job."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    file_path: Mapped[str] = mapped_column(String(512), default="")     # API-served relative artifact path
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    job: Mapped[Job] = relationship("Job", back_populates="video")