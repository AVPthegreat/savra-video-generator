"""Offline semantic asset lookup using all-MiniLM-L6-v2 embeddings.

Loaded once at startup via lru_cache. Zero network calls at query time.
Falls back to an empty list (safely) if the index or model is unavailable.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Tiered thresholds for find_assets()
_THRESHOLD_HIGH   = float(os.environ.get("SEMANTIC_THRESHOLD", "0.55"))  # primary results
_THRESHOLD_MID    = 0.45  # fill remaining slots if < top_k above high
_THRESHOLD_MIN    = 0.35  # last-resort — never return empty if any hit above this

# Resolve index path:
#   1. ASSET_INDEX_PATH env var (absolute path — set in Cloud Run / .env)
#   2. Anchored fallback: <project_root>/assets/index.json
#      __file__ = .../backend/services/semantic_search.py  →  ../../assets/index.json
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_INDEX = _PROJECT_ROOT / "assets" / "index.json"
_INDEX_PATH = Path(os.environ.get("ASSET_INDEX_PATH", str(_DEFAULT_INDEX)))


def _try_fetch_from_gcs() -> bool:
    """Attempt to download index.json from GCS if missing locally. Returns True on success."""
    gcs_bucket = os.environ.get("GCS_ASSETS_BUCKET", "gs://savra-video-assets")
    bucket_name = gcs_bucket.removeprefix("gs://")
    try:
        from google.cloud import storage  # noqa: PLC0415
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("assets/index.json")
        _INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(_INDEX_PATH))
        logger.info("semantic_search: downloaded index.json from gs://%s/assets/index.json", bucket_name)
        return True
    except Exception as e:
        logger.warning("semantic_search: GCS fetch failed: %s — tier 1 disabled", e)
        return False


@lru_cache(maxsize=1)
def _load_index() -> tuple[list[dict], np.ndarray] | None:
    """Load index.json and stack embeddings into a matrix. Cached after first call."""
    if not _INDEX_PATH.exists():
        logger.warning("semantic_search: index not found at %s — attempting GCS fetch", _INDEX_PATH)
        if not _try_fetch_from_gcs():
            return None
    try:
        with open(_INDEX_PATH, encoding="utf-8") as f:
            entries = json.load(f)
        if not entries:
            logger.warning("semantic_search: index is empty")
            return None
        matrix = np.array([e["embedding"] for e in entries], dtype=np.float32)
        # Pre-normalise rows so dot product == cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        matrix = matrix / norms
        logger.info("semantic_search: loaded %d entries from index", len(entries))
        return entries, matrix
    except Exception as e:
        logger.error("semantic_search: failed to load index: %s", e)
        return None


@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the SentenceTransformer model."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        model = SentenceTransformer(_MODEL_NAME)
        logger.info("semantic_search: model loaded (%s)", _MODEL_NAME)
        return model
    except Exception as e:
        logger.error("semantic_search: model load failed: %s", e)
        return None


def find_assets(
    query: str,
    exclude_ids: list[str] | None = None,
    top_k: int = 3,
) -> list[dict]:
    """
    Find the top-k closest assets to the query using cosine similarity.

    Tiered thresholds (never returns empty if ANY match exists above 0.35):
      - Primary slot:  score >= 0.55 (SEMANTIC_THRESHOLD env override)
      - Fill slots:    score >= 0.45  (fills remaining slots up to top_k)
      - Last-resort:   score >= 0.35  (added only if list still has < 1 item)

    Returns list of dicts {"id", "path", "text", "embedding"} sorted by score
    descending, excluding exclude_ids. Returns [] if index/model unavailable.

    Args:
        query:       Search query string.
        exclude_ids: Asset IDs already used in this job — excluded from results.
        top_k:       Maximum number of results to return.
    """
    if not query or not query.strip():
        return []

    index_data = _load_index()
    if index_data is None:
        return []

    model = _get_model()
    if model is None:
        return []

    try:
        entries, matrix = index_data
        excluded = set(exclude_ids) if exclude_ids else set()

        qvec = model.encode(query.strip(), normalize_embeddings=True, show_progress_bar=False)
        sims = matrix @ qvec  # cosine similarity (both sides normalised)

        # Walk candidates from best to worst, skipping excluded IDs
        ranked = list(np.argsort(sims)[::-1])

        scored: list[tuple[float, dict]] = []
        for idx in ranked:
            entry = entries[idx]
            if entry.get("id") in excluded or entry.get("path") in excluded:
                continue
            scored.append((float(sims[idx]), entry))

        if not scored:
            return []

        best_score = scored[0][0]
        logger.info(
            "semantic_search: '%s' → best='%s' (score=%.3f)",
            query[:60], scored[0][1]["text"], best_score,
        )

        results: list[dict] = []

        # Pass 1: fill with scores >= HIGH threshold
        for score, entry in scored:
            if score < _THRESHOLD_HIGH:
                break
            results.append(entry)
            if len(results) >= top_k:
                break

        # Pass 2: fill remaining slots with scores >= MID threshold
        if len(results) < top_k:
            for score, entry in scored:
                if entry in results:
                    continue
                if score < _THRESHOLD_MID:
                    break
                results.append(entry)
                if len(results) >= top_k:
                    break

        # Pass 3: last-resort — include best result if still empty and score >= MIN
        if not results and scored[0][0] >= _THRESHOLD_MIN:
            results.append(scored[0][1])
            logger.info(
                "semantic_search: last-resort inclusion (score=%.3f >= %.2f)",
                scored[0][0], _THRESHOLD_MIN,
            )

        if not results:
            logger.info("semantic_search: below all thresholds (best=%.3f) — no match", best_score)

        return results

    except Exception as e:
        logger.warning("semantic_search: query failed: %s", e)
        return []


# ── Backwards-compatibility shim ──────────────────────────────────────────────
def find_asset(query: str, exclude_ids: list[str] | None = None) -> dict | None:
    """
    Legacy single-result wrapper around find_assets().
    Retained for any callers that still use the old signature.
    """
    results = find_assets(query, exclude_ids=exclude_ids, top_k=1)
    return results[0] if results else None
