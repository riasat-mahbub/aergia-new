---
SCHEMA: 3
FORMAT: project-tracker
ID: ADR-01KYZ1XGGHXX9F2DW5HDXBBWMG
TYPE: adr
STATUS: DONE
SUMMARY: 'Why the database was migrated from PostgreSQL to SQLite and the trade-offs'
PRIORITY: null
SEVERITY: null
EFFORT: null
OWNER: null
CONFIDENCE: Medium
TAGS:
- adr
- architecture
- database
RELATIONS:
  related:
  - FEAT-01KYZ1HDBPMFG4G6HANFNCHJGA
AFFECTS:
  files:
  - api/app/db/session.py
  - docker-compose.yml
  - dev.sh
  - DEPLOY.md
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-01T16:18:34.641588+00:00'
UPDATED_AT: '2026-08-01T16:18:34.641588+00:00'
---

# ADR: PostgreSQL → SQLite migration

## Background

Why the database was migrated from PostgreSQL to SQLite and the trade-offs

The original architecture used PostgreSQL via `asyncpg`, requiring Docker
for local development (`docker compose up -d postgres`). This added a hard
dependency on Docker and slowed down onboarding: `dev.sh` had to start
Postgres, wait for health checks, and required Docker daemon access.

*Migrated from SCHEMA 2 entry 007-adr-sqlite-migration.md (status OPEN) on 2026-08-01.*

## Investigation


## Decision

Replace PostgreSQL with SQLite (`aiosqlite`) for both development and
production. The database is a single file at `data/aergia.db`, stored in
a Docker volume in production.

### Consequences

- **Zero-dependency local dev**: `./dev.sh` works out of the box
- **Simpler deployment**: single Docker service, no database container
- **Simpler backups**: single file copy instead of `pg_dump`
- **Lower resource requirements**: 1 vCPU, 1GB RAM minimum
- **Lost**: concurrent write capability (acceptable for single-user CV builder)
- **Lost**: PostgreSQL-specific features (JSONB indexing, full-text search)
- **Migration**: clean break — old PG migrations deleted, single fresh init

### Date

2026-07-26

## Implementation

- `asyncpg` → `aiosqlite` dependency
- 11 incremental PostgreSQL migrations replaced by a single `init_sqlite`
  auto-generated migration
- `docker-compose.yml`: `postgres` service removed, new `data` volume
- `dev.sh`: Docker checks, Postgres startup, and health-check wait removed
- `Dockerfile`: `mkdir -p /app/data` for SQLite file
- `DEPLOY.md`: backup simplified to `docker compose cp`, minimum specs
  reduced from 2 vCPU/4GB/50GB → 1 vCPU/1GB/20GB
- `session.py`: `check_same_thread=False` for async SQLite access
- Config `database_url` default changed to `sqlite+aiosqlite:///data/aergia.db`

## Verification


## Follow-up
