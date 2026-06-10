"""Utility to fetch secrets from Google Cloud Secret Manager."""

from __future__ import annotations

import os
import logging
from google.cloud import secretmanager
from google.api_core import exceptions

logger = logging.getLogger(__name__)

def get_secret(secret_id: str, project_id: str | None = None) -> str | None:
    """
    Fetch a secret value from GCP Secret Manager.
    Format: projects/{project_id}/secrets/{secret_id}/versions/latest
    """
    if not project_id:
        # Try to get from environment first (Cloud Run usually has this)
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    
    if not project_id:
        logger.warning("GOOGLE_CLOUD_PROJECT not set; cannot fetch secret %s", secret_id)
        return None

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except exceptions.PermissionDenied:
        logger.error("Permission denied accessing secret %s. Does the service account have 'Secret Manager Secret Accessor'?", secret_id)
    except exceptions.NotFound:
        logger.warning("Secret %s not found in project %s", secret_id, project_id)
    except Exception as exc:
        logger.exception("Unexpected error fetching secret %s", secret_id)

    return None
