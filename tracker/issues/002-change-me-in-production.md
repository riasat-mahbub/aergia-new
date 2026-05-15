---
ID:             002
TYPE:           issue
NAME:           Default SECRET_KEY passes in dev but blocks prod
SUMMARY:        Default 'change-me-in-production' raises RuntimeError in production mode
STATUS:         CLOSED
TAGS:           security, config, intentional
LINKS:          decision=AGENTS.md
---

## Description

The default `SECRET_KEY=change-me-in-production` in `.env.example` passes
through in development mode but raises a `RuntimeError` in production mode.
This is an intentional safety check — documented in AGENTS.md and DEPLOY.md.
The deployment guide instructs to generate a real key with
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Status

Closed by design. Not a bug — intentional safety mechanism.
