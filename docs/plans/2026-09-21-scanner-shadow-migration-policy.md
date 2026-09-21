# Scanner shadow migration and history policy

## Purpose

Populate and inspect fresh scanner results while the legacy relevance system
remains active. This is a shadow migration: it does not translate or rewrite
legacy analysis data and does not make scanner output authoritative for
application or tailoring consumers.

## Field policy

| Existing data | During shadow migration | At scanner cutover |
| --- | --- | --- |
| `application.relevance` | The existing legacy service may continue updating it. The backfill never reads it as scanner input or writes it. | Stop legacy writes and retain the final value as an inert legacy snapshot. Never convert it into `scanner_result`. |
| `application.algorithm_version` | Preserve the version written by legacy relevance. The backfill never changes it. | Retain it as legacy provenance; it does not identify any scanner subsystem version. |
| `application.quality` | Existing legacy quality writes continue until cutover. The backfill never changes it. | Preserve the last legacy result as historical data; do not reinterpret it as presentation-quality findings. |
| `application.extracted_keywords` | Existing legacy writes continue until cutover. The backfill never changes it. | Preserve the last legacy value; do not use it to seed scanner lexical analysis. |
| Relevance inside tailoring snapshots | Leave existing snapshots untouched. Existing tailoring consumers may continue using their current legacy contract during the shadow period. | Keep old snapshots immutable and versioned by their existing context. New tailoring work can consume scanner data after its separate migration. |
| `application.scanner_result` | Generate from the current job description and linked CV only. Store its input fingerprints and subsystem/scoring versions. | Becomes the scanner result contract after validation and consumer cutover. |

The scanner backfill is not a database migration. The nullable
`applications.scanner_result` column was added in Alembic revision
`o0p1q2r3`. No historical relevance, quality, keyword, or tailoring payload is
backfilled or transformed.

## Backfill behavior

The command considers applications with a nonblank job description and an
active, linked CV. It treats a `scanner-v1` result as current when its job and
CV fingerprints, installed matcher/lexical/quality/PDF/scoring versions, and
configured extractor model revision match. Current results are skipped by
default. Stale or absent results are scanned. `--only-missing` skips any
application that already has a result, even if stale; `--force` rescans all
scannable applications and cannot be combined with `--only-missing`.

`--dry-run` executes analysis but rolls back all writes. Each persisted
application result is committed independently so a failure does not undo
successful rows in the same batch. Failures report the application ID and
exception type, without logging CV content. Unscannable applications are
counted separately from scanner failures.

Run it from the API environment with the intended `DATABASE_URL`:

```bash
cd api
scanner-backfill --dry-run --batch-size 25
scanner-backfill --application-id <application-id>
scanner-backfill --only-missing
scanner-backfill --force
```

`--force` and `--only-missing` are mutually exclusive. The dry run performs
the scanner work but persists no `scanner_result` values.

The command writes only `scanner_result` and the application's ordinary
`updated_at` timestamp through the existing application scan service. It
leaves `relevance`, `algorithm_version`, `quality`, `extracted_keywords`, and
tailoring snapshots unchanged.

## Recalculation and history

Input edits invalidate `scanner_result`; they do not rewrite historical
scanner payloads into a different version. Use `--force` to explicitly
recalculate existing results after an algorithm or scoring-version change.
Every new result records independent extractor, matcher, lexical, quality,
PDF, and scoring versions so shadow data can be compared without assuming that
all results share identical semantics.

At consumer cutover, stop legacy relevance writes before removing legacy
services and UI. Retain existing legacy fields as inert history unless a
separate, explicit data-retention decision chooses to remove them. Tailoring
snapshot migration is not part of this shadow-backfill policy.
