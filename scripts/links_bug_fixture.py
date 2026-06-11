"""Fixture script: exercise link rendering across templates × flag states × section sets.

For each combination, the script:
1. Creates a CV with the chosen template and a defined set of sections.
2. PATCHes the CV's customizations to set `default_link_style` and
   `underline_section_titles` flags.
3. Fetches the preview HTML and the PDF through the API.
4. Dumps the PDF text with `pdftotext`.
5. Greps the preview HTML for every expected anchor text and asserts
   the *same* text appears in the pdftotext output.

Artifacts land in `/tmp/links-bug-fixture/`. Exit code is 0 only when
every case passes the "anchor text in PDF" check.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

API_BASE = os.environ.get("AERGIA_API", "http://localhost:8000")
ARTIFACT_DIR = Path("/tmp/links-bug-fixture")
EMAIL = os.environ.get("AERGIA_LINKS_BUG_EMAIL", "links-bug@example.com")
PASSWORD = "links-bug-pw-1234"

TEMPLATES = ["generic-modern", "generic-classic", "generic-minimal"]
FLAG_MATRIX = [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
]

# Texts we expect to appear inside <a>...</a> in the preview HTML and
# therefore also in the PDF text dump. These are the four anchor sites
# the bugs are about: profile email, profile site, project URL, cert URL.
ANCHOR_TEXTS = [
    "jane@example.com",
    "jane.dev",
    "github.com/jane/aergia",
    "Credential",
]

SITE_URL = "https://jane.dev"
SITE_TEXT = "jane.dev"
PROJECT_URL = "https://github.com/jane/aergia"
PROJECT_LINK_TEXT = "github.com/jane/aergia"
CERT_URL = "https://aws.amazon.com/verify/cred-001"

# Section sets exercised in the matrix.
MINIMAL_SECTIONS: list[dict] = [
    {"id": "sec_profile", "type": "profile", "title": "Profile", "enabled": True,
     "style": {"show_title": True},
     "data": {
         "name": "Jane Doe", "title": "Software Engineer",
         "email": ANCHOR_TEXTS[0], "phone": "+1 555-1234", "location": "Boston, MA",
         "site_text": SITE_TEXT, "site_url": SITE_URL,
         "summary": "Hello.",
         "photo_url": "",
     }},
    {"id": "sec_projects", "type": "projects", "title": "Projects", "enabled": True,
     "data": [{
         "id": "proj_1", "name": "Aergia",
         "url": PROJECT_URL, "link_text": PROJECT_LINK_TEXT,
         "start_date": "2025-01", "end_date": "2025-06",
         "description": "Build Aergia.", "tech_stack": ["React"],
     }]},
    {"id": "sec_certifications", "type": "certifications", "title": "Certifications", "enabled": True,
     "data": [{
         "id": "cert_1", "name": "AWS Architect",
         "issuer": "Amazon", "date": "2024",
         "credential_url": CERT_URL,
     }]},
]

FULL_SECTIONS: list[dict] = [
    {"id": "sec_profile", "type": "profile", "title": "Profile", "enabled": True,
     "style": {"show_title": True},
     "data": {
         "name": "Jane Doe", "title": "Software Engineer",
         "email": ANCHOR_TEXTS[0], "phone": "+1 555-1234", "location": "Boston, MA",
         "site_text": SITE_TEXT, "site_url": SITE_URL,
         "summary": "Experienced engineer building great products.",
         "photo_url": "",
     }},
    {"id": "sec_experience", "type": "experience", "title": "Experience", "enabled": True,
     "data": [
         {"id": "exp_1", "company": "Acme", "position": "Senior Engineer",
          "start_date": "2022-01", "end_date": None, "current": True,
          "location": "Boston, MA", "description": "Built things."},
         {"id": "exp_2", "company": "Foo", "position": "Engineer",
          "start_date": "2019-01", "end_date": "2021-12", "current": False,
          "location": "NYC", "description": "Did other things."},
     ]},
    {"id": "sec_education", "type": "education", "title": "Education", "enabled": True,
     "data": [{
         "id": "edu_1", "institution": "MIT", "degree": "B.S. CS",
         "start_date": "2018", "end_date": "2022", "current": False,
         "gpa": "3.8", "summary": "",
     }]},
    {"id": "sec_skills", "type": "skills", "title": "Skills", "enabled": True,
     "data": [
         {"id": "sk_1", "category": "Frontend", "items": ["React", "TypeScript"]},
         {"id": "sk_2", "category": "Backend", "items": ["Python", "FastAPI"]},
     ]},
    {"id": "sec_projects", "type": "projects", "title": "Projects", "enabled": True,
     "data": [{
         "id": "proj_1", "name": "Aergia",
         "url": PROJECT_URL, "link_text": PROJECT_LINK_TEXT,
         "start_date": "2025-01", "end_date": "2025-06",
         "description": "Build Aergia.", "tech_stack": ["React", "FastAPI"],
     }]},
    {"id": "sec_languages", "type": "languages", "title": "Languages", "enabled": True,
     "data": [
         {"id": "lang_1", "language": "English", "proficiency": "Native"},
         {"id": "lang_2", "language": "Spanish", "proficiency": "Intermediate"},
     ]},
    {"id": "sec_certifications", "type": "certifications", "title": "Certifications", "enabled": True,
     "data": [{
         "id": "cert_1", "name": "AWS Architect",
         "issuer": "Amazon", "date": "2024",
         "credential_url": CERT_URL,
     }]},
]

# Edge case: a CV with a photo URL on the profile, long summaries, and multiple
# entries in every section. Useful to surface the bug if it is triggered by a
# specific data shape that the standard full set does not hit.
EDGE_SECTIONS: list[dict] = [
    {"id": "sec_profile", "type": "profile", "title": "Profile", "enabled": True,
     "style": {"show_title": True},
     "data": {
         "name": "Jane Doe", "title": "Senior Software Engineer",
         "email": ANCHOR_TEXTS[0], "phone": "+1 555-1234", "location": "Boston, MA",
         "site_text": SITE_TEXT, "site_url": SITE_URL,
         "summary": "Twelve years of experience scaling distributed systems.",
         "photo_url": "https://example.com/photo.jpg",
     }},
    {"id": "sec_experience", "type": "experience", "title": "Experience", "enabled": True,
     "data": [
         {"id": "exp_1", "company": "Acme Corp", "position": "Staff Engineer",
          "start_date": "2022-01", "end_date": None, "current": True,
          "location": "Boston, MA", "description": "Led team of 5 engineers."},
         {"id": "exp_2", "company": "Foo Inc", "position": "Senior Engineer",
          "start_date": "2018-01", "end_date": "2021-12", "current": False,
          "location": "NYC", "description": "Shipped critical projects."},
     ]},
    {"id": "sec_education", "type": "education", "title": "Education", "enabled": True,
     "data": [{
         "id": "edu_1", "institution": "MIT", "degree": "B.S. Computer Science",
         "start_date": "2014", "end_date": "2018", "current": False,
         "gpa": "3.8", "summary": "",
     }]},
    {"id": "sec_skills", "type": "skills", "title": "Skills", "enabled": True,
     "data": [
         {"id": "sk_1", "category": "Frontend", "items": ["React", "TypeScript", "Tailwind"]},
         {"id": "sk_2", "category": "Backend", "items": ["Python", "FastAPI", "PostgreSQL"]},
     ]},
    {"id": "sec_projects", "type": "projects", "title": "Projects", "enabled": True,
     "data": [{
         "id": "proj_1", "name": "Aergia",
         "url": PROJECT_URL, "link_text": PROJECT_LINK_TEXT,
         "start_date": "2025-01", "end_date": "2025-06",
         "description": "Build Aergia.", "tech_stack": ["React", "FastAPI"],
     }]},
    {"id": "sec_languages", "type": "languages", "title": "Languages", "enabled": True,
     "data": [
         {"id": "lang_1", "language": "English", "proficiency": "Native"},
         {"id": "lang_2", "language": "Spanish", "proficiency": "Intermediate"},
     ]},
    {"id": "sec_certifications", "type": "certifications", "title": "Certifications", "enabled": True,
     "data": [{
         "id": "cert_1", "name": "AWS Architect",
         "issuer": "Amazon", "date": "2024",
         "credential_url": CERT_URL,
     }]},
]

SECTION_SETS = {
    "minimal": MINIMAL_SECTIONS,
    "full": FULL_SECTIONS,
    "edge": EDGE_SECTIONS,
}


@dataclass


@dataclass
class Case:
    template: str
    link_flag: bool
    underline_flag: bool
    section_set: str


def case_name(c: Case) -> str:
    return f"{c.template}-link{int(c.link_flag)}-under{int(c.underline_flag)}-{c.section_set}"


def make_cases() -> list[Case]:
    cases: list[Case] = []
    for tmpl in TEMPLATES:
        for link_flag, underline_flag in FLAG_MATRIX:
            for section_set in SECTION_SETS:
                cases.append(Case(tmpl, link_flag, underline_flag, section_set))
    return cases


def register_or_login(client: httpx.Client) -> str:
    """Register (idempotent), then login. Returns the access token."""
    r = client.post("/api/v1/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code not in (201, 409):
        raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    r = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def create_cv(client: httpx.Client, headers: dict, template_id: str, sections: list[dict]) -> str:
    r = client.post("/api/v1/cvs", headers=headers, json={
        "title": f"links-bug {template_id} {int(time.time()*1000)}",
        "template_id": template_id,
        "sections": sections,
    })
    r.raise_for_status()
    return r.json()["id"]


def patch_customizations(client: httpx.Client, headers: dict, cv_id: str, link: bool, underline: bool) -> None:
    r = client.patch(f"/api/v1/cvs/{cv_id}", headers=headers, json={
        "customizations": {
            "flags": {
                "default_link_style": link,
                "underline_section_titles": underline,
            }
        }
    })
    r.raise_for_status()


def fetch_preview(client: httpx.Client, headers: dict, cv_id: str) -> str:
    r = client.get(f"/api/v1/cvs/{cv_id}/preview", headers=headers)
    r.raise_for_status()
    return r.json()["html"]


def fetch_pdf(client: httpx.Client, headers: dict, cv_id: str) -> bytes:
    r = client.post(f"/api/v1/cvs/{cv_id}/export/pdf", headers=headers)
    r.raise_for_status()
    return r.content


def grep_anchor_texts_in_html(html: str) -> dict[str, bool]:
    """Each anchor text should appear somewhere in the HTML (not stripped)."""
    return {t: (t in html) for t in ANCHOR_TEXTS}


def pdftotext_dump(pdf_path: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", "-q", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def render_pdf_to_png(pdf_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # The pattern must end with a dash so pdftoppm appends `-NN.png`; if it ends
    # with `.png` literally, pdftoppm emits a single `.png` file (or PPM).
    prefix = out_dir / (pdf_path.stem + "-p")
    subprocess.run(["pdftoppm", "-r", "120", "-png", str(pdf_path), str(prefix)], check=True)
    return sorted(out_dir.glob(pdf_path.stem + "-p-*.png"))


def assert_case(case: Case, *, html: str, pdf_text: str, failures: list[str]) -> None:
    """Compare the preview HTML's anchor content against the PDF text dump."""
    in_html = grep_anchor_texts_in_html(html)
    for text, present in in_html.items():
        if not present:
            failures.append(f"[{case_name(case)}] preview HTML missing anchor text: {text!r}")

    for text in ANCHOR_TEXTS:
        if text in html and text not in pdf_text:
            failures.append(
                f"[{case_name(case)}] PDF text missing anchor text {text!r} "
                f"(present in preview HTML)",
            )


def write_artifacts(c: Case, html: str, pdf: bytes, text: str) -> None:
    name = case_name(c)
    (ARTIFACT_DIR / f"preview-{name}.html").write_text(html, encoding="utf-8")
    (ARTIFACT_DIR / f"pdf-{name}.pdf").write_bytes(pdf)
    (ARTIFACT_DIR / f"text-{name}.txt").write_text(text, encoding="utf-8")


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    png_dir = ARTIFACT_DIR / "png"
    if png_dir.exists():
        for p in png_dir.glob("*.png"):
            p.unlink()

    cases = make_cases()
    failures: list[str] = []
    per_case_meta: dict[str, dict[str, Any]] = {}

    with httpx.Client(base_url=API_BASE, timeout=60.0) as client:
        token = register_or_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        for case in cases:
            print(f"==> {case_name(case)}")
            sections = SECTION_SETS[case.section_set]
            cv_id = create_cv(client, headers, case.template, sections)
            patch_customizations(client, headers, cv_id, case.link_flag, case.underline_flag)
            html = fetch_preview(client, headers, cv_id)
            pdf = fetch_pdf(client, headers, cv_id)

            pdf_path = ARTIFACT_DIR / f"pdf-{case_name(case)}.pdf"
            pdf_path.write_bytes(pdf)
            text = pdftotext_dump(pdf_path)
            pngs = render_pdf_to_png(pdf_path, png_dir)

            write_artifacts(case, html, pdf, text)
            assert_case(case, html=html, pdf_text=text, failures=failures)

            per_case_meta[case_name(case)] = {
                "html_chars": len(html),
                "pdf_bytes": len(pdf),
                "pdf_text_chars": len(text),
                "pngs": [p.name for p in pngs],
            }

    summary = {
        "total_cases": len(cases),
        "failures": failures,
        "meta": per_case_meta,
    }
    (ARTIFACT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nAll {len(cases)} cases passed (anchor text preserved in PDF).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
