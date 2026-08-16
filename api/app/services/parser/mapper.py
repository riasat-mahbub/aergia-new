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
    DATE_RANGE_RE,
    GITHUB_RE,
    LINKEDIN_RE,
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


def _new_id() -> str:
    """Stable identifier for an imported section or entry.

    Every section and entry id in the frontend uses the ``sec_`` prefix;
    the parser used to emit type-specific prefixes (``prof_``, ``edu_``,
    ...) which previously caused imported sections to be ignored by the
    customize surface's drop handler when ids did not start with ``sec_``.
    A single prefix keeps the implicit contract the rest of the codebase
    assumes; the helper no longer takes a per-type tag because the data is
    already type-typed via ``SectionInstance.type`` and ``entry.id``.
    """
    return f"sec_{uuid.uuid4().hex[:8]}"


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


_TITLE_TAIL_RE = re.compile(
    r"\s*(?:Paper|Certificate|GitHub|Repo|Link|Project)\s*↗\s*$",
    re.IGNORECASE,
)


def _strip_title_tail(title: str) -> str:
    """Drop a trailing ``Paper↗`` / ``Certificate↗`` style marker.

    Chromium exports often glue the link label onto the title text
    (``"… systems Paper↗"``); the renderer wants the bare title and
    the link label in a separate field. Only the recognised tail
    words get stripped, so foreign tails pass through unchanged.
    """
    return _TITLE_TAIL_RE.sub("", title).strip()


def _find_title_block(
    cleaned: list[LabeledBlock], title_text: str, start: int
) -> LabeledBlock | None:
    """Locate the title block for an entry in the cleaned section.

    The classifier explodes the section body into (title, description)
    pairs but doesn't tell the mapper which :class:`LabeledBlock`
    produced which pair. Match on the (stripped) title text starting
    from the cursor; return ``None`` when no match is found so the
    caller falls back to the body-wide link scan.
    """
    for i in range(start, len(cleaned)):
        if cleaned[i].text.strip().startswith(title_text):
            return cleaned[i]
    return None


def _short_label(text: str) -> str:
    """First ~24 chars of the first line, collapsed."""
    first_line = (text or "").splitlines()[0].strip()
    if not first_line:
        return ""
    if len(first_line) <= 24:
        return first_line
    return first_line[:24].rstrip()


def _build_profile_data(blocks: list[LabeledBlock], heading: str | None) -> dict:
    """Profile is a single dict. The largest mixed-case line is the name.

    When the page carries PDF ``/Annots`` URI links attached to the
    profile blocks (mailto:, linkedin, github, website), those
    supersede the regex-based extraction in
    :func:`_extract_profile_fields`. The regex fallback stays as a
    defensive layer for PDFs without annotations.
    """
    cleaned = _skip_header(blocks, heading)
    text = "\n".join(b.text for b in cleaned)
    extracted = _extract_profile_fields(text)
    name_candidate = next(
        (
            b.text.strip()
            for b in cleaned
            if b.text.strip() and not _looks_like_contact_line(b.text)
        ),
        "",
    )
    social_links: list[dict[str, str]] = list(
        extracted.get("social_links", []) or []
    )
    site_url = extracted.get("site_url", "") or ""
    email = extracted.get("email", "") or ""
    seen_uris: set[str] = {s["url"] for s in social_links if s.get("url")}
    for blk in cleaned:
        for uri in blk.links:
            if uri in seen_uris:
                continue
            if uri.startswith("mailto:"):
                email = uri[len("mailto:"):]
            elif LINKEDIN_RE.search(uri):
                if not any(s.get("label") == "LinkedIn" for s in social_links):
                    social_links.append(
                        {"url": uri, "label": "LinkedIn", "icon": ""}
                    )
                    seen_uris.add(uri)
            elif GITHUB_RE.search(uri):
                if not any(s.get("label") == "GitHub" for s in social_links):
                    social_links.append(
                        {"url": uri, "label": "GitHub", "icon": ""}
                    )
                    seen_uris.add(uri)
            elif not site_url:
                site_url = uri
    return {
        "name": name_candidate,
        "title": "",
        "email": email,
        "phone": extracted.get("phone", "") or "",
        "location": "",
        "site_text": "",
        "site_url": site_url,
        "summary": "",
        "photo_url": "",
        "social_links": social_links,
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
                "id": _new_id(),
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
                "id": _new_id(),
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
    groups = _extract_skills_fields(text)
    if not groups:
        return []
    return [
        {"id": _new_id(), "category": g.get("category", ""), "items": g.get("items", [])}
        for g in groups
    ]


def _build_simple_entries(
    blocks: list[LabeledBlock],
    heading: str | None = None,
    extra: dict | None = None,
    title_field: str = "title",
    link_field: str = "url",
    link_text_field: str = "link_text",
    date_field: str | None = None,
) -> list[dict]:
    cleaned = _skip_header(blocks, heading)
    rows = _extract_simple_entries(cleaned)
    block_index_by_label = {id(b): i for i, b in enumerate(cleaned)}
    out: list[dict] = []
    cursor = 0
    for row in rows:
        entry: dict = {"id": _new_id()}
        title_text_raw = (row.get("title", "") or "").strip()
        title_text = _strip_title_tail(title_text_raw)
        entry[title_field] = title_text
        if extra:
            entry.update(extra)
        entry["description"] = row.get("description", "") or ""
        collected_links: list[str] = []
        collected_date = ""
        title_block = _find_title_block(cleaned, title_text, cursor)
        if title_block is not None:
            title_idx = block_index_by_label[id(title_block)]
            cursor = title_idx + 1
            # Walk forward through cleaned[] until the next bold
            # (entry-title) block, gathering every link URI on the
            # way. The bold heuristic mirrors
            # ``_extract_simple_entries``'s entry boundaries.
            while cursor < len(cleaned):
                blk = cleaned[cursor]
                if blk.is_bold:
                    break
                for uri in blk.links:
                    if uri not in collected_links:
                        collected_links.append(uri)
                if date_field and not collected_date:
                    m = DATE_RANGE_RE.search(blk.text)
                    if m:
                        collected_date = m.group(0)
                cursor += 1
        if title_block is not None and title_block.links:
            entry[link_field] = title_block.links[0]
            link_text = "↗"
        elif collected_links:
            entry[link_field] = collected_links[0]
            link_text = "↗"
        else:
            link_text = ""
        if len(collected_links) > 1 and entry.get(link_field) in collected_links:
            entry["extra_links"] = [
                u for u in collected_links if u != entry.get(link_field)
            ]
        if not entry.get(link_text_field):
            entry[link_text_field] = link_text or "↗"
        # Strip a trailing link indicator
        # Strip a trailing link indicator (``GitHub↗`` etc.) from the
        # description when it was glued onto the title's wrapped line.
        desc = entry["description"]
        desc_clean = _TITLE_TAIL_RE.sub("", desc)
        if desc_clean != desc:
            entry["description"] = desc_clean.strip()
        if date_field and collected_date:
            entry[date_field] = collected_date
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
    return [{"id": _new_id(), "title": title, "fields": fields}]


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
                id=_new_id(),
                type="profile",
                title=SECTION_LABELS_BY_TYPE["profile"],
                enabled=True,
                data=_build_profile_data(blocks, heading),
            )
        elif section_label == "experience":
            instance = SectionInstance(
                id=_new_id(),
                type="experience",
                title=SECTION_LABELS_BY_TYPE["experience"],
                enabled=True,
                data=_build_experience_data(blocks, heading),
            )
        elif section_label == "education":
            instance = SectionInstance(
                id=_new_id(),
                type="education",
                title=SECTION_LABELS_BY_TYPE["education"],
                enabled=True,
                data=_build_education_data(blocks, heading),
            )
        elif section_label == "skills":
            instance = SectionInstance(
                id=_new_id(),
                type="skills",
                title=SECTION_LABELS_BY_TYPE["skills"],
                enabled=True,
                data=_build_skills_data(blocks, heading),
            )
        elif section_label == "projects":
            instance = SectionInstance(
                id=_new_id(),
                type="projects",
                title=SECTION_LABELS_BY_TYPE["projects"],
                enabled=True,
                data=_build_simple_entries(
                    blocks,
                    heading,
                    title_field="name",
                    link_field="url",
                    link_text_field="link_text",
                ),
            )
        elif section_label == "certifications":
            instance = SectionInstance(
                id=_new_id(),
                type="certifications",
                title=SECTION_LABELS_BY_TYPE["certifications"],
                enabled=True,
                data=_build_simple_entries(
                    blocks,
                    heading,
                    title_field="title",
                    link_field="url",
                    link_text_field="link_text",
                ),
            )
        elif section_label == "languages":
            cleaned = _skip_header(blocks, heading)
            entries = _extract_simple_entries(cleaned)
            data = [
                {"id": _new_id(), "language": e.get("title", ""), "proficiency": ""}
                for e in entries
            ]
            instance = SectionInstance(
                id=_new_id(),
                type="languages",
                title=SECTION_LABELS_BY_TYPE["languages"],
                enabled=True,
                data=data,
            )
        elif section_label == "research":
            instance = SectionInstance(
                id=_new_id(),
                type="research",
                title=SECTION_LABELS_BY_TYPE["research"],
                enabled=True,
                data=_build_simple_entries(
                    blocks,
                    heading,
                    title_field="title",
                    link_field="paper_url",
                    link_text_field="paper_link_text",
                    date_field="publication_date",
                ),
            )
        else:  # UNCLASSIFIED / extras
            data = _build_extras_data(blocks, heading)
            if not data:
                continue
            instance = SectionInstance(
                id=_new_id(),
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
