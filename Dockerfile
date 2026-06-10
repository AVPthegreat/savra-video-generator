FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Let Remotion/Puppeteer find Chromium in the system path
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV CHROMIUM_PATH=/usr/bin/chromium

WORKDIR /app

# Step 1: Install system dependencies including NodeSource for Node.js 20
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		chromium \
		curl \
		ffmpeg \
		ca-certificates \
		gnupg \
		libnss3 \
		libatk1.0-0 \
		libatk-bridge2.0-0 \
		libcups2 \
		libdrm2 \
		libxkbcommon0 \
		libxcomposite1 \
		libxdamage1 \
		libxrandr2 \
		libgbm1 \
		libasound2 \
	&& mkdir -p /etc/apt/keyrings \
	&& curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
	&& echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
	&& apt-get update \
	&& apt-get install nodejs -y \
	&& rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Pre-download MiniLM model at build time — baked into image layer.
# unDraw SVGs and index.json are NOT baked — fetched from GCS at startup.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('MiniLM model cached.')"

COPY backend /app/backend
COPY renderer /app/renderer
# assets/undraw/ and assets/index.json are gitignored — fetched from GCS at startup.
# Only create the directory here so the chown below works.
RUN mkdir -p /app/assets/undraw
COPY scripts /app/scripts

# Use npm ci for deterministic, reproducible installs from lockfile
RUN npm ci --prefix /app/renderer 2>/dev/null || npm install --prefix /app/renderer


RUN useradd --system --uid 10001 --create-home appuser \
	&& mkdir -p /app/renderer/runs /app/renderer/public/runs \
	&& chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
	CMD curl -f http://localhost:${PORT:-8080}/healthz || exit 1

# Use the PORT environment variable if provided (default to 8080 for Cloud Run)
# Run migrations first — fail loudly in production if migration fails
CMD ["sh", "-c", "python /app/scripts/migrate_db.py && python /app/scripts/fetch_assets.py && uvicorn backend.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-8080}"]
