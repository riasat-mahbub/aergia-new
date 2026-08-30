# Aergia tailoring protocol prototype

This package is the Phase 1 fixed-patch client. It does not invoke an LLM or
start a coding agent. It exchanges a one-time session code, downloads the
sanitized evidence packet, creates a deterministic test patch, and submits it
to the scoped tailoring endpoint.

From the repository root, run:

```bash
node agent/src/cli.mjs <session-code> --server http://localhost:8000
```

Use `--no-submit` to exercise only the exchange and evidence steps. The
published `npx @aergia/tailor` workflow and local-agent workspace are later
phases.
