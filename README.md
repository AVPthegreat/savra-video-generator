# Savra Video Generator 🎥

An end-to-end, production-ready system that converts uploaded text documents (PDFs, DOCX, TXT) into beautifully animated, AI-narrated whiteboard-style tutorial videos.

**Author:** Anant Vardhan Pandey  
**Email:** dkpandeycan1@gmail.com  
**Repository:** [github.com/AVPthegreat/savra-video-generator](https://github.com/AVPthegreat/savra-video-generator)

## 🌟 System Architecture

The Savra Video Generator platform is a highly decoupled, asynchronous pipeline optimized for Google Cloud Run:

### 1. The Dashboard (`/frontend`)
- **Stack:** React 18, Vite, Tailwind CSS (Glassmorphism), TypeScript.
- **Role:** Handles Admin JWT authentication, drag-and-drop document uploads (with strict client & server size validation), and long-polling for real-time video generation status.
- **UX:** Premium dark-mode glass styling with animated feedback for API states.

### 2. The Orchestration API (`/backend`)
- **Stack:** Python 3.12, FastAPI, SQLAlchemy (SQLite/Cloud SQL), Alembic, Pydantic, gTTs.
- **Role:** The nerve center. 
  - **Parsing:** Extracts normalized text from complex file uploads (up to 20MB).
  - **Directing (LLM):** Prompts **Google Gemini (2.5 Flash)** to read the text and intelligently storyboard educational "scenes" (script + vector visual targets).
  - **Audio (TTS):** Asynchronously generates voiceovers.
  - **Queueing:** Manages concurrent job states via SQL, rate limits traffic, and safely executes isolated rendering subprocesses.

### 3. The Video Engine (`/renderer`)
- **Stack:** Node 20+, Remotion (`@remotion/cli`), React.
- **Role:** Consumes the `render_props.json` dropped by the backend, launches a multi-threaded Headless Chromium pipeline (Puppeteer), draws out the SVG paths dynamically, and encodes the exact visual timing into an `H.264` MP4 via FFmpeg.

---

## 🚀 Local Development Environment

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Docker** (Optional, but recommended for architecture parity)
- **Google Gemini API Key**

### 1. Setup Data Stores & Secrets
Duplicate the secure example files and inject your keys:
```bash
cp .env.example .env
cp .env.production.example .env.production
```
Make sure `GEMINI_API_KEY` is set inside your local `.env`. If you want to bypass local login, set `ENABLE_AUTH=false`.

### 2. Run the Stack Locally
You can boot all three core pillars by simply running the main API server locally. Assuming you have configured your python virtual environment:

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

> **Note:** For the backend to render videos successfully on your local Mac/PC, ensure `npx` and `@remotion/cli` dependencies are accessible in your environment PATH, or run `npm i` inside `/renderer`.

---

## ☁️ Google Cloud Deployment

This codebase is structurally hardened for **Google Cloud Run**. The pipeline automatically maps secrets, handles Nginx proxy routing, scales concurrency limits, and intercepts Chromium out-of-memory bounds.

### Pre-Deployment Checklist
1. Enable **Cloud Run**, **Cloud Build**, and **Secret Manager** on GCP.
2. Ensure you have provisioned the following Secrets in your project:
   - `GEMINI_API_KEY`
   - `DATABASE_URL` (Pointer to Cloud SQL Postgres)
   - `ADMIN_PASSWORD` (Must be a secure hash, `admin123` is blocked intentionally)
   - `JWT_SECRET` (Secure cryptographic string)

### Standard Deployment
Once your secrets are published, trigger the automated `cloudbuild.yaml` architecture:
```bash
gcloud builds submit --config cloudbuild.yaml
```

The config automatically provisions the exact specifications required for Remotion Headless Chromium tasks without breaching instance capacities:
- **vCPU:** 4
- **RAM:** 8Gi
- **Remotion Concurrency limit:** Flagged internally to exactly `4` rendering threads.

---

## 🛡️ Security Hardening & Observability

This platform enforces zero-compromise security configurations:
- **Guarded Boot:** The backend fundamentally refuses to boot in `APP_ENV=production` if weak fallback passwords (e.g., `admin123`) slip through from example configurations.
- **Real-IP Tracking:** Nginx load balancers preserve routing layers (via `X-Forwarded-For`) so backend rate limiters aggressively ban abusive bot clients attempting brute-force Auth cracks, rather than throttling the internal VPC loop.
- **Fail-Fast Error Handling:** Headless rendering bounds capture rigorous `TimeoutExpired` logic with complete log tracing appended to the API crash, preventing phantom memory-leak stalls.
- **Secure File Boundaries:** Hard thresholds exist natively on the Client-side (`20MB` chunk rejections target UI returns before network loads block up the internal ingress).
