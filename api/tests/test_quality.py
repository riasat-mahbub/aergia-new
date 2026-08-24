from app.services.quality import evaluate_cv_quality


def test_quality_checks_find_missing_contact_empty_sections_bad_links_and_overflow():
    result = evaluate_cv_quality(
        [
            {"type": "profile", "title": "Profile", "enabled": True, "data": {"name": "Ada"}},
            {"type": "experience", "title": "Experience", "enabled": True, "data": []},
            {"type": "projects", "title": "Projects", "enabled": True, "data": [{"url": "javascript:alert(1)"}]},
        ],
        page_count=2,
    )

    assert result.status == "warning"
    assert {issue.code for issue in result.issues} == {"missing_contact", "empty_section", "invalid_link", "page_overflow"}
    assert all(issue.severity == "warning" for issue in result.issues)


def test_quality_requires_a_profile_name():
    result = evaluate_cv_quality([{"type": "profile", "data": {"email": "ada@example.com"}}])

    assert result.status == "error"
    assert [(issue.code, issue.severity) for issue in result.issues] == [("missing_name", "error")]


def test_quality_accepts_external_and_private_asset_links():
    result = evaluate_cv_quality(
        [{
            "type": "profile",
            "data": {
                "name": "Ada",
                "email": "ada@example.com",
                "site_url": "https://example.com/ada",
                "photo_url": "/api/v1/assets/photo.png",
            },
        }]
    )

    assert result.status == "pass"
    assert result.issues == []
