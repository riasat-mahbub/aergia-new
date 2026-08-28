"""Deterministic quality checks for rendered and editable CV payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.safe_url import normalize_url
from app.schemas.application import CVQualityIssue, CVQualityResult


_URL_KEYS = frozenset({"url", "link", "site_url", "photo_url", "paper_url", "credential_url"})
_IGNORED_CONTENT_KEYS = frozenset({"id"})


def _has_content(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(
            key not in _IGNORED_CONTENT_KEYS and _has_content(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_has_content(item) for item in value)
    return value is not None and value is not False


def _is_valid_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if value.startswith("/api/v1/assets/"):
        return ".." not in value and "\\" not in value
    return bool(normalize_url(value))


def _walk_url_values(value: object, path: str = ""):
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            item_path = f"{path}.{key_text}" if path else key_text
            if key_text in _URL_KEYS or key_text.endswith("_url"):
                yield item_path, item
            yield from _walk_url_values(item, item_path)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            yield from _walk_url_values(item, f"{path}[{index}]")


def evaluate_cv_quality(
    sections: Sequence[object] | Mapping[str, object],
    *,
    page_count: int | None = None,
) -> CVQualityResult:
    """Return non-blocking quality findings for a CV payload.

    URL checks intentionally validate safe syntax and schemes only. Network
    availability is not tested because it would make the result flaky and
    non-deterministic.
    """

    if isinstance(sections, Mapping):
        sections = sections.get("sections", [])  # type: ignore[assignment]
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes, bytearray)):
        sections = []

    issues: list[CVQualityIssue] = []
    profile_data: Mapping[str, object] | None = None
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_type = str(section.get("type") or "")
        data = section.get("data")
        if section_type == "profile" and isinstance(data, Mapping):
            profile_data = data
        if section.get("enabled", True) and not _has_content(data):
            issues.append(
                CVQualityIssue(
                    code="empty_section",
                    severity="warning",
                    message=f"{section.get('title') or section_type.title()} has no content.",
                    section_type=section_type or None,
                )
            )

        for path, value in _walk_url_values(data, f"sections[{section_type}].data"):
            if value is not None and not _is_valid_url(value):
                issues.append(
                    CVQualityIssue(
                        code="invalid_link",
                        severity="warning",
                        message="This link is not a valid HTTP(S) or supported CV URL.",
                        section_type=section_type or None,
                        field_path=path,
                    )
                )

    if not profile_data or not str(profile_data.get("name") or "").strip():
        issues.append(
            CVQualityIssue(
                code="missing_name",
                severity="error",
                message="Add your name to the profile.",
                section_type="profile",
                field_path="profile.name",
            )
        )
    if not profile_data or not any(
        str(profile_data.get(key) or "").strip() for key in ("email", "phone")
    ):
        issues.append(
            CVQualityIssue(
                code="missing_contact",
                severity="warning",
                message="Add an email address or phone number to your profile.",
                section_type="profile",
                field_path="profile.email",
            )
        )

    if page_count is not None and page_count > 1:
        issues.append(
            CVQualityIssue(
                code="page_overflow",
                severity="warning",
                message=f"This CV renders to {page_count} pages; trim content to keep it to one page.",
            )
        )

    status = "error" if any(issue.severity == "error" for issue in issues) else "warning" if issues else "pass"
    return CVQualityResult(status=status, page_count=page_count, issues=issues)


__all__ = ["evaluate_cv_quality"]
