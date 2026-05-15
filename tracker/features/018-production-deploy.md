---
ID:             018
TYPE:           feature
NAME:           Production deployment (Docker, rate limiting)
SUMMARY:        Docker multi-stage build, docker-compose, rate limiting, health checks
STATUS:         CLOSED
TAGS:           devops, phase-8
LINKS:          phase=COMPLETED.md-phase-8
---

## Description

Production-ready deployment:
- Docker Compose with postgres and api services
- Multi-stage Dockerfile (frontend builds inside API image)
- Single-origin: FastAPI serves both API and built SPA
- Rate limiting via slowapi (100 req/min global, 10 req/min on auth)
- Enhanced health check endpoint
- `dev.sh` with --prod/--build flags and playwright install
- DEPLOY.md with deployment instructions
- Uploads stored in Docker volume

## Status

All Phase 8 tasks complete.
