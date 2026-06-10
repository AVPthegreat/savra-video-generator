from __future__ import annotations

import tempfile
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth.jwt import require_beta_authorized
from backend.db.models import User
from backend.db.database import get_db
from backend.db import crud
from backend.core.config import get_settings
from backend.services.parser import extract_text, chunk_text
from backend.services.pipeline_service import start_background_job
from pydantic import BaseModel, Field

router = APIRouter(prefix="/user", tags=["user"])

import json
from typing import Literal
from backend.core.schemas import RenderProps, SceneChoreography

class UploadResponse(BaseModel):
    extracted_text: str
    chunk_count: int

class GenerateRequest(BaseModel):
    extracted_text: str = Field(..., min_length=1)

JobStatus = Literal["queued", "running", "rendering", "completed", "failed"]

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    error: str | None = None
    render_props: RenderProps | None = None
    video_path: str | None = None

@router.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(require_beta_authorized),
):
    """Secure document upload (20MB limit)."""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        size_bytes = tmp_path.stat().st_size
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        size_mb = size_bytes / (1024 * 1024)
        if size_mb > 20: # Strictly 20MB
            raise HTTPException(status_code=413, detail="File too large (Max 20MB)")

        try:
            extracted = extract_text(str(tmp_path), max_file_size_mb=20)
            chunks = chunk_text(extracted)
            return UploadResponse(extracted_text=extracted, chunk_count=len(chunks))
        except ValueError as ve:
            # Handle "Document contains no extractable text" or other parser errors
            raise HTTPException(status_code=400, detail=str(ve))
    finally:
        tmp_path.unlink(missing_ok=True)

@router.post("/generate")
def generate(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_beta_authorized),
):
    """Queue a video generation (Admins have unlimited quota)."""
    
    # 1. Quota Check (Bypassed ONLY for Admins)
    if not current_user.is_admin:
        completed_count = crud.count_user_completed_jobs_last_24h(db, current_user.id)
        if completed_count >= 1:
            raise HTTPException(
                status_code=429, 
                detail="You have reached your daily limit (1 successful video per 24h). Please try again later."
            )
    
    job_id = uuid.uuid4().hex
    crud.create_job(db, job_id, user_id=current_user.id)
    
    # Start background process
    start_background_job(job_id, current_user.id, request.extracted_text, True)
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_beta_authorized),
):
    """Poll job status for the current user."""
    job = crud.get_job(db, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")

    # Reconstruct props from DB scenes
    scenes = crud.get_scenes(db, job_id)
    props = None
    if scenes:
        props = RenderProps(scenes=[
            SceneChoreography(
                scene_id=int(s.scene_index),
                narration=s.narration,
                on_screen_text=s.on_screen_text or " ".join(s.narration.split()[:6]) or s.narration,
                svg_markup=s.svg_markup,
                metaphor_hint=s.metaphor_hint,
                audio_path=s.audio_path,
                svg_path=s.svg_path or f"inline://scene_{s.scene_index}.svg",
                svg_content=s.svg_markup,
                audio_duration_ms=int(s.audio_duration_ms or 0),
                draw_duration_ms=int(s.draw_duration_ms or 0),
                draw_start_ms=0,
                hold_ms=max(0, int((s.audio_duration_ms or 0) - (s.draw_duration_ms or 0))),
                canvas_x=int(s.canvas_x or 0),
                canvas_y=int(s.canvas_y or 0),
                canvas_width=int(s.canvas_width or 1920),
                canvas_height=int(s.canvas_height or 1080),
                layout_direction=s.layout_direction or "right",
                kinetic_words=json.loads(s.kinetic_words_json or "[]"),
            ) for s in scenes
        ])

    video = crud.get_video(db, job_id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        error=job.error,
        render_props=props,
        video_path=video.file_path if video else None
    )

@router.post("/mark-onboarded")
def mark_onboarded(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_beta_authorized),
):
    """Set the flag so the user doesn't see the daily-limit pop-up again."""
    crud.mark_user_onboarded(db, current_user.id)
    return {"status": "ok"}
