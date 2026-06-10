"""End-to-end orchestration script from document upload to async job completion.

This script implements the modern async pipeline flow:
  1. Upload document → extract text
  2. Submit async generation job
  3. Poll for job completion
  4. Download or display result URL
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import requests

DEFAULT_API_URL = "http://127.0.0.1:8000"
POLL_INTERVAL_SECONDS = 5
MAX_POLL_DURATION_SECONDS = 1800  # 30 minutes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for input file path and generation settings."""

    parser = argparse.ArgumentParser(description="Document to whiteboard pipeline runner")
    parser.add_argument("--input", required=True, help="Path to source PDF/DOCX/TXT document")
    parser.add_argument("--max-scenes", type=int, default=12, help="Maximum number of scenes")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Base URL for backend API",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Bearer token for authentication (if ENABLE_AUTH=true)",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip video render, only generate scene props",
    )
    return parser.parse_args()


def _headers(token: str) -> dict[str, str]:
    """Build authorization headers if a token is provided."""
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def upload_document(api_url: str, input_path: Path, token: str) -> dict:
    """Upload the source document and return extracted text metadata."""

    try:
        with input_path.open("rb") as handle:
            response = requests.post(
                f"{api_url}/upload",
                files={"file": (input_path.name, handle, "application/octet-stream")},
                headers=_headers(token),
                timeout=180,
            )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.exception("Upload request failed")
        raise RuntimeError(f"Upload endpoint failed: {exc}") from exc


def submit_async_job(
    api_url: str, extracted_text: str, max_scenes: int, render_video: bool, token: str,
) -> str:
    """Submit an async generation job and return the job ID."""

    payload = {
        "extracted_text": extracted_text,
        "max_scenes": max_scenes,
        "render_video": render_video,
    }
    try:
        response = requests.post(
            f"{api_url}/generate/async",
            json=payload,
            headers={**_headers(token), "Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["job_id"]
    except requests.RequestException as exc:
        logger.exception("Generate async request failed")
        raise RuntimeError(f"Generate endpoint failed: {exc}") from exc


def poll_job(api_url: str, job_id: str, token: str) -> dict:
    """Poll the job status until completion or timeout."""

    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed > MAX_POLL_DURATION_SECONDS:
            raise TimeoutError(f"Job {job_id} did not complete within {MAX_POLL_DURATION_SECONDS}s")

        try:
            response = requests.get(
                f"{api_url}/jobs/{job_id}",
                headers=_headers(token),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as exc:
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                raise RuntimeError(f"Permanent HTTP error during polling: {exc}") from exc
            logger.warning("Poll request failed with HTTP error (will retry): %s", exc)
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        except requests.RequestException as exc:
            logger.warning("Poll request failed (will retry): %s", exc)
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        status = data.get("status", "unknown")
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(f"Job {job_id} failed: {data.get('error', 'Unknown error')}")

        logger.info("Job %s status: %s (%.0fs elapsed)", job_id, status, elapsed)
        time.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    """Run the full upload → async generate → poll pipeline."""

    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print("[1/4] Uploading document and extracting text...")
    upload_result = upload_document(args.api_url, input_path, args.token)
    extracted_text = upload_result.get("extracted_text", "")
    chunk_count = upload_result.get("chunk_count", 0)
    print(f"      Extracted text received. Chunks: {chunk_count}")

    print("[2/4] Submitting async generation job...")
    job_id = submit_async_job(
        args.api_url, extracted_text, args.max_scenes,
        render_video=not args.no_render, token=args.token,
    )
    print(f"      Job queued: {job_id}")

    print("[3/4] Polling for completion...")
    result = poll_job(args.api_url, job_id, args.token)
    scene_count = len(result.get("render_props", {}).get("scenes", []))
    print(f"      Job completed. Scenes: {scene_count}")

    video_path = result.get("video_path")
    if video_path:
        print(f"[4/4] Video available at: {video_path}")
    else:
        print("[4/4] No video render requested or render skipped.")

    print("\nPipeline finished successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline execution failed")
        raise SystemExit(1) from exc
