"""Phase 8 hardening live smoke client.

Exercises the live backend (uvicorn launched by scripts/smoke.sh) for
``generic-modern``, ``generic-classic``, and ``generic-minimal``:

- Register a unique throwaway user.
- Login and obtain a bearer token.
- List the seed templates and assert the exact set.
- For each template, create a CV and verify the HTML preview
  (``<body`` in the response) and the PDF export (``Content-Type``
  starts with ``application/pdf`` and bytes start with ``%PDF``).
- Verify the import endpoint accepts a fixture PDF and returns a
  ``ParseResult`` whose ``sections`` are valid ``SectionInstance`` dicts.
- Verify the built SPA is served at ``/`` (``<div id="root">``).

The function ``run_smoke`` takes an :class:`httpx.Client` so unit tests
can drive the same code path through :class:`httpx.MockTransport`.
The CLI creates a real client with a 30s timeout and calls
``run_smoke``.
"""

from __future__ import annotations

import argparse
import io
import sys
import uuid
from pathlib import Path
from typing import Iterable, Optional

import httpx


EXPECTED_TEMPLATES = ("generic-modern", "generic-classic", "generic-minimal")


def _register_and_login(client: httpx.Client, base_url: str) -> str:
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    password = "smoke-test-123"
    r = client.post(
        f"{base_url}/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    if r.status_code not in (200, 201):
        # 409 is tolerated: previous runs may have left orphan users.
        if r.status_code != 409:
            raise AssertionError(f"register failed: {r.status_code} {r.text[:200]}")
    r = client.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if r.status_code != 200:
        raise AssertionError(f"login failed: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def _list_templates(client: httpx.Client, base_url: str, token: str) -> list[str]:
    r = client.get(
        f"{base_url}/api/v1/templates",
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        raise AssertionError(f"templates list failed: {r.status_code} {r.text[:200]}")
    return [t["id"] for t in r.json()]


def _wait_for_ready(client: httpx.Client, base_url: str) -> None:
    import time

    deadline = time.time() + 30.0
    while time.time() < deadline:
        r = client.get(f"{base_url}/readyz")
        if r.status_code == 200:
            return
        time.sleep(0.25)
    raise AssertionError(f"server at {base_url} did not become ready within 30s")


def _smoke_import_pdf(client: httpx.Client, base_url: str, token: str) -> None:
    """POST the fixture PDF to the import route and validate the response shape."""
    fixture = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "fixtures"
        / "sample.pdf"
    )
    if not fixture.exists():
        raise AssertionError(f"PDF import fixture missing: {fixture}")
    body = fixture.read_bytes()
    r = client.post(
        f"{base_url}/api/v1/cvs/import/pdf",
        files={"file": ("sample.pdf", io.BytesIO(body), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        raise AssertionError(
            f"import PDF returned {r.status_code}: {r.text[:200]}"
        )
    payload = r.json()
    sections = payload.get("sections") or []
    if not isinstance(sections, list):
        raise AssertionError(
            f"import PDF payload.sections is not a list: {type(sections)!r}"
        )
    if not all(
        isinstance(s, dict) and "type" in s and "data" in s
        for s in sections
    ):
        raise AssertionError(
            "import PDF sections are not SectionInstance-shaped"
        )


def run_smoke(client: httpx.Client, base_url: str) -> None:
    _wait_for_ready(client, base_url)
    token = _register_and_login(client, base_url)
    headers = {"Authorization": f"Bearer {token}"}

    template_ids = _list_templates(client, base_url, token)
    if set(template_ids) != set(EXPECTED_TEMPLATES):
        raise AssertionError(
            f"unexpected template set: {template_ids!r}; "
            f"expected exactly {EXPECTED_TEMPLATES!r}"
        )

    for template_id in template_ids:
        r = client.post(
            f"{base_url}/api/v1/cvs",
            json={"title": f"Smoke {template_id}", "template_id": template_id},
            headers=headers,
        )
        if r.status_code not in (200, 201):
            raise AssertionError(
                f"create CV for {template_id} failed: {r.status_code} {r.text[:200]}"
            )
        cv_id = r.json()["id"]

        r = client.get(
            f"{base_url}/api/v1/cvs/{cv_id}/preview",
            headers=headers,
        )
        if r.status_code != 200:
            raise AssertionError(
                f"preview for {template_id} failed: {r.status_code} {r.text[:200]}"
            )
        if "<body" not in r.text:
            raise AssertionError(
                f"preview for {template_id} missing <body>: {r.text[:200]!r}"
            )

        r = client.post(
            f"{base_url}/api/v1/cvs/{cv_id}/export/pdf",
            headers=headers,
        )
        if r.status_code != 200:
            raise AssertionError(
                f"export PDF for {template_id} failed: {r.status_code} {r.text[:200]}"
            )
        content_type = r.headers.get("content-type", "")
        if not content_type.startswith("application/pdf"):
            raise AssertionError(
                f"export PDF for {template_id} returned Content-Type {content_type!r}"
            )
        if not r.content.startswith(b"%PDF"):
            raise AssertionError(
                f"export PDF for {template_id} returned non-PDF body: {r.content[:8]!r}"
            )

    # Import route smoke (PDF → typed ParseResult).
    _smoke_import_pdf(client, base_url, token)

    r = client.get(f"{base_url}/")
    if r.status_code != 200:
        raise AssertionError(f"SPA GET / failed: {r.status_code} {r.text[:120]}")
    if '<div id="root"></div>' not in r.text:
        raise AssertionError(
            f"SPA GET / is missing the React root mount: {r.text[:200]!r}"
        )


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 8 live smoke client.")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    with httpx.Client(timeout=30.0) as client:
        run_smoke(client, args.base_url)
    print(
        "SMOKE OK: modern/classic/minimal preview + PDF + import PDF + built SPA"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
