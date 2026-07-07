"""Phase 8 hardening live smoke client.

Exercises the live backend (uvicorn launched by scripts/smoke.sh) for
``generic-modern``, ``generic-classic``, and ``generic-minimal``:

- Register a unique throwaway user.
- Login and obtain a bearer token.
- List the seed templates and assert the exact set.
- For each template, create a CV and verify the HTML preview
  (``<body`` in the response) and the PDF export (``Content-Type``
  starts with ``application/pdf`` and bytes start with ``%PDF``).
- Verify the built SPA is served at ``/`` (``<div id="root">``).

The function ``run_smoke`` takes an :class:`httpx.Client` so unit tests
can drive the same code path through :class:`httpx.MockTransport`.
The CLI creates a real client with a 30s timeout and calls
``run_smoke``.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from typing import Iterable, Optional

import httpx


EXPECTED_TEMPLATES = ("generic-modern", "generic-classic", "generic-minimal")


def _register_and_login(client: httpx.Client, base_url: str) -> str:
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    password = "SmokePass123!"
    r = client.post(f"{base_url}/api/v1/auth/register", json={"email": email, "password": password})
    if r.status_code != 201:
        raise AssertionError(f"register failed: {r.status_code} {r.text}")
    r = client.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise AssertionError(f"login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def _list_templates(client: httpx.Client, base_url: str, token: str) -> list[str]:
    r = client.get(
        f"{base_url}/api/v1/templates",
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        raise AssertionError(f"list templates failed: {r.status_code} {r.text}")
    return [t["id"] for t in r.json()]


def _wait_for_ready(client: httpx.Client, base_url: str) -> None:
    import time
    deadline = time.time() + 30.0
    while time.time() < deadline:
        r = client.get(f"{base_url}/readyz")
        if r.status_code == 200 and r.json().get("status") == "ok":
            return
        time.sleep(0.25)
    raise AssertionError(f"server at {base_url} did not become ready within 30s")


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
        if r.status_code != 201:
            raise AssertionError(
                f"create CV for {template_id} failed: {r.status_code} {r.text}"
            )
        cv_id = r.json()["id"]

        r = client.get(f"{base_url}/api/v1/cvs/{cv_id}/preview", headers=headers)
        if r.status_code != 200:
            raise AssertionError(
                f"preview for {template_id} failed: {r.status_code} {r.text}"
            )
        payload = r.json()
        html = payload.get("html", "")
        if not html.lstrip().startswith("<!DOCTYPE html>"):
            raise AssertionError(
                f"preview for {template_id} is not a complete HTML document: "
                f"{html[:80]!r}"
            )
        if "<body" not in html:
            raise AssertionError(
                f"preview for {template_id} is missing <body>: {html[:80]!r}"
            )

        r = client.post(f"{base_url}/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
        if r.status_code != 200:
            raise AssertionError(
                f"export PDF for {template_id} failed: {r.status_code} {r.text}"
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
    print("SMOKE OK: modern/classic/minimal preview + PDF + built SPA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
