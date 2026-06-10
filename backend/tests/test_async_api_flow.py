"""Integration-style API tests for async job queue and status endpoints."""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient


class _ImmediateExecutor:
    """Executor test double that runs submitted jobs synchronously."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

        class _DoneFuture:
            def result(self, timeout=None):  # noqa: ANN001
                return None

        return _DoneFuture()


class AsyncApiFlowTests(unittest.TestCase):
    """Validate async generation queueing and persisted status retrieval."""

    _original_env: dict[str, str | None]
    _env_keys = [
        "DATABASE_URL", "APP_ENV", "AUTO_CREATE_TABLES", "ENABLE_AUTH",
        "JOB_WORKER_COUNT", "JOB_QUEUE_CAPACITY", "MAX_CONCURRENT_RENDERS",
        "MAX_INPUT_CHARS",
    ]

    @classmethod
    def setUpClass(cls) -> None:
        cls._tempdir = tempfile.TemporaryDirectory()
        db_path = Path(cls._tempdir.name) / "test_async.db"

        # Save original environment so we can restore it later
        cls._original_env = {k: os.environ.get(k) for k in cls._env_keys}

        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["APP_ENV"] = "development"
        os.environ["AUTO_CREATE_TABLES"] = "true"
        os.environ["ENABLE_AUTH"] = "false"
        os.environ["JOB_WORKER_COUNT"] = "1"
        os.environ["JOB_QUEUE_CAPACITY"] = "3"
        os.environ["MAX_CONCURRENT_RENDERS"] = "1"
        os.environ["MAX_INPUT_CHARS"] = "10000"

        from backend.core.config import get_settings
        get_settings.cache_clear()

        import backend.main as main_module
        from backend.db.database import engine as db_engine

        cls.main = importlib.reload(main_module)
        cls._engine = db_engine
        from backend.db.database import create_all_tables
        create_all_tables()
        cls.client = TestClient(cls.main.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls._engine.dispose()
        cls._tempdir.cleanup()

        # Restore original environment
        for key, value in cls._original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        from backend.core.config import get_settings
        get_settings.cache_clear()

    def test_generate_async_and_fetch_job_status(self) -> None:
        """Queue an async job and verify persisted completed state + artifact path."""

        def _fake_run_job(job_id: str, text: str, max_sc: int, render: bool) -> None:
            db = self.main.SessionLocal()
            try:
                self.main.crud.set_job_running(db, job_id)
                self.main.crud.create_scenes(
                    db,
                    job_id=job_id,
                    choreography_scenes=[
                        {
                            "scene_id": 1,
                            "narration": "Intro narration",
                            "svg_content": "<svg viewBox='0 0 400 300'></svg>",
                            "metaphor_hint": "simple hint",
                            "audio_path": "public/runs/test/audio/scene_1.mp3",
                            "audio_duration_ms": 1200,
                            "draw_duration_ms": 480,
                        }
                    ],
                )
                if render:
                    self.main.crud.create_video(
                        db,
                        job_id=job_id,
                        file_path="artifacts/runs/test.mp4",
                    )
                self.main.crud.set_job_completed(db, job_id)
            finally:
                db.close()

        with mock.patch.object(self.main, "_background_job", side_effect=_fake_run_job):
            with mock.patch.object(self.main, "_JOB_EXECUTOR", _ImmediateExecutor()):
                response = self.client.post(
                    "/generate/async",
                    json={
                        "extracted_text": "Short extracted text for integration test.",
                        "max_scenes": 1,
                        "render_video": True,
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "queued")
        self.assertTrue(payload["job_id"])

        status_response = self.client.get(f"/jobs/{payload['job_id']}")
        self.assertEqual(status_response.status_code, 200)
        status_payload = status_response.json()

        self.assertEqual(status_payload["status"], "completed")
        self.assertEqual(status_payload["video_path"], "artifacts/runs/test.mp4")
        self.assertEqual(len(status_payload["render_props"]["scenes"]), 1)

    def test_generate_async_rejects_oversized_text(self) -> None:
        """Reject requests that exceed MAX_INPUT_CHARS before queueing work."""

        large_payload = "x" * 10001
        response = self.client.post(
            "/generate/async",
            json={
                "extracted_text": large_payload,
                "max_scenes": 1,
                "render_video": False,
            },
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("too large", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
