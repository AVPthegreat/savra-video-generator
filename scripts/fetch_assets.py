"""
GCS asset sync — runs at container startup before uvicorn.

Uses the google-cloud-storage Python client (already in requirements.txt
via google-cloud-storage). No gsutil CLI needed.

Downloads:
  gs://savra-video-assets/assets/index.json  → $ASSET_INDEX_PATH
  gs://savra-video-assets/assets/undraw/*.svg → $ASSET_UNDRAW_DIR/

Skips files already present (size-based check) to keep restarts fast.
If GCS is unreachable (e.g. local dev without credentials), logs a warning
and continues — Tier 2 (Iconify) remains fully operational.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_assets")

# Strip gs:// prefix — the Python client uses bucket name + blob prefix separately
_RAW_BUCKET = os.environ.get("GCS_ASSETS_BUCKET", "gs://savra-video-assets")
GCS_BUCKET_NAME = _RAW_BUCKET.removeprefix("gs://")
GCS_INDEX_BLOB  = "assets/index.json"
GCS_UNDRAW_PREFIX = "assets/undraw/"

LOCAL_INDEX  = Path(os.environ.get("ASSET_INDEX_PATH", "/app/assets/index.json"))
LOCAL_UNDRAW = Path(os.environ.get("ASSET_UNDRAW_DIR",  "/app/assets/undraw"))


def _gcs_client():
    """Return a GCS client, or None if credentials/library unavailable."""
    try:
        from google.cloud import storage  # noqa: PLC0415
        return storage.Client()
    except Exception as e:
        logger.warning("fetch_assets: cannot initialise GCS client: %s", e)
        return None


def sync_index(client, bucket) -> bool:
    """Download index.json from GCS. Skip if already present and same size."""
    try:
        blob = bucket.blob(GCS_INDEX_BLOB)
        blob.reload()                        # fetch metadata
        remote_size = blob.size or 0

        if LOCAL_INDEX.exists() and LOCAL_INDEX.stat().st_size == remote_size:
            logger.info("fetch_assets: index.json already up-to-date (%d bytes)", remote_size)
            return True

        LOCAL_INDEX.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(LOCAL_INDEX))
        logger.info("fetch_assets: downloaded index.json (%d bytes)", remote_size)
        return True
    except Exception as e:
        logger.error("fetch_assets: index.json download failed: %s", e)
        return False


def sync_undraw(client, bucket) -> bool:
    """Sync unDraw SVGs from GCS prefix. Only downloads missing/changed files."""
    LOCAL_UNDRAW.mkdir(parents=True, exist_ok=True)
    try:
        blobs = list(client.list_blobs(bucket, prefix=GCS_UNDRAW_PREFIX))
        svg_blobs = [b for b in blobs if b.name.endswith(".svg")]
        if not svg_blobs:
            logger.warning("fetch_assets: no SVGs found at gs://%s/%s", GCS_BUCKET_NAME, GCS_UNDRAW_PREFIX)
            return False

        downloaded = 0
        skipped = 0
        for blob in svg_blobs:
            filename = Path(blob.name).name
            dest = LOCAL_UNDRAW / filename
            if dest.exists() and dest.stat().st_size == (blob.size or 0):
                skipped += 1
                continue
            blob.download_to_filename(str(dest))
            downloaded += 1

        logger.info(
            "fetch_assets: SVGs — %d downloaded, %d already present (%d total)",
            downloaded, skipped, len(svg_blobs),
        )
        return True
    except Exception as e:
        logger.error("fetch_assets: SVG sync failed: %s", e)
        return False


def main() -> int:
    client = _gcs_client()
    if client is None:
        logger.warning(
            "fetch_assets: GCS unavailable — Tier 1 (semantic search) disabled. "
            "Iconify (Tier 2) is still operational."
        )
        return 0  # Never block startup

    try:
        bucket = client.bucket(GCS_BUCKET_NAME)
        index_ok  = sync_index(client, bucket)
        undraw_ok = sync_undraw(client, bucket)

        if not index_ok or not undraw_ok:
            logger.warning(
                "fetch_assets: partial sync — Tier 1 may be degraded. Iconify (Tier 2) still operational."
            )
        else:
            logger.info("fetch_assets: all assets synced ✓")
    except Exception as e:
        logger.error("fetch_assets: unexpected error: %s", e)

    return 0  # Never fail startup


if __name__ == "__main__":
    sys.exit(main())
