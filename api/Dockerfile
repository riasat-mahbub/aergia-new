# Stage 1 — Build frontend
FROM node:20-alpine AS frontend-build

WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

# Stage 2 — Production image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 \
    libcairo2 libcups2t64 libdbus-1-3 libdrm2 \
    libgbm1 libnspr4 libnss3 libpango-1.0-0 \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright
ENV HF_HOME=/opt/huggingface

# Keep the production image on the CPU-only GLiNER2.5-small path. The model
# artifact is downloaded at build time, while Python model initialisation is
# still lazy at runtime.
ARG GLINER2_MODEL_REVISION=cab1bddfd30fda7b803a4691c41f90378a2d517a
ARG TORCH_VERSION=2.9.1+cpu
ENV GLINER2_MODEL_REVISION=${GLINER2_MODEL_REVISION}

COPY api/ .
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
      --no-deps "torch==${TORCH_VERSION}" && \
    python -m pip install --no-cache-dir -e ".[model]" && \
    playwright install chromium

RUN python -c 'import os; from gliner2 import AutoExtractor; AutoExtractor.from_pretrained("fastino/gliner2.5-small-v1", revision=os.environ["GLINER2_MODEL_REVISION"], map_location="cpu")'

# Create data directory for SQLite
RUN mkdir -p /app/data

# Copy built frontend from Stage 1
COPY --from=frontend-build /build/dist /app/static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
