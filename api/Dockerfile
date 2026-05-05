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

COPY api/pyproject.toml .
RUN pip install --no-cache-dir -e ".[test]" && \
    playwright install chromium

COPY api/ .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Copy built frontend from Stage 1
COPY --from=frontend-build /build/dist /app/static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
