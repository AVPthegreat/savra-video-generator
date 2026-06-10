# Savra Video Generator API Contracts

This document details the exact REST API contracts exposed by the Savra Video Generator FastAPI backend.

**Base URL:** `http://localhost:8000` (Local) / `https://<cloud-run-url>` (Production)
**Authentication:** Endpoints require a `Bearer <token>` in the `Authorization` header if `ENABLE_AUTH=true` in the environment.

---

## 1. System Health & Metrics

### `GET /healthz`
Validates that the server is running.
**Auth Required:** No
**Response (200 OK):**
```json
{
  "status": "ok"
}
```

### `GET /metrics`
Lightweight operational metrics for queue and worker monitoring.
**Auth Required:** Yes
**Response (200 OK):**
```json
{
  "queue_capacity": 50,
  "worker_count": 4,
  "max_concurrent_renders": 2,
  "jobs": {
    "completed": 12,
    "running": 1,
    "queued": 0
  }
}
```

---

## 2. Document Processing

### `POST /upload`
Extracts text from uploaded documents (`.pdf`, `.docx`, `.txt`) and splits it into semantic chunks.
**Auth Required:** Yes
**Content-Type:** `multipart/form-data`
**Request Body:**
*   `file`: The binary file payload (Max size enforced by `MAX_UPLOAD_MB`).

**Response (200 OK):**
```json
{
  "extracted_text": "Full extracted string content...",
  "chunk_count": 4
}
```
**Errors:**
*   `400 Bad Request`: Unsupported file type.
*   `413 Request Entity Too Large`: File exceeds size limits.

---

## 3. Video Generation Pipeline

### `POST /generate/async`
Queues a background job to convert text into a rendered whiteboard animation.
**Auth Required:** Yes
**Content-Type:** `application/json`
**Request Body:**
```json
{
  "extracted_text": "String content to animate...", 
  "max_scenes": 6, 
  "render_video": true
}
```
*(Note: `max_scenes` is optional, must be between 1 and 8. `render_video` defaults to true).*

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4e5f678901234567890abcdef",
  "status": "queued"
}
```
**Errors:**
*   `413 Request Entity Too Large`: Text exceeds `MAX_INPUT_CHARS`.
*   `429 Too Many Requests`: Job queue capacity is full.

---

### `GET /jobs/{job_id}`
Polls the status of a generation job and retrieves the final artifacts.
**Auth Required:** Yes
**Path Parameter:** `job_id` (32-character hex string)

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4e5f678901234567890abcdef",
  "status": "completed", 
  "created_at": "2026-04-24T12:00:00.000Z",
  "updated_at": "2026-04-24T12:02:15.000Z",
  "error": null,
  "video_path": "runs/a1b2c3d4e5f678901234567890abcdef.mp4",
  "render_props": {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "scenes": [
      {
        "scene_id": 1,
        "narration": "What is Bitcoin?",
        "svg_markup": "<svg>...</svg>",
        "metaphor_hint": "A digital coin.",
        "audio_path": "runs/.../scene_1.mp3",
        "svg_path": "inline://scene_1.svg",
        "svg_content": "<svg>...</svg>",
        "audio_duration_ms": 2500,
        "draw_start_ms": 0,
        "draw_duration_ms": 1000,
        "hold_ms": 1500
      }
    ]
  }
}
```
*(Note: `status` can be "queued", "running", "completed", or "failed". If failed, the `error` field will contain a traceback or message).*

---

## 4. Artifact Retrieval

### `GET /artifacts/{path:path}`
Serves static artifacts (audio files, `.json` prop files, `.mp4` videos). 
*   **Local Env:** Serves directly from the local renderer `public` directory.
*   **Prod Env:** Automatically returns a `307 Temporary Redirect` to the Google Cloud Storage public URL.

**Auth Required:** No
**Response:** Binary file stream or 307 Redirect.
**Errors:** `404 Not Found` if the file doesn't exist locally.
