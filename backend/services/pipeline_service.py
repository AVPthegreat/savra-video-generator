from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore
from time import perf_counter
from typing import Any

from backend.core.config import get_settings
from backend.core.schemas import RenderProps, SceneChoreography, SceneScript
from backend.db import crud
from backend.db.database import SessionLocal
from backend.services.audio_gen import synthesize
from backend.services.multi_model_director import generate_enhanced_scenes
from backend.services.parser import chunk_text, smart_sample_text
from backend.services.storage_service import get_storage_provider

from threading import BoundedSemaphore, Lock

logger = logging.getLogger(__name__)


def calculate_scene_count(text: str) -> int:
    """Derive scene count for a 60-90s video: 4–6 scenes, ~15-22s each."""
    words = len(text.split())
    duration_s = (words / 130) * 60
    count = int(duration_s / 12)
    return max(4, min(count, 6))


# Scene generator is now exclusively the multi-model director
_generate_scenes = generate_enhanced_scenes


# ── ENGINE INITIALIZATION ──────────────────────────────────────────────────
_settings = get_settings()
_storage = get_storage_provider(_settings)
_JOB_EXECUTOR = ThreadPoolExecutor(
    max_workers=_settings.job_worker_count,
    thread_name_prefix="job",
)
_RENDER_LIMITER = BoundedSemaphore(value=_settings.max_concurrent_renders)
# Global lock to prevent simultaneous binary launches (prevents ETXTBSY)
_LAUNCH_LOCK = Lock()

@contextmanager
def _timed_stage(job_id: str, stage: str) -> Any:
    start = perf_counter()
    try:
        yield
    finally:
        duration_ms = int((perf_counter() - start) * 1000)
        logger.info("perf job_id=%s stage=%s duration_ms=%s", job_id, stage, duration_ms)

def _synthesize_scene_choreography(
    scene: SceneScript,
    audio_dir: Path,
    run_token: str,
    enhanced: SceneChoreography | None = None,
    pre_fetched_svg: str | None = None,
) -> SceneChoreography:
    """Synthesize audio and return a fully-populated SceneChoreography.

    When `enhanced` is provided (multi-model path), its svg/timing data is
    preserved and only the audio is freshly synthesized.
    When `enhanced` is None (classic path), svg comes from pre_fetched_svg
    (already deduped) or falls back to a fresh Iconify fetch.
    """
    audio_filename = f"scene_{scene.scene_id}.mp3"
    audio_abs_path = audio_dir / audio_filename
    duration_ms = synthesize(scene.narration, str(audio_abs_path))
    remote_path = f"runs/{run_token}/audio/{audio_filename}"
    accessible_url = _storage.upload_file(audio_abs_path, remote_path)

    if enhanced:
        # Multi-model path: carry over pre-computed assets, timing, and canvas spatial data
        return SceneChoreography(
            scene_id=scene.scene_id,
            narration=scene.narration,
            on_screen_text=scene.on_screen_text,
            svg_markup=enhanced.svg_markup,
            metaphor_hint=enhanced.metaphor_hint,
            audio_path=accessible_url,
            svg_path=enhanced.svg_path,
            svg_content=enhanced.svg_content,
            audio_duration_ms=duration_ms,
            draw_start_ms=enhanced.draw_start_ms,
            draw_duration_ms=enhanced.draw_duration_ms,
            hold_ms=enhanced.hold_ms,
            canvas_x=enhanced.canvas_x,
            canvas_y=enhanced.canvas_y,
            canvas_width=enhanced.canvas_width,
            canvas_height=enhanced.canvas_height,
            layout_direction=enhanced.layout_direction,
            kinetic_words=enhanced.kinetic_words,
        )

    # Classic path — text-only fallback (no SVG/icon fetching).
    # The renderer handles text-only scenes gracefully.
    return SceneChoreography(
        scene_id=scene.scene_id,
        narration=scene.narration,
        on_screen_text=scene.on_screen_text,
        svg_markup="",
        metaphor_hint=scene.metaphor_hint,
        audio_path=accessible_url,
        svg_path="none://",
        svg_content="",
        audio_duration_ms=duration_ms,
        draw_start_ms=0,
        draw_duration_ms=duration_ms,
        hold_ms=0,
        canvas_x=0,
        canvas_y=0,
        canvas_width=1920,
        canvas_height=1080,
        layout_direction="right",
        kinetic_words=[],
    )


def _generate_render_props_internal(
    extracted_text: str,
    run_id: str
) -> RenderProps:
    settings = get_settings()
    scene_count = calculate_scene_count(extracted_text)
    max_words_per_narration = max(10, 195 // scene_count)
    sampled_text = smart_sample_text(extracted_text, max_chars=settings.max_input_chars)
    chunks = chunk_text(sampled_text)

    if not chunks:
        raise ValueError("No text content available to generate scenes")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_dir = Path(tmp_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Generate scenes using the multi-stage LLM pipeline
        enhanced_scenes = generate_enhanced_scenes(
            sampled_text,
            scene_count,
            max_words_per_narration,
        )

        if not enhanced_scenes:
            raise ValueError("Pipeline generated zero scenes — check LLM or validation")

        # Build SceneScript list for audio synthesis
        raw_scenes = [
            SceneScript(
                scene_id=s.scene_id,
                narration=s.narration,
                on_screen_text=s.on_screen_text,
                metaphor_hint=s.metaphor_hint
            ) for s in enhanced_scenes
        ]

        # Synthesize audio and assemble full SceneChoreography
        try:
            choreography_scenes = []
            for scene in raw_scenes:
                enhanced = next((s for s in enhanced_scenes if s.scene_id == scene.scene_id), None)
                if enhanced:
                    choreo = _synthesize_scene_choreography(scene, audio_dir, run_id, enhanced=enhanced)
                    choreography_scenes.append(choreo)
                else:
                    choreo = _synthesize_scene_choreography(scene, audio_dir, run_id)
                    choreography_scenes.append(choreo)
        except Exception as e:
            logger.error(f"Scene generation failed: {e}")
            raise

        choreography_scenes.sort(key=lambda s: s.scene_id)
        props = RenderProps(scenes=choreography_scenes)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(props.model_dump(), f, indent=2)
            f_path = Path(f.name)
        try:
            _storage.upload_file(f_path, f"runs/{run_id}/render_props.json")
        finally:
            f_path.unlink(missing_ok=True)

        return props

def _render_scene_group(
    group_idx: int,
    scenes: list[SceneChoreography],
    job_id: str,
    renderer_dir: Path,
    tmp_dir: Path,
    concurrency: int = 1,
) -> Path:
    """Render one group of scenes as a single chunk MP4."""
    sanitized_scenes: list[dict] = []
    for scene in scenes:
        scene_dict = scene.model_dump()
        path = scene_dict.get("audio_path", "")
        # Strip prefixes so Remotion finds them in public/
        for prefix in ["/artifacts/", "/local-artifacts/", "artifacts/", "local-artifacts/"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
        scene_dict["audio_path"] = path.lstrip("/")
        sanitized_scenes.append(scene_dict)

    props_dict = {"fps": 30, "width": 1920, "height": 1080, "scenes": sanitized_scenes}
    props_path = tmp_dir / f"chunk_{group_idx}_props.json"
    props_path.write_text(json.dumps(props_dict, indent=2))

    output_path = tmp_dir / f"chunk_{group_idx}.mp4"
    command = [
        "node_modules/.bin/remotion", "render",
        "src/Root.tsx", "Whiteboard",
        f"--props={props_path}",
        f"--concurrency={concurrency}",
        "--chromium-flags=--no-sandbox",
        str(output_path),
    ]

    try:
        # Use Global Launch Lock to prevent ETXTBSY
        with _LAUNCH_LOCK:
            logger.info("job_id=%s chunk=%s status=launching_engine", job_id, group_idx)
            # Short sleep inside lock to ensure OS has fully released the binary from any previous run
            import time
            time.sleep(0.5) 
            subprocess.run(command, cwd=renderer_dir, check=True, capture_output=True, text=True)
        
        # Verify chunk integrity immediately
        if not output_path.exists() or output_path.stat().st_size < 1000:
            raise RuntimeError(f"Chunk {group_idx} generated an empty or invalid video file.")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip().split('\n')[-3:] 
        logger.error("Remotion render failed (chunk %s). Stderr: %s", group_idx, e.stderr)
        raise RuntimeError(f"Render Engine Error (Chunk {group_idx}): {' | '.join(error_msg)}") from e
    return output_path

def _stitch_videos_ffmpeg(chunk_videos: list[Path], output_path: Path) -> None:
    concat_list = output_path.parent / "concat_list.txt"
    concat_list.write_text("\n".join(f"file '{v.resolve()}'" for v in chunk_videos), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(output_path)], check=True)

def _run_remotion_render(job_id: str, props: RenderProps) -> str:
    renderer_dir = Path(__file__).resolve().parent.parent.parent / "renderer"
    output_filename = f"{job_id}.mp4"
    
    import time
    n_groups = 2
    chunk_size = max(1, -(-len(props.scenes) // n_groups))
    groups = [props.scenes[i: i + chunk_size] for i in range(0, len(props.scenes), chunk_size)]

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        chunk_videos: dict[int, Path] = {}

        with ThreadPoolExecutor(max_workers=n_groups) as pool:
            futures = {}
            for i, g in enumerate(groups):
                if not g: continue
                # Staggered launch to reduce lock contention
                if i > 0:
                    time.sleep(1.0)
                futures[pool.submit(_render_scene_group, i, g, job_id, renderer_dir, tmp, concurrency=6)] = i
            
            for future in as_completed(futures):
                try:
                    chunk_videos[futures[future]] = future.result()
                except Exception as e:
                    logger.error(f"Render job {job_id} aborted due to chunk failure: {e}")
                    raise

        ordered_chunks = [chunk_videos[i] for i in sorted(chunk_videos)]
        stitch_local = tmp / "stitched.mp4"
        _stitch_videos_ffmpeg(ordered_chunks, stitch_local)
        
        if not stitch_local.exists() or stitch_local.stat().st_size < 5000:
            raise RuntimeError("Render Engine Error: Final video is empty or missing.")

        remote_path = f"runs/{output_filename}"
        accessible_url = _storage.upload_file(stitch_local, remote_path)

    return accessible_url

def start_background_job(job_id: str, user_id: int | None, text: str, render: bool):
    _JOB_EXECUTOR.submit(_background_job_worker, job_id, user_id, text, render)

def _background_job_worker(job_id: str, user_id: int | None, text: str, render: bool):
    db = SessionLocal()
    try:
        crud.set_job_running(db, job_id)
        props = _generate_render_props_internal(text, job_id)
        crud.create_scenes(db, job_id, [s.model_dump() for s in props.scenes])
        if render:
            crud.update_job_status(db, job_id, "rendering")
            with _RENDER_LIMITER:
                video_url = _run_remotion_render(job_id, props)
                db.expire_all()
                crud.create_video(db, job_id, video_url)
        crud.set_job_completed(db, job_id)
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        # Store detailed error message in DB
        error_msg = str(exc)
        if "Render Engine Error" in error_msg:
             error_msg = f"Video Engine Failure: {error_msg}"
        crud.set_job_failed(db, job_id, error_msg)
    finally:
        db.close()
