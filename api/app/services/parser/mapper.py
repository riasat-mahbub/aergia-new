"""Mapper — labelled blocks → :class:`SectionInstance` list.

Pure function. The classifier already attached ``section`` to every
``LabeledBlock``; the mapper groups by section, runs the per-section
field extractor, and emits a ``SectionInstance`` per group. Every emitted
``SectionInstance`` is validated at construction time so a single bad row
never poisons the rest of the parse.

Section labels are the closed builder-vocab types, plus ``"extras"`` for
unmapped content and ``"profile"`` for the contact-info pre-section.
Profiles get a single ``data`` dict; every other section gets a list of
``data`` dicts matching the per-type shape documented in
``api/app/services/renderer/builders/*.py``.
"""

from __future__ import annotations

import re
import uuid

from app.schema.models import SectionInstance
from pydantic import ValidationError

from .classify import (
    LabeledBlock,
    PROFILE,
    UNCLASSIFIED,
    _extract_education_fields,
    _extract_experience_fields,
    _extract_profile_fields,
    _extract_simple_entries,
    _extract_skills_fields,
)
from .schemas import ConfidenceReport, FieldConfidence


SECTION_LABELS_BY_TYPE: dict[str, str] = {
    "profile": "Profile",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "certifications": "Certifications",
    "languages": "Languages",
    "research": "Research",
    "extras": "Extras",
}


def _new_id(prefix: str = "imp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _skip_header(blocks: list[LabeledBlock], heading: str | None) -> list[LabeledBlock]:
    """Drop the header line itself from per-section data inputs."""
    if not heading:
        return blocks
    target = heading.strip()
    return [b for b in blocks if b.text.strip() != target]


def _looks_like_contact_line(text: str) -> bool:
    t = text.strip()
    if "@" in t:
        return True
    digits = sum(c.isdigit() for c in t)
    return digits >= 7 and any(sep in t for sep in ("+", "-", " ", ".", "("))


def _split_dates(date_text: str) -> tuple[str, str, bool]:
    """Pull ``(start, end, current)`` from a free-form date-range string.

    Returns ``("", "", False)`` when the input is empty.
    """
    s = (date_text or "").strip()
    if not s:
        return "", "", False
    if s.lower() in ("present", "current"):
        return "", "", True
    m = re.search(
        r"(?P<start>\w+\.?\s+\d{4}|\d{1,2}/\d{4})\s*[-–—]\s*"
        r"(?P<end>\w+\.?\s+\d{4}|\d{1,2}/\d{4}|[Pp]resent|[Cc]urrent)",
        s,
    )
    if not m:
        return _coerce_year(s), "", False
    start = _coerce_year(m.group("start"))
    end_raw = m.group("end")
    current = end_raw.lower() in ("present", "current")
    end = "" if current else _coerce_year(end_raw)
    return start, end, current


def _coerce_year(value: str) -> str:
    """``Jan 2020`` → ``2020-01``; ``2020`` → ``2020-01``; else trimmed original."""
    s = value.strip()
    year_match = re.search(r"(\d{4})", s)
    if not year_match:
        return s
    year = year_match.group(1)
    month_match = re.search(r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", s)
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    month = month_map.get(month_match.group(1).lower()[:3], "01") if month_match else "01"
    return f"{year}-{month}"


def _short_label(text: str) -> str:
    """First ~24 chars of the first line, collapsed."""
    first_line = (text or "").splitlines()[0].strip()
    if not first_line:
        return ""
    if len(first_line) <= 24:
        return first_line
    return first_line[:24].rstrip()


# ---------------------------------------------------------------------------
# Per-section data builders
# ---------------------------------------------------------------------------


def _build_profile_data(blocks: list[LabeledBlock], heading: str | None) -> dict:
    """Profile is a single dict. The largest mixed-case line is the name."""
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    if not text.strip():
        return {}

    extracted = _extract_profile_fields(text)
    name_candidate = next(
        (
            b.text.strip()
            for b in cleaned
            if b.text.strip() and not _looks_like_contact_line(b.text)
        ),
        "",
    )
    return {
        "name": name_candidate,
        "title": "",
        "email": extracted.get("email", "") or "",
        "phone": extracted.get("phone", "") or "",
        "location": "",
        "site_text": "",
        "site_url": extracted.get("site_url", "") or "",
        "summary": "",
        "photo_url": "",
        "social_links": extracted.get("social_links", []) or [],
    }


def _build_experience_data(
    blocks: list[LabeledBlock], heading: str | None = None
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    rows = _extract_experience_fields(text)
    out: list[dict] = []
    for row in rows:
        dates = _split_dates(row.get("date_text", ""))
        out.append(
            {
                "id": _new_id("exp"),
                "position": row.get("position", "") or "",
                "company": row.get("company", "") or "",
                "start_date": dates[0],
                "end_date": dates[1] if dates[1] else None,
                "current": dates[2],
                "location": "",
                "description": row.get("description", "") or "",
            }
        )
    return out


def _build_education_data(
    blocks: list[LabeledBlock], heading: str | None = None
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    rows = _extract_education_fields(text)
    out: list[dict] = []
    for row in rows:
        dates = _split_dates(row.get("date_text", ""))
        out.append(
            {
                "id": _new_id("edu"),
                "institution": row.get("institution", "") or "",
                "degree": row.get("degree", "") or "",
                "start_date": dates[0],
                "end_date": dates[1] if dates[1] else None,
                "current": dates[2],
                "gpa": "",
                "summary": row.get("summary", "") or "",
            }
        )
    return out


def _build_skills_data(
    blocks: list[LabeledBlock], heading: str | None = None
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    items = _extract_skills_fields(text)
    if not items:
        return []
    return [{"id": _new_id("skg"), "category": "", "items": items}]


def _build_simple_entries(
    blocks: list[LabeledBlock],
    heading: str | None = None,
    prefix: str = "row",
    extra: dict | None = None,
    title_field: str = "title",
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    rows = _extract_simple_entries(text)
    out: list[dict] = []
    for row in rows:
        entry: dict = {"id": _new_id(prefix)}
        entry[title_field] = row.get("title", "") or ""
        if extra:
            entry.update(extra)
        entry["description"] = row.get("description", "") or ""
        out.append(entry)
    return out


def _build_extras_data(
    blocks: list[LabeledBlock], heading: str | None
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    if not cleaned:
        return []
    title = heading or "Imported content"
    fields = []
    seen: set[str] = set()
    for i, b in enumerate(cleaned):
        label = _short_label(b.text) or f"Block {i + 1}"
        base = label
        suffix = 2
        while label in seen:
            label = f"{base} ({suffix})"
            suffix += 1
        seen.add(label)
        fields.append({"label": label, "value": b.text})
    return [{"id": _new_id("ext"), "title": title, "fields": fields}]


def _validate_instance(candidate: SectionInstance) -> SectionInstance | None:
    try:
        return SectionInstance.model_validate(candidate.model_dump())
    except ValidationError:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def map_to_sections(
    labeled: list[LabeledBlock],
    confidence_entries: list,
) -> tuple[list[SectionInstance], ConfidenceReport]:
    """Group labelled blocks by section, run per-type builders, validate.

    Returns ``(instances, confidence_report)``.
    """
    by_section: dict[str, list[LabeledBlock]] = {}
    heading_for: dict[str, str | None] = {}
    for lb in labeled:
        by_section.setdefault(lb.section, []).append(lb)
        if lb.section not in heading_for and lb.source_heading:
            heading_for[lb.section] = lb.source_heading

    instances: list[SectionInstance] = []
    section_order = (
        PROFILE,
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "languages",
        "research",
        UNCLASSIFIED,
    )

    for section_label in section_order:
        blocks = by_section.get(section_label, [])
        heading = heading_for.get(section_label)

        if not blocks and section_label != UNCLASSIFIED:
            continue

        if section_label == PROFILE:
            instance = SectionInstance(
                id=_new_id("prof"),
                type="profile",
                title=SECTION_LABELS_BY_TYPE["profile"],
                enabled=True,
                data=_build_profile_data(blocks, heading),
            )
        elif section_label == "experience":
            instance = SectionInstance(
                id=_new_id("exp"),
                type="experience",
                title=SECTION_LABELS_BY_TYPE["experience"],
                enabled=True,
                data=_build_experience_data(blocks, heading),
            )
        elif section_label == "education":
            instance = SectionInstance(
                id=_new_id("edu"),
                type="education",
                title=SECTION_LABELS_BY_TYPE["education"],
                enabled=True,
                data=_build_education_data(blocks, heading),
            )
        elif section_label == "skills":
            instance = SectionInstance(
                id=_new_id("sk"),
                type="skills",
                title=SECTION_LABELS_BY_TYPE["skills"],
                enabled=True,
                data=_build_skills_data(blocks, heading),
            )
        elif section_label == "projects":
            instance = SectionInstance(
                id=_new_id("proj"),
                type="projects",
                title=SECTION_LABELS_BY_TYPE["projects"],
                enabled=True,
                data=_build_simple_entries(blocks, heading, "proj"),
            )
        elif section_label == "certifications":
            instance = SectionInstance(
                id=_new_id("cert"),
                type="certifications",
                title=SECTION_LABELS_BY_TYPE["certifications"],
                enabled=True,
                data=_build_simple_entries(blocks, heading, "cert"),
            )
        elif section_label == "languages":
            cleaned = _skip_header(blocks, heading)
            text = "\n".join(b.text for b in cleaned)
            entries = _extract_simple_entries(text)
            data = [
                {"id": _new_id("lang"), "language": e.get("title", ""), "proficiency": ""}
                for e in entries
            ]
            instance = SectionInstance(
                id=_new_id("lang"),
                type="languages",
                title=SECTION_LABELS_BY_TYPE["languages"],
                enabled=True,
                data=data,
            )
        elif section_label == "research":
            instance = SectionInstance(
                id=_new_id("res"),
                type="research",
                title=SECTION_LABELS_BY_TYPE["research"],
                enabled=True,
                data=_build_simple_entries(blocks, heading, "res"),
            )
        else:  # UNCLASSIFIED / extras
            data = _build_extras_data(blocks, heading)
            if not data:
                continue
            instance = SectionInstance(
                id=_new_id("ext"),
                type="extras",
                title=SECTION_LABELS_BY_TYPE["extras"],
                enabled=True,
                data=data,
            )

        validated = _validate_instance(instance)
        if validated is not None:
            instances.append(validated)

    fields = [FieldConfidence(path=c.path, level=c.level) for c in confidence_entries]
    overall = "high"
    if fields:
        order = {"low": 0, "medium": 1, "high": 2}
        worst = min(fields, key=lambda c: order[c.level])
        overall = worst.level
    confidence = ConfidenceReport(fields=fields, overall_level=overall)

    return instances, confidence


__all__ = ["map_to_sections"]
