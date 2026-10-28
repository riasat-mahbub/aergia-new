"""Browser geometry for the compact contact header used in preview and PDF."""

from __future__ import annotations

from io import BytesIO

import pdfplumber
import pytest

from app.db.seed import SEED_TEMPLATES
from app.services.renderer import prepare_render_source, render_source_html
from app.services.renderer._pdf_runtime import _get_browser, close_browser


def reference_profile():
    return {
        "id": "profile", "type": "profile", "title": "Profile", "enabled": True,
        "data": {
            "name": "Riasat Mahbub", "email": "riasat1998@gmail.com",
            "location": "Halifax, NS", "site_url": "https://rmahbub.com",
            "social_links": [
                {"label": "github.com/riasat-mahbub", "url": "https://github.com/riasat-mahbub", "icon": "github"},
                {"label": "linkedin.com/in/riasat-mahbub", "url": "https://linkedin.com/in/riasat-mahbub", "icon": "linkedin"},
            ],
        },
    }


@pytest.mark.parametrize("template_id,width,body_size", [
    ("generic-minimal", 794, None),
    ("generic-classic", 794, None),
    ("generic-modern", 360, None),
    ("generic-minimal", 794, "large"),
])
async def test_reference_contact_header_stays_compact_and_preserves_controls(template_id, width, body_size):
    profile = reference_profile()
    if body_size:
        profile["style"] = {"typography": {"body": {"font_size": body_size}}}
    manifest = next(t["manifest"] for t in SEED_TEMPLATES if t["id"] == template_id)
    html = render_source_html(prepare_render_source([profile], manifest))
    browser = await _get_browser()
    page = await browser.new_page(viewport={"width": width, "height": 600})
    try:
        await page.set_content(html)
        metrics = await page.evaluate("""() => {
            const row = document.querySelector('.contact-row');
            const items = [...row.children];
            const bounds = row.getBoundingClientRect();
            return {
                sizes: items.map(el => parseFloat(getComputedStyle(el).fontSize)),
                tops: items.map(el => el.getBoundingClientRect().top),
                separators: items.map(el => getComputedStyle(el, '::before').content),
                contained: items.every(el => el.getBoundingClientRect().right <= bounds.right + 1),
                icons: row.querySelectorAll('.f-icon').length,
                siteIconLinked: !!row.querySelector('.f-site a .f-icon'),
                links: [...row.querySelectorAll('a')].map(el => el.href),
            };
        }""")
        assert len(metrics["tops"]) == 5
        assert len(set(metrics["sizes"])) == 1
        assert metrics["separators"][0] == "none"
        assert all("|" in separator for separator in metrics["separators"][1:])
        assert metrics["icons"] == 3
        assert metrics["siteIconLinked"]
        assert len(metrics["links"]) == 3
        assert metrics["contained"]
        if template_id != "generic-modern" and not body_size:
            assert max(metrics["tops"]) - min(metrics["tops"]) < 1
            pdf = await page.pdf(format="A4", prefer_css_page_size=True)
            with pdfplumber.open(BytesIO(pdf)) as document:
                contacts = [document.pages[0].search(label, regex=False)[0] for label in {
                    "riasat1998@gmail.com", "rmahbub.com", "github.com/riasat-mahbub",
                    "linkedin.com/in/riasat-mahbub",
                }]
                assert max(w["top"] for w in contacts) - min(w["top"] for w in contacts) < 1
        if body_size:
            assert metrics["sizes"] == [18] * 5
    finally:
        await page.close()
        await close_browser()
