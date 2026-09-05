---
SCHEMA: 4
FORMAT: project-tracker
ID: ADR-01M1SV2ZZ2P7JPRCX87AS4N7VE
TYPE: adr
STATUS: PLANNED
PRIORITY: Medium
SEVERITY: null
EFFORT: M
OWNER: null
CONFIDENCE: Medium
TAGS:
- architecture
- repository-structure
- frontend
RELATIONS:
  related:
  - TASK-01M1SV2RPD9SXKF5N9ADSC22GR
AFFECTS:
  files:
  - web/src/routes/
  - web/src/features/
  - web/src/shared/
  - tailoring-skill/
  - api/app/document_schema/
  - api/app/http_schemas/
LINKS: null
VERIFIED_BY: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-05T22:30:07.586762+00:00'
UPDATED_AT: '2026-09-05T22:30:07.586762+00:00'
---

# Organize web code by routes, features, and shared layers

## Background

The web application will keep TanStack Start route registration under web/src/routes/. Product capabilities will live under web/src/features/<feature>/ with explicit index.ts public entrypoints. Cross-cutting reusable code will live under web/src/shared/. Routes own URL parameters, search validation, redirects, route context, and SSR settings; feature pages receive plain props. The root agent/ and contracts/ directories will move to tailoring-skill/ because they serve the tailoring workflow. Backend schema namespaces will be renamed to document_schema and http_schemas to distinguish AST/rendering models from HTTP DTOs. FastAPI Swagger and OpenAPI JSON will be exposed through the same-origin /api/docs and /api/openapi.json endpoints outside production.

## Investigation

The previous frontend layout mixed route registration, page implementations,
feature state, and reusable code under `web/src/app/`, `components/`, `lib/`,
`services/`, and `store/`. The tailoring skill and its contracts were also
split between two root directories. These names required contributors to read
large documents before they could identify ownership.

## Decision

Use TanStack Start's `web/src/routes/` directory only for route adapters and
move product code into explicit feature modules. Give each feature an
`index.ts` public entrypoint. Put cross-feature infrastructure in
`web/src/shared/`. Move the tailoring skill and its contracts into one
`tailoring-skill/` subtree. Rename backend schema namespaces so the document
AST and HTTP DTOs are distinguishable. Expose FastAPI's OpenAPI JSON and
Swagger UI under the same-origin `/api` gateway in non-production environments.

## Implementation

See `docs/plans/2026-09-05-self-documenting-repository-structure.md`.

## Verification

The implementation must pass the frontend boundary checker, TypeScript build,
backend schema/codegen drift check, focused OpenAPI tests, and the existing
smoke gate.

## Follow-up
