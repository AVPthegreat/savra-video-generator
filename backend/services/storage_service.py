"""Abstraction layer for artifact storage (Local vs GCS)."""

from __future__ import annotations

import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Base interface for all storage backends."""

    @abstractmethod
    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        """Upload a file and return its public or relative access URL."""
        pass

    @abstractmethod
    def get_url(self, remote_rel_path: str) -> str:
        """Return the accessible URL for a given relative path."""
        pass


class LocalStorageProvider(StorageProvider):
    """Provider for local filesystem storage (Development)."""

    def __init__(self, base_dir: Path, public_url_prefix: str = "/artifacts"):
        self.base_dir = base_dir
        self.public_url_prefix = public_url_prefix
        logger.info("LocalStorageProvider initialized at %s", base_dir)

    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        """Copy file to the local public directory with robust traversal protection."""
        base_dir_resolved = self.base_dir.resolve()
        # lstrip slashes to ensure we join as a relative path
        dest_path = (base_dir_resolved / remote_rel_path.lstrip("/")).resolve()
        
        # Ensure the resolved destination is strictly within the base directory
        if not dest_path.is_relative_to(base_dir_resolved):
            raise ValueError(f"Security Warning: Path traversal attempt blocked: {remote_rel_path}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        logger.info("Local Storage (Secured): %s -> %s", local_path, dest_path)
        
        return self.get_url(remote_rel_path)

    def get_url(self, remote_rel_path: str) -> str:
        # Strip 'public/' if it exists in the path for the URL
        if remote_rel_path.startswith("public/"):
            remote_rel_path = remote_rel_path[len("public/") :]
        return f"{self.public_url_prefix}/{remote_rel_path.lstrip('/')}"


class GcsStorageProvider(StorageProvider):
    """Provider for Google Cloud Storage (Production)."""

    def __init__(self, bucket_name: str):
        # Lazy import — only needed in production; avoids ImportError in dev
        from google.cloud import storage

        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        logger.info("GcsStorageProvider initialized for bucket: %s", bucket_name)

    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        """Upload to GCS with content-type detection and retry."""
        import mimetypes

        blob = self.bucket.blob(remote_rel_path)

        # Set content type based on file extension
        content_type, _ = mimetypes.guess_type(str(local_path))
        if content_type:
            blob.content_type = content_type

        # Set cache control for audio/video assets
        if remote_rel_path.endswith((".mp3", ".mp4", ".wav")):
            blob.cache_control = "public, max-age=3600"

        blob.upload_from_filename(str(local_path), timeout=300)
        logger.info("Uploaded %s to gs://%s/%s", local_path, self.bucket_name, remote_rel_path)
        return self.get_url(remote_rel_path)

    def get_url(self, remote_rel_path: str) -> str:
        return f"artifacts/{remote_rel_path.lstrip('/')}"


def get_storage_provider(settings: Any) -> StorageProvider:
    """Factory to return the correct provider based on settings."""
    if settings.app_env.lower() == "production" and settings.gcs_bucket_name:
        logger.info("Using GCS Storage Provider (bucket: %s)", settings.gcs_bucket_name)
        return GcsStorageProvider(settings.gcs_bucket_name)
    
    logger.info("Using Local Storage Provider")
    # For local, 'base_dir' is typically '../renderer/public'
    # We use an absolute path to ensure clarity in Docker
    backend_root = Path(__file__).resolve().parent.parent
    renderer_public = backend_root.parent / "renderer" / "public"
    
    # In Docker, we might have a specific mount point for artifacts
    # For now, we use the renderer's public dir so Remotion sees it instantly
    return LocalStorageProvider(renderer_public)
