"""Focused regression cases for the PDF recovery audit.

These tests intentionally use the bounded-worker seam so the comparison
logic can be exercised without requiring Chromium or a real PDF fixture.
"""

from __future__ import annotations

from typing import Any

from app.scanner.pdf_recovery import (
    _check_status,
    _ordered_match_count,
    analyze_pdf_recovery,
)
from app.scanner.results import PDFRecoveryStatus


def _field(key: str, text: str) -> dict[str, Any]:
    return {"key": key, "runs": [{"text": text}]}


def _worker(monkeypatch, *, text: str, links: list[str] | None = None) -> None:
    monkeypatch.setattr(
        "app.scanner.pdf_recovery._run_bounded_pdf_worker",
        lambda _pdf: {
            "page_count": 1,
            "plain_text": text,
            "links": links or [],
            "text_truncated": False,
        },
    )


def _wire_cv(*sections: dict[str, Any], customizations: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "template_id": "generic-minimal",
        "customizations": customizations or {},
        "sections": list(sections),
    }


def test_ordered_match_skips_missing_expected_tokens_instead_of_terminating() -> None:
    assert _ordered_match_count(["a", "b", "c", "d", "e"], ["a", "b", "d", "e"]) == 4
    assert _ordered_match_count(["a", "b", "c", "d", "e"], ["a", "c", "d", "e"]) == 4
    assert _ordered_match_count(["a", "b", "c", "d", "e"], ["a", "b", "e", "c", "d"]) == 4


def test_hidden_profile_heading_is_not_an_expected_heading(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada"}},
        {"id": "experience", "type": "experience", "title": "Experience", "data": [{"id": "job", "position": "Developer"}]},
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia"}]},
        {"id": "education", "type": "education", "title": "Education", "data": [{"id": "school", "institution": "Dalhousie"}]},
    )
    _worker(monkeypatch, text="Experience\nDeveloper\nProjects\nAergia\nEducation\nDalhousie")

    result = analyze_pdf_recovery(b"pdf", cv)
    headings = next(check for check in result.checks if check.code == "section_heading_recovery")

    assert headings.expected_count == 3
    assert headings.recovered_count == 3
    assert "Profile" not in headings.evidence


def test_project_and_education_entries_use_renderer_identifying_fields(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia"}]},
        {"id": "education", "type": "education", "title": "Education", "data": [{"id": "school", "institution": "Dalhousie University"}]},
    )
    _worker(monkeypatch, text="Projects\nAergia\nEducation\nDalhousie University")

    result = analyze_pdf_recovery(b"pdf", cv)
    entries = next(check for check in result.checks if check.code == "entry_recovery")

    assert entries.expected_count == 2
    assert entries.recovered_count == 2


def test_zero_expected_contacts_are_unavailable(monkeypatch) -> None:
    cv = _wire_cv({"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada"}})
    _worker(monkeypatch, text="Ada")

    result = analyze_pdf_recovery(b"pdf", cv)
    contacts = next(check for check in result.checks if check.code == "contact_recovery")

    assert contacts.status is PDFRecoveryStatus.UNAVAILABLE


def test_contact_recovery_reports_missing_contact_types(monkeypatch) -> None:
    cv = _wire_cv(
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "data": {"name": "Ada", "email": "ada@example.com", "phone": "+1 555 0100"},
        }
    )
    _worker(monkeypatch, text="Ada\nada@example.com")

    result = analyze_pdf_recovery(b"pdf", cv)
    contacts = next(check for check in result.checks if check.code == "contact_recovery")

    assert contacts.recovered_count == 1
    assert contacts.evidence == ["email"]
    assert contacts.missing_items == ["phone"]


def test_heading_matching_does_not_count_body_mentions(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia"}]}
    )
    _worker(monkeypatch, text="Worked across several projects while building Aergia.")

    result = analyze_pdf_recovery(b"pdf", cv)
    headings = next(check for check in result.checks if check.code == "section_heading_recovery")

    assert headings.expected_count == 1
    assert headings.recovered_count == 0


def test_duplicate_heading_occurrences_are_accounted_for_individually(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "one", "name": "Aergia"}]},
        {"id": "extras", "type": "extras", "title": "Projects", "data": [{"id": "two", "title": "Other"}]},
    )
    _worker(monkeypatch, text="Projects\nAergia\nOther")

    result = analyze_pdf_recovery(b"pdf", cv)
    headings = next(check for check in result.checks if check.code == "section_heading_recovery")

    assert headings.expected_count == 2
    assert headings.recovered_count == 1


def test_duplicate_entry_labels_are_accounted_for_individually(monkeypatch) -> None:
    cv = _wire_cv(
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [
                {"id": "one", "position": "Software Engineer"},
                {"id": "two", "position": "Software Engineer"},
            ],
        }
    )
    _worker(monkeypatch, text="Experience\nSoftware Engineer")

    result = analyze_pdf_recovery(b"pdf", cv)
    entries = next(check for check in result.checks if check.code == "entry_recovery")

    assert entries.expected_count == 2
    assert entries.recovered_count == 1


def test_expected_text_uses_formatted_visible_fields_and_visible_link_labels(monkeypatch) -> None:
    cv = _wire_cv(
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "data": {
                "name": "Ada",
                "site_url": "example.com",
                "site_text": "Portfolio",
                "social_links": [{"label": "GitHub", "url": "github.com/ada", "icon": "github"}],
            },
        },
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "job", "position": "Developer", "start_date": "2022-07", "end_date": "2023-08"}],
        },
    )
    _worker(monkeypatch, text="Ada\nPortfolio\nGitHub\nExperience\nDeveloper\nJuly 2022 – August 2023")

    result = analyze_pdf_recovery(b"pdf", cv)
    text_check = next(check for check in result.checks if check.code == "text_retention")

    assert text_check.recovered_count == text_check.expected_count
    assert "July 2022 – August 2023" in text_check.expected_items
    assert "2022-07" not in text_check.expected_items
    assert "Portfolio" in text_check.expected_items
    assert "https://example.com" not in text_check.expected_items


def test_zone_order_is_used_for_reading_order(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada"}},
        {"id": "experience", "type": "experience", "title": "Experience", "data": [{"id": "job", "position": "Developer"}]},
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia"}]},
        customizations={
            "layout": {
                "zones": [{"id": "sidebar", "styles": {}}, {"id": "main", "styles": {}}],
                "placement": {"profile": "sidebar", "experience": "main", "projects": "sidebar"},
            }
        },
    )
    _worker(monkeypatch, text="Projects\nAergia\nProfile\nExperience\nDeveloper")

    result = analyze_pdf_recovery(b"pdf", cv)
    order = next(check for check in result.checks if check.code == "reading_order")

    assert order.status is PDFRecoveryStatus.PASS
    assert order.recovered_count == order.expected_count


def test_reading_order_reports_a_real_anchor_swap(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "experience", "type": "experience", "title": "Experience", "data": [{"id": "job", "position": "Developer"}]},
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia"}]},
    )
    _worker(monkeypatch, text="Projects\nAergia\nExperience\nDeveloper")

    result = analyze_pdf_recovery(b"pdf", cv)
    order = next(check for check in result.checks if check.code == "reading_order")

    assert order.status is PDFRecoveryStatus.FAIL
    assert order.recovered_count < order.expected_count
    assert order.affected_items


def test_renderer_normalized_urls_match_source_urls(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "projects", "type": "projects", "title": "Projects", "data": [{"id": "project", "name": "Aergia", "url": "example.com"}]}
    )
    _worker(monkeypatch, text="Projects\nAergia\nhttps://example.com", links=["https://example.com"])

    result = analyze_pdf_recovery(b"pdf", cv)
    links = next(check for check in result.checks if check.code == "link_recovery")

    assert links.expected_count == 1
    assert links.recovered_count == 1


def test_non_rendered_url_metadata_is_not_a_link_expectation(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada", "photo_url": "https://example.com/photo.png"}}
    )
    _worker(monkeypatch, text="Ada")

    result = analyze_pdf_recovery(b"pdf", cv)
    links = next(check for check in result.checks if check.code == "link_recovery")

    assert links.status is PDFRecoveryStatus.UNAVAILABLE


def test_non_critical_link_failure_does_not_veto_pdf_analysis(monkeypatch) -> None:
    cv = _wire_cv(
        {"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada", "email": "ada@example.com"}}
    )
    _worker(monkeypatch, text="Ada\nada@example.com")

    result = analyze_pdf_recovery(b"pdf", cv)

    assert result.status is PDFRecoveryStatus.PASS


def test_missing_link_annotation_is_warning_not_critical_failure(monkeypatch) -> None:
    cv = _wire_cv(
        {
            "id": "projects",
            "type": "projects",
            "title": "Projects",
            "data": [{"id": "project", "name": "Aergia", "url": "example.com"}],
        }
    )
    _worker(monkeypatch, text="Projects\nAergia\nhttps://example.com", links=[])

    result = analyze_pdf_recovery(b"pdf", cv)
    links = next(check for check in result.checks if check.code == "link_recovery")

    assert links.status is PDFRecoveryStatus.WARNING
    assert result.status is PDFRecoveryStatus.WARNING


def test_unicode_and_technical_tokens_are_preserved() -> None:
    from app.scanner.pdf_recovery import _tokens

    tokens = _tokens("Montréal Université Développeur expérience 中文 C++ C# .NET CI/CD Node.js")

    assert tokens == [
        "montréal",
        "université",
        "développeur",
        "expérience",
        "中文",
        "c++",
        "c#",
        ".net",
        "ci/cd",
        "node.js",
    ]


def test_recovery_thresholds_are_specific_to_check_severity() -> None:
    assert _check_status(0.75, "text_retention") is PDFRecoveryStatus.FAIL
    assert _check_status(0.75, "entry_recovery") is PDFRecoveryStatus.WARNING
    assert _check_status(0.75, "link_recovery") is PDFRecoveryStatus.WARNING
