# Aergia portfolio showcase

This folder is a disposable capture harness for the portfolio product tour. It
starts an isolated Aergia instance, seeds fictional data through the public
API, records a Playwright browser flow, and emits portfolio-ready media.

The showcase intentionally keeps the account under Aergia's free-account quota:
one authored CV, one application-generated CV, and one imported CV.

The imported source is the fictional, parser-friendly
`fixtures/source-cv.html`. Each run renders it to a temporary PDF before the
browser imports it with the Modern template, so no personal CV or checked-in
binary is required.

The recording opens on a title card built from Aergia's emerald, mint, slate,
and off-white application palette. A short encoded-away preroll guarantees the
poster is fully painted before the first output frame. The disposable seed also
creates a valid short-lived tailoring session for the application detail scene;
its one-time capability is discarded without being printed or persisted.

## Prerequisites

- A completed frontend build in `web/.output` (the default command rebuilds it).
- `api/.venv` with Playwright and Chromium installed.
- `ffmpeg` and `ffprobe` on `PATH`.

## Run

From the repository root:

```bash
api/.venv/bin/python portfolio-showcase/run.py
```

Useful development modes:

```bash
api/.venv/bin/python portfolio-showcase/run.py --skip-build
api/.venv/bin/python portfolio-showcase/run.py --skip-build --headed
api/.venv/bin/python portfolio-showcase/run.py --dry-run
```

The normal command writes these ignored artifacts to `output/`:

- `aergia-showcase.mp4` — primary portfolio embed
- `aergia-showcase.webm` — web-friendly alternative
- `aergia-showcase.gif` — documentation and fallback version
- `aergia-showcase-poster.webp` — poster image

The API and web ports default to `8875` and `8876`. Override them when needed:

```bash
AERGIA_SHOWCASE_API_PORT=8975 AERGIA_SHOWCASE_WEB_PORT=8976 \
  api/.venv/bin/python portfolio-showcase/run.py --skip-build
```

## Storyboard

The recorded flow is intentionally outcome-oriented:

1. Intro card and value proposition.
2. CV dashboard and one reusable Maya Chen source CV.
3. PDF import with the Modern template, then continued editing of that same CV.
4. Builder content editing with immediate live preview.
5. Visible typography, heading-color, and section-background customization.
6. Reusing an experience from the Library.
7. Opening the Applications tab and the Northstar Systems application record.
8. Opening the generated CV and exporting PDF.
9. Outro card.

Edit scene copy and target pacing in `config/storyboard.json`. The interaction
selectors live in `src/capture.py`; they use accessible labels and the stable
section test IDs already present in the builder. The capture overlay moves to
the measured center of each target and emits a ripple before every scripted
click, making the interaction path legible in the final media.

## Safety boundaries

- Every run uses a temporary SQLite database and temporary upload directory.
- The normal development database is never opened.
- Demo credentials are generated in memory and are not printed.
- No external LLM key or tailoring capability is stored by this harness.
- The output directory contains generated media only and is ignored by Git.

If the product flow changes, run the `--dry-run` mode first. It exercises the
seed, import, builder, application, and export flow before spending time on
encoding.
