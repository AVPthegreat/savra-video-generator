"""CRUD helpers — these replace the in-memory _job_store dict in main.py.

Usage in main.py:
    from backend.db.database import get_db
    from backend.db import crud

    @app.post("/generate/async")
    def generate_async(request: GenerateRequest, db: Session = Depends(get_db)):
        job = crud.create_job(db, job_id=uuid.uuid4().hex, ...)
        ...

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str, db: Session = Depends(get_db)):
        job = crud.get_job(db, job_id)
        ...
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.db.models import Job, Scene, User, Video

logger = logging.getLogger(__name__)

# ── User ──────────────────────────────────────────────────────────────────────

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def list_users(db: Session, limit: int = 100) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).limit(limit).all()

def update_user_beta_access(db: Session, user_id: int, authorized: bool) -> User | None:
    user = db.get(User, user_id)
    if user:
        user.is_beta_authorized = authorized
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False

def mark_user_onboarded(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if user:
        user.has_seen_onboarding = True
        db.commit()

def count_user_completed_jobs_last_24h(db: Session, user_id: int) -> int:
    """Count how many jobs this user completed in the last 24 hours."""
    from datetime import datetime, timedelta, timezone
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return db.query(Job).filter(
        Job.user_id == user_id,
        Job.status == "completed",
        Job.created_at >= since
    ).count()

# ── Job ───────────────────────────────────────────────────────────────────────

def create_job(db: Session, job_id: str, user_id: int | None = None, input_filename: str = "") -> Job:
    """Insert a new job row with status=queued."""
    job = Job(id=job_id, user_id=user_id, status="queued", input_filename=input_filename)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> Job | None:
    """Fetch a job by ID. Returns None if not found."""
    return db.get(Job, job_id)


def list_jobs(db: Session, limit: int = 50) -> list[Job]:
    """Return the most recent jobs, newest first."""
    return db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()


def recover_incomplete_jobs(db: Session, reason: str) -> int:
    """Mark queued/running jobs as failed after an unclean shutdown."""

    now = datetime.now(timezone.utc)
    updated = (
        db.query(Job)
        .filter(Job.status.in_(["queued", "running"]))
        .update(
            {
                Job.status: "failed",
                Job.error: reason,
                Job.updated_at: now,
            },
            synchronize_session="fetch",
        )
    )
    db.commit()
    return int(updated or 0)


def _set_job_status(db: Session, job_id: str, status: str, error: str | None = None) -> None:
    """Private helper: fetch job, update status/error/timestamp, commit."""
    job = db.get(Job, job_id)
    if not job:
        logger.error("_set_job_status: job %s not found — state transition skipped", job_id)
        return
    job.status = status
    if error is not None:
        job.error = error
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def set_job_running(db: Session, job_id: str) -> None:
    _set_job_status(db, job_id, "running")


def set_job_completed(db: Session, job_id: str) -> None:
    _set_job_status(db, job_id, "completed")


def set_job_failed(db: Session, job_id: str, error: str) -> None:
    _set_job_status(db, job_id, "failed", error=error)


def update_job_status(db: Session, job_id: str, status: str) -> None:
    _set_job_status(db, job_id, status)


# ── Scenes ────────────────────────────────────────────────────────────────────

def create_scenes(db: Session, job_id: str, choreography_scenes: list[dict]) -> list[Scene]:
    """Bulk-insert scene rows from a list of choreography dicts."""
    rows = [
        Scene(
            job_id=job_id,
            scene_index=s.get("scene_id", i + 1),
            narration=s.get("narration", ""),
            on_screen_text=s.get("on_screen_text", ""),
            svg_markup=s.get("svg_content", ""),
            metaphor_hint=s.get("metaphor_hint", ""),
            audio_path=s.get("audio_path", ""),
            svg_path=s.get("svg_path", ""),
            audio_duration_ms=s.get("audio_duration_ms", 0),
            draw_start_ms=s.get("draw_start_ms", 0),
            draw_duration_ms=s.get("draw_duration_ms", 0),
            hold_ms=s.get("hold_ms", 0),
            canvas_x=s.get("canvas_x", 0),
            canvas_y=s.get("canvas_y", 0),
            canvas_width=s.get("canvas_width", 1920),
            canvas_height=s.get("canvas_height", 1080),
            layout_direction=s.get("layout_direction", "right"),
            kinetic_words_json=json.dumps(s.get("kinetic_words", [])),
            svg_content_secondary=s.get("svg_content_secondary"),
            svg_path_secondary=s.get("svg_path_secondary"),
        )
        for i, s in enumerate(choreography_scenes)
    ]
    db.add_all(rows)
    db.commit()
    return rows


def get_scenes(db: Session, job_id: str) -> list[Scene]:
    return db.query(Scene).filter(Scene.job_id == job_id).order_by(Scene.scene_index).all()


# ── Video ─────────────────────────────────────────────────────────────────────

def create_video(db: Session, job_id: str, file_path: str, file_size_bytes: int = 0, duration_ms: int = 0) -> Video:
    video = Video(job_id=job_id, file_path=file_path, file_size_bytes=file_size_bytes, duration_ms=duration_ms)
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def get_video(db: Session, job_id: str) -> Video | None:
    return db.query(Video).filter(Video.job_id == job_id).first()