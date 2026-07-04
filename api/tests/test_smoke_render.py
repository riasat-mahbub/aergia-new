"""Smoke test — the only Phase 1 integration assertion.

Build a Document from a CV + Template, resolve, render HTML, spawn
Playwright, and assert the resulting bytes start with ``%PDF``. This is
the end-to-end path the user actually exercises when they click "Export
PDF".
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schema.models import Customizations, TemplateManifest
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.services.renderer._pdf_runtime import html_to_pdf


def _cv():
    return SimpleNamespace(
        sections=[
            {
                "id": "sec_profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {
                    "name": "Ada",
                    "title": "Engineer",
                    "email": "a@example.com",
                    "phone": "555-0100",
                    "location": "Remote",
                    "summary": "Builder.",
                },
            },
            {
                "id": "sec_x",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [
                    {
                        "id": "e1",
                        "position": "Dev",
                        "company": "Co",
                        "start_date": "2020-01",
                        "end_date": "2022-06",
                        "description": "Did things.",
                    },
                ],
            },
            {
                "id": "sec_sk",
                "type": "skills",
                "title": "Skills",
                "enabled": True,
                "data": [{"id": "g1", "category": "Backend", "items": ["Python", "Go"]}],
            },
        ]
    )


def _manifest():
    return TemplateManifest.model_validate({
        "manifest_version": 2,
        "name": "Modern",
        "zones": [
            {"id": "sidebar", "styles": {"width": "narrow"}},
            {"id": "main", "styles": {"width": "full"}},
        ],
        "placement": {
            "profile": "sidebar",
            "experience": "main",
            "skills": "main",
        },
        "layout_defaults": {"spacing": "comfortable"},
        "policy_overrides": {"by_type": {}},
        "global_styles": {
            "accent_color": "#2563eb",
            "body_font": "sans-serif",
            "heading_font": "sans-serif",
        },
    })


@pytest.mark.asyncio
async def test_full_pipeline_emits_a_real_pdf():
    document = build_document(_cv(), _manifest())
    model = resolve(document, HTMLDocumentRenderer(), _manifest(), Customizations())
    html = HTMLDocumentRenderer().render(model)
    pdf_bytes = await html_to_pdf(html)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000  # Sanity: a real PDF is bigger than a stub.
