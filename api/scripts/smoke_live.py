"""Phase 8 hardening live smoke client.

Exercises the live backend (uvicorn launched by scripts/smoke.sh) for
``generic-modern``, ``generic-classic``, and ``generic-minimal``:

- Register a unique throwaway user.
- Login and obtain the HttpOnly access/refresh cookies plus the CSRF cookie.
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

from app.core.auth import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME


EXPECTED_TEMPLATES = ("generic-modern", "generic-classic", "generic-minimal")


def _register_and_login(client: httpx.Client, base_url: str) -> dict[str, str]:
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
    csrf_token = client.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_token:
        raise AssertionError("login did not establish a CSRF cookie")
    if not client.cookies.get(ACCESS_COOKIE_NAME):
        raise AssertionError("login did not establish an access cookie")
    if not client.cookies.get(REFRESH_COOKIE_NAME):
        raise AssertionError("login did not establish a refresh cookie")
    return {"X-CSRF-Token": csrf_token}


def _list_templates(client: httpx.Client, base_url: str, headers: dict[str, str]) -> list[str]:
    r = client.get(
        f"{base_url}/api/v1/templates",
        headers=headers,
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


def _smoke_import_pdf(client: httpx.Client, base_url: str, headers: dict[str, str]) -> None:
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
        headers=headers,
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
            f"import PDF payload.sections contains malformed items: {sections!r}"
        )

def _smoke_library(client: httpx.Client, base_url: str, headers: dict[str, str]) -> None:
    """Minimal Library block: create an entry, clone it into a CV, render preview."""
    title_substring = f"SmokeEntry-{uuid.uuid4().hex[:6]}"

    r = client.post(
        f"{base_url}/api/v1/library",
        json={"kind": "experience", "payload": [{"title": title_substring, "company": "SmokeCo"}]},
        headers=headers,
    )
    if r.status_code != 201:
        raise AssertionError(f"create library entry failed: {r.status_code} {r.text[:200]}")
    entry_id = r.json()["id"]

    r = client.post(f"{base_url}/api/v1/library/{entry_id}/clone", headers=headers)
    if r.status_code != 200:
        raise AssertionError(f"clone library entry failed: {r.status_code} {r.text[:200]}")
    section_instance = r.json()["section_instance"]

    r = client.post(
        f"{base_url}/api/v1/cvs",
        json={"title": "Library smoke CV", "sections": [section_instance]},
        headers=headers,
    )
    if r.status_code not in (200, 201):
        raise AssertionError(f"create CV from cloned library entry failed: {r.status_code} {r.text[:200]}")
    cv_id = r.json()["id"]

    r = client.get(f"{base_url}/api/v1/cvs/{cv_id}/preview", headers=headers)
    if r.status_code != 200:
        raise AssertionError(f"preview of library-CV failed: {r.status_code} {r.text[:200]}")
    if title_substring not in r.text:
        raise AssertionError(
            f"preview missing cloned entry title '{title_substring}': {r.text[:200]!r}"
        )

    # Idempotent re-promote of the same CV — Library already has the entry, no new rows.
    r = client.post(f"{base_url}/api/v1/cvs/{cv_id}/promote-to-library", headers=headers)
    if r.status_code != 200:
        raise AssertionError(f"promote re-run failed: {r.status_code} {r.text[:200]}")
    if r.json()["promoted"] != {}:
        raise AssertionError(f"re-promote should be a no-op; got {r.json()['promoted']!r}")

def _smoke_application(client: httpx.Client, base_url: str, headers: dict[str, str]) -> None:
    """Exercise Profile → Library rows → generated application → linked CV."""
    profile = client.put(
        f"{base_url}/api/v1/profile",
        json={
            "name": "Smoke Applicant",
            "title": "Platform Engineer",
            "email": "smoke@example.com",
            "phone": None,
            "location": "Remote",
            "site_text": None,
            "site_url": None,
            "summary": "Builds distributed systems.",
            "photo_url": None,
            "email_link": True,
            "social_links": [],
        },
        headers=headers,
    )
    if profile.status_code != 200:
        raise AssertionError(f"update profile failed: {profile.status_code} {profile.text[:200]}")

    rows = (
        ("education", [{"id": "edu-smoke", "institution": "Example University", "degree": "Platform Engineering"}]),
        ("skill", [{"id": "skill-smoke", "category": "Backend", "items": ["Python", "FastAPI", "PostgreSQL"]}]),
        ("experience", [{"id": "exp-smoke", "company": "Example Labs", "position": "Distributed Systems"}]),
        ("certification", [{"id": "cert-smoke", "name": "Cloud Native"}]),
        ("project", [{"id": "project-smoke", "name": "Platform", "tech_stack": ["Python"]}]),
        ("research", [{"id": "research-smoke", "title": "Systems Research"}]),
    )
    for kind, payload in rows:
        created = client.post(
            f"{base_url}/api/v1/library",
            json={"kind": kind, "payload": payload},
            headers=headers,
        )
        if created.status_code != 201:
            raise AssertionError(f"create {kind} Library row failed: {created.status_code} {created.text[:200]}")

    created = client.post(
        f"{base_url}/api/v1/applications",
        json={
            "company": "Example Labs",
            "role": "Platform Engineer",
            "job_description": (
                "Build Python services with FastAPI and PostgreSQL.\n"
                "Distributed systems and platform engineering experience.\n"
                "Cloud Native certification preferred.\n"
                "Platform project.\n"
                "Systems research publication preferred."
            ),
        },
        headers=headers,
    )
    if created.status_code != 201:
        raise AssertionError(f"create application failed: {created.status_code} {created.text[:200]}")
    application_id = created.json()["id"]

    generated = client.post(
        f"{base_url}/api/v1/applications/{application_id}/generate",
        headers=headers,
    )
    if generated.status_code != 200:
        raise AssertionError(f"generate application failed: {generated.status_code} {generated.text[:200]}")
    generated_body = generated.json()
    generated_application = generated_body.get("application") or {}
    cv_id = generated_body.get("cv_id")
    if generated_application.get("generation_status") != "ready" or not cv_id:
        raise AssertionError(f"application generation was not ready: {generated_body!r}")
    relevance = generated_application.get("relevance") or {}
    has_requirement_details = bool(relevance.get("requirements")) and "total_requirements" in relevance
    has_legacy_details = bool(relevance.get("matched_keywords"))
    if not (has_requirement_details or has_legacy_details) or "score" not in relevance:
        raise AssertionError(f"generation relevance details missing: {generated_body!r}")

    cv = client.get(f"{base_url}/api/v1/cvs/{cv_id}", headers=headers)
    if cv.status_code != 200:
        raise AssertionError(f"get generated CV failed: {cv.status_code} {cv.text[:200]}")
    cv_body = cv.json()
    sections = cv_body.get("sections") or []
    expected_order = ["profile", "education", "skills", "experience", "certifications", "projects", "research"]
    actual_order = [section.get("type") for section in sections if section.get("data")]
    if actual_order != expected_order:
        raise AssertionError(f"generated CV section order mismatch: {actual_order!r}")

    preview = client.get(f"{base_url}/api/v1/cvs/{cv_id}/preview", headers=headers)
    if preview.status_code != 200 or "<body" not in preview.text:
        raise AssertionError(f"generated CV preview failed: {preview.status_code} {preview.text[:200]}")
    exported = client.post(f"{base_url}/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
    if exported.status_code != 200 or not exported.content.startswith(b"%PDF"):
        raise AssertionError(f"generated CV PDF export failed: {exported.status_code} {exported.content[:8]!r}")

    detail = client.get(f"{base_url}/api/v1/applications/{application_id}", headers=headers)
    if detail.status_code != 200:
        raise AssertionError(f"get application detail failed: {detail.status_code} {detail.text[:200]}")
    detail_body = detail.json()
    if detail_body.get("id") != application_id or detail_body.get("cv_id") != cv_id:
        raise AssertionError(f"application/CV ownership link mismatch: {detail_body!r}")


def run_smoke(client: httpx.Client, base_url: str) -> None:
    _wait_for_ready(client, base_url)
    headers = _register_and_login(client, base_url)

    template_ids = _list_templates(client, base_url, headers)
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
    _smoke_import_pdf(client, base_url, headers)

    # Library smoke — promote-to-library + clone-into-CV + preview reflects it.
    _smoke_library(client, base_url, headers)
    # Application smoke — singleton Profile + all generated section kinds +
    # relevance and canonical preview/PDF paths.
    _smoke_application(client, base_url, headers)

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
