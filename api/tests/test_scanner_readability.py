"""Edge cases for visible URL and entry-date PDF recovery checks."""

from __future__ import annotations

from typing import Any

import pytest

from app.scanner.pdf_recovery import analyze_pdf_recovery
from app.scanner.results import PDFRecoveryStatus


def _wire_cv(*sections: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": "generic-minimal",
        "customizations": {},
        "sections": list(sections),
    }


def _projects(*entries: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "projects",
        "type": "projects",
        "title": "Projects",
        "data": list(entries),
    }


def _worker(
    monkeypatch,
    *,
    text: str,
    links: list[str] | None = None,
) -> None:
    monkeypatch.setattr(
        "app.scanner.pdf_recovery._run_bounded_pdf_worker",
        lambda _pdf: {
            "page_count": 1,
            "plain_text": text,
            "links": links or [],
            "text_truncated": False,
        },
    )


def _check(result, code: str):
    return next(check for check in result.checks if check.code == code)


def test_compact_link_without_scheme_or_www_matches_its_clickable_target(monkeypatch) -> None:
    target = "https://www.linkedin.com/in/sample"
    cv = _wire_cv(
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "data": {
                "name": "Ada",
                "social_links": [{"url": target, "icon": "linkedin"}],
            },
        }
    )
    _worker(monkeypatch, text="Ada\nlinkedin.com/in/sample", links=[target])

    result = analyze_pdf_recovery(b"pdf", cv)

    assert _check(result, "link_recovery").status is PDFRecoveryStatus.PASS
    assert _check(result, "visible_url_recovery").status is PDFRecoveryStatus.PASS
    assert _check(result, "link_label_visibility").missing_items == []


def test_visible_url_query_comparison_preserves_case(monkeypatch) -> None:
    target = "https://example.com/Docs/FILE.MD?Ref=Q"
    cv = _wire_cv(
        _projects({"id": "docs", "name": "Docs", "url": target})
    )
    _worker(
        monkeypatch,
        text="Projects\nDocs\nexample.com/Docs/FILE.MD?ref=q",
        links=[target],
    )

    result = analyze_pdf_recovery(b"pdf", cv)
    visible_urls = _check(result, "visible_url_recovery")

    assert _check(result, "link_recovery").status is PDFRecoveryStatus.PASS
    assert visible_urls.status is PDFRecoveryStatus.WARNING
    assert visible_urls.recovered_count == 0


def test_trailing_period_in_a_query_is_part_of_the_visible_url(monkeypatch) -> None:
    target = "https://example.com/download?format=PDF."
    cv = _wire_cv(
        _projects({"id": "download", "name": "Download", "url": target})
    )
    _worker(
        monkeypatch,
        text="Projects\nDownload\nexample.com/download?format=PDF.",
        links=[target],
    )

    result = analyze_pdf_recovery(b"pdf", cv)
    visible_urls = _check(result, "visible_url_recovery")

    assert visible_urls.status is PDFRecoveryStatus.PASS
    assert visible_urls.recovered_count == 1


def test_root_slash_in_pdf_annotation_matches_empty_root_path(monkeypatch) -> None:
    target = "https://example.com"
    cv = _wire_cv(
        _projects({"id": "site", "name": "Example site", "url": target})
    )
    _worker(
        monkeypatch,
        text="Projects\nExample site\nexample.com",
        links=["https://example.com/"],
    )

    result = analyze_pdf_recovery(b"pdf", cv)

    assert _check(result, "link_recovery").status is PDFRecoveryStatus.PASS
    assert _check(result, "link_recovery").recovered_count == 1


def test_one_occurrence_of_a_repeated_date_cannot_satisfy_two_entries(monkeypatch) -> None:
    cv = _wire_cv(
        _projects(
            {
                "id": "one",
                "name": "Project One",
                "start_date": "2026-04",
                "description": "Built the search system.",
            },
            {
                "id": "two",
                "name": "Project Two",
                "start_date": "2026-04",
                "description": "Added export support.",
            },
        )
    )
    _worker(
        monkeypatch,
        text="Projects\nProject One\nApril 2026\nBuilt the search system.\nProject Two\nAdded export support.",
    )

    result = analyze_pdf_recovery(b"pdf", cv)
    dates = _check(result, "entry_date_association")

    assert dates.expected_count == 2
    assert dates.recovered_count == 1
    assert dates.status is PDFRecoveryStatus.WARNING


@pytest.mark.parametrize("visible", ["notexample.com/foo", "example.com/foobar", "example.com/foo?different=1"])
def test_visible_url_does_not_match_a_longer_address(monkeypatch, visible) -> None:
    target = "https://example.com/foo"
    cv = _wire_cv(_projects({"id": "site", "name": "Example site", "url": target}))
    _worker(monkeypatch, text=f"Projects\nExample site\n{visible}", links=[target])

    result = analyze_pdf_recovery(b"pdf", cv)

    assert _check(result, "visible_url_recovery").recovered_count == 0


def test_wrapped_url_keeps_real_text_boundaries(monkeypatch) -> None:
    target = "https://example.com/long-project-name?view=full"
    cv = _wire_cv(_projects({"id": "site", "name": "Example site", "url": target}))
    _worker(
        monkeypatch,
        text="Projects\nExample site\nexample.com/long-\nproject-name?view=full\nDescription",
        links=[target],
    )

    result = analyze_pdf_recovery(b"pdf", cv)

    assert _check(result, "visible_url_recovery").status is PDFRecoveryStatus.PASS


@pytest.mark.parametrize("hyphen_flags,expected", [([1, 0], "a-b"), ([0, 0], "a\ufffeb")])
def test_pdfium_hyphen_restoration_does_not_mask_unmapped_glyphs(monkeypatch, hyphen_flags, expected) -> None:
    from app.scanner.pdf_worker import _restore_pdfium_hyphens

    monkeypatch.setattr(
        "app.scanner.pdf_worker.pdfium.raw.FPDFText_IsHyphen",
        lambda _page, index: hyphen_flags[index],
    )

    assert _restore_pdfium_hyphens(object(), "a\ufffeb", len(hyphen_flags)) == expected
