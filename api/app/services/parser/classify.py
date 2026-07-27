"""Classification layer — :class:`ExtractedDocument` → labeled blocks.

Pure function. Returns a tuple of:

- ``labeled``: a list of :class:`LabeledBlock` records, each a :class:`TextBlock`
  annotated with the section it belongs to (or :data:`UNCLASSIFIED` for
  leftovers) and a confidence level per the regex/heuristic match quality;
- ``confidence_fields``: a list of :class:`FieldConfidenceEntry` entries that
  the mapper will surface as ambiguous fields in the editor.

Section detection is title-driven: scan candidate headers (bold or font-size
≥ 1.15 × page-median body font size AND looks like a header — short,
mostly uppercase, no terminal punctuation), match against
:data:`SECTION_ALIASES` (case-insensitive, punctuation-stripped), then span
each section through the next header on the same page. An unknown bold
header closes the previous section and opens a new ``"extras"`` span so
unmapped content survives.

Header pre-section on page 1 maps to ``"profile"`` with the contact-info
regex set (email/phone/url/linkedin/github).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .schemas import ExtractedDocument, TextBlock


SECTION_ALIASES: dict[str, list[str]] = {
    "experience": [
        "experience",
        "work experience",
        "employment",
        "employment history",
        "professional experience",
        "work history",
    ],
    "education": [
        "education",
        "academic background",
        "academic history",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
    ],
    "projects": [
        "projects",
        "personal projects",
        "selected projects",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
    ],
    "languages": [
        "languages",
        "language skills",
    ],
    "research": [
        "research",
        "publications",
        "research experience",
    ],
}

_PROFILE_SUMMARY_ALIASES: list[str] = [
    "summary",
    "objective",
    "professional summary",
    "profile",
    "professional objective",
    "career objective",
]

PROFILE = "profile"
UNCLASSIFIED = "extras"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
URL_RE = re.compile(r"https?://[^\s]+|www\.[^\s]+")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+")
GITHUB_RE = re.compile(r"github\.com/[\w-]+")
DATE_RANGE_RE = re.compile(
    r"(?P<start>\w+\.?\s+\d{4}|\d{1,2}/\d{4})\s*[-–—]\s*"
    r"(?P<end>\w+\.?\s+\d{4}|\d{1,2}/\d{4}|[Pp]resent|[Cc]urrent)"
)
DEGREE_KEYWORDS = ("Bachelor", "Master", "B.Sc", "M.Sc", "PhD", "Diploma", "Associate")

HEADER_RATIO_THRESHOLD = 1.15
SKILL_TOKEN_MAX_LEN = 40


Confidence = Literal["high", "medium", "low"]


class FieldConfidenceEntry(BaseModel):
    """A single field's confidence. Becomes :class:`FieldConfidence` after the mapper runs.

    ``path`` mirrors a Pydantic-flavoured access path into the eventual
    ``SectionInstance.data``: ``("experience", 0, "position")``.
    """

    model_config = ConfigDict(extra="ignore")

    path: tuple[str | int, ...]
    level: Confidence


class LabeledBlock(BaseModel):
    """A :class:`TextBlock` annotated with the section it belongs to."""

    model_config = ConfigDict(extra="ignore")

    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: float
    is_bold: bool
    page: int
    section: str
    confidence: Confidence
    source_heading: str | None = None


def _normalize_title(text: str) -> str:
    lowered = text.lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", lowered)).strip()


def _header_threshold_for(page_blocks: list[TextBlock]) -> float:
    sizes = [b.font_size for b in page_blocks if not b.is_bold] or [10.0]
    sizes.sort()
    median = sizes[len(sizes) // 2]
    return median * HEADER_RATIO_THRESHOLD


def _is_candidate_header(block: TextBlock, threshold: float) -> bool:
    """A bold/large line is a candidate section header if it looks like one.

    Two checks:
    - The bold flag is set OR the font size is above the page threshold.
    - The text is header-shaped: short (<=64 chars), and either
      ALL-CAPS-ish (>= 60% uppercase letters) OR matches a known
      section/title alias.

    The bold flag is now reliable (font-family-based inference in
    ``extract._infer_font``), but bold alone admits too much — names,
    job titles, and emphasised body lines are all bold. The shape
    check keeps the false-positive rate down.
    """
    if not (block.is_bold or block.font_size >= threshold):
        return False
    text = block.text.strip()
    if not text or len(text) > 64:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    # ALL-CAPS lines (legacy heuristic) remain accepted.
    upper = sum(1 for c in letters if c.isupper())
    if upper / len(letters) >= 0.6:
        return True
    # Mixed-case lines: only accept when the text matches a known
    # section or title alias. This catches "Experience", "Research",
    # "Education", "Projects", "Skills" and their synonyms without
    # admitting bold names like "Jane Doe" or "Riasat Mahbub".
    section, is_profile = _match_section_title(text)
    return section is not None or is_profile


def _match_section_title(line: str) -> tuple[str | None, bool]:
    """Return ``(section_name_or_None, is_profile_summary_alias)``.

    Single-word aliases (``research``, ``skills``, …) match EXACTLY.
    Multi-word aliases (``research experience``, ``professional
    summary``, …) additionally prefix-match so headings like
    "Research Experience at Dalhousie" still classify. The single-word
    restriction is what stops job titles like "Research Assistant"
    (which would prefix-match ``research`` + space) from opening a
    bogus section — a real bug on the benchmark CV where the first
    experience entry is a Research Assistant role.
    """
    norm = _normalize_title(line)
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            if norm == alias:
                return section, False
            if len(alias.split()) > 1 and (
                norm.startswith(alias + " ") or norm.startswith(alias + "&")
            ):
                return section, False
    for alias in _PROFILE_SUMMARY_ALIASES:
        if norm == alias:
            return PROFILE, True
        if len(alias.split()) > 1 and norm.startswith(alias + " "):
            return PROFILE, True
    return None, False


def _detect_sections(
    blocks: list[TextBlock],
) -> list[tuple[int, int, str, str | None]]:
    """Return ``[(start, end, section, heading), ...]`` spans for the page.

    Page-scoped. Sections close on the next header (known or unknown); an
    unknown header opens an :data:`UNCLASSIFIED` span so the content
    survives unmapped.
    """
    sections: list[tuple[int, int, str, str | None]] = []
    if not blocks:
        return sections

    by_page: dict[int, list[int]] = {}
    for idx, b in enumerate(blocks):
        by_page.setdefault(b.page, []).append(idx)

    for page, indices in by_page.items():
        page_blocks = [blocks[i] for i in indices]
        threshold = _header_threshold_for(page_blocks)

        current_section: str | None = None
        current_heading: str | None = None
        current_start: int | None = None

        for idx in indices:
            block = blocks[idx]
            if not _is_candidate_header(block, threshold):
                continue

            section, is_profile_summary = _match_section_title(block.text)
            close_existing = current_section is not None and current_start is not None

            if section is not None and not is_profile_summary:
                if close_existing:
                    sections.append(
                        (current_start, idx - 1, current_section, current_heading)
                    )
                current_section = section
                current_heading = block.text
                current_start = idx
                continue

            if is_profile_summary and current_section is None and page == 0:
                current_section = PROFILE
                current_heading = block.text
                current_start = idx
                continue

            # Unknown bold header — close current and start an extras span.
            if close_existing:
                sections.append(
                    (current_start, idx - 1, current_section, current_heading)
                )
            current_section = UNCLASSIFIED
            current_heading = block.text
            current_start = idx

        if current_section is not None and current_start is not None:
            sections.append((current_start, indices[-1], current_section, current_heading))

    return sections


def _split_entries(text: str) -> list[list[str]]:
    raw = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    return [[line.strip() for line in chunk.splitlines() if line.strip()] for chunk in raw]


def _extract_experience_fields(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    bullet_re = re.compile(r"^\s*[•\-*]\s+")
    for lines in _split_entries(text):
        if not lines:
            continue
        position = ""
        company = ""
        date_text = ""
        description_lines: list[str] = []
        non_meta: list[str] = []
        for line in lines:
            if bullet_re.match(line):
                description_lines.append(bullet_re.sub("", line))
                continue
            if DATE_RANGE_RE.search(line):
                date_text = line
                continue
            non_meta.append(line)

        if non_meta:
            for sep in (" — ", " – ", " - ", " at ", " @ "):
                if sep in non_meta[0]:
                    position, company = non_meta[0].split(sep, 1)
                    break
            else:
                position = non_meta[0]
                # Ambiguous: a second non-meta line is a candidate company.
                if len(non_meta) >= 2:
                    company = non_meta[1]

        entries.append(
            {
                "position": position,
                "company": company,
                "date_text": date_text,
                "description": "\n".join(description_lines).strip(),
            }
        )
    return entries


def _extract_education_fields(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for lines in _split_entries(text):
        if not lines:
            continue
        degree = ""
        institution = ""
        date_text = ""
        summary = ""
        for line in lines:
            if any(k.lower() in line.lower() for k in DEGREE_KEYWORDS):
                if not degree:
                    degree = line
                else:
                    summary = line
                continue
            if DATE_RANGE_RE.search(line):
                date_text = line
                continue
            if not institution:
                institution = line
            else:
                summary = (summary + "\n" + line).strip() if summary else line
        entries.append(
            {
                "degree": degree,
                "institution": institution,
                "date_text": date_text,
                "summary": summary,
            }
        )
    return entries


def _extract_skills_fields(text: str) -> list[str]:
    items: list[str] = []
    for t in re.split(r"[,\n;•]+", text):
        cleaned = t.strip()
        if not cleaned or len(cleaned) > SKILL_TOKEN_MAX_LEN:
            continue
        items.append(cleaned)
    return items


def _extract_simple_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for lines in _split_entries(text):
        if not lines:
            continue
        title = lines[0]
        description = "\n".join(lines[1:]).strip()
        entries.append({"title": title, "description": description})
    return entries


def _extract_profile_fields(text: str) -> dict[str, object]:
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    url_match = URL_RE.search(text)
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)

    social_links: list[dict[str, str]] = []
    if linkedin_match:
        social_links.append(
            {
                "url": "https://" + linkedin_match.group(0),
                "label": "LinkedIn",
                "icon": "",
            }
        )
    if github_match:
        social_links.append(
            {
                "url": "https://" + github_match.group(0),
                "label": "GitHub",
                "icon": "",
            }
        )
    site_url = ""
    if url_match and not linkedin_match and not github_match:
        site_url = url_match.group(0)
    return {
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "site_url": site_url,
        "social_links": social_links,
    }


def classify(
    extracted: ExtractedDocument,
) -> tuple[list[LabeledBlock], list[FieldConfidenceEntry]]:
    """Tag every block with the section it belongs to (or extras)."""
    blocks = extracted.blocks
    sections = _detect_sections(blocks)
    confidences: list[FieldConfidenceEntry] = []

    page1_first_section_idx: int | None = None
    for start, _end, _section, _heading in sections:
        if start < len(blocks) and blocks[start].page == 0:
            page1_first_section_idx = start
            break

    profile_block_indices: list[int] = []
    end = page1_first_section_idx if page1_first_section_idx is not None else len(blocks)
    for idx, b in enumerate(blocks):
        if b.page != 0 or idx >= end:
            continue
        profile_block_indices.append(idx)

    section_lookup: dict[int, tuple[str, str | None]] = {}
    for start, end_idx, section, heading in sections:
        for idx in range(start, end_idx + 1):
            section_lookup[idx] = (section, heading)

    labeled: list[LabeledBlock] = []
    for idx, block in enumerate(blocks):
        if idx in section_lookup:
            section, heading = section_lookup[idx]
            labeled.append(
                LabeledBlock(
                    text=block.text,
                    x=block.x,
                    y=block.y,
                    width=block.width,
                    height=block.height,
                    font_size=block.font_size,
                    is_bold=block.is_bold,
                    page=block.page,
                    section=section,
                    confidence="medium",
                    source_heading=heading,
                )
            )
            continue
        if idx in profile_block_indices:
            labeled.append(
                LabeledBlock(
                    text=block.text,
                    x=block.x,
                    y=block.y,
                    width=block.width,
                    height=block.height,
                    font_size=block.font_size,
                    is_bold=block.is_bold,
                    page=block.page,
                    section=PROFILE,
                    confidence="high",
                    source_heading=None,
                )
            )
            continue
        labeled.append(
            LabeledBlock(
                text=block.text,
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                font_size=block.font_size,
                is_bold=block.is_bold,
                page=block.page,
                section=UNCLASSIFIED,
                confidence="low",
                source_heading=None,
            )
        )

    for start, end_idx, section_name, _heading in sections:
        body = "\n".join(b.text for b in blocks[start : end_idx + 1])
        if not body.strip():
            continue
        if section_name == "experience":
            plan = _extract_experience_fields(body)
            for i, entry in enumerate(plan):
                if entry.get("position") and not entry.get("company"):
                    confidences.append(
                        FieldConfidenceEntry(
                            path=("experience", i, "position"), level="low"
                        )
                    )
                    confidences.append(
                        FieldConfidenceEntry(path=("experience", i, "company"), level="low")
                    )
                if entry.get("date_text"):
                    confidences.append(
                        FieldConfidenceEntry(
                            path=("experience", i, "date_text"), level="high"
                        )
                    )
        elif section_name == "education":
            plan = _extract_education_fields(body)
            for i, entry in enumerate(plan):
                if entry.get("degree"):
                    confidences.append(
                        FieldConfidenceEntry(
                            path=("education", i, "degree"), level="medium"
                        )
                    )
                if entry.get("institution"):
                    confidences.append(
                        FieldConfidenceEntry(
                            path=("education", i, "institution"), level="medium"
                        )
                    )
        elif section_name == "skills":
            plan = _extract_skills_fields(body)
            for j in range(len(plan)):
                confidences.append(
                    FieldConfidenceEntry(path=("skills", "items", j), level="high")
                )
        elif section_name in ("projects", "certifications", "languages", "research"):
            plan = _extract_simple_entries(body)
            for i, entry in enumerate(plan):
                if entry.get("title"):
                    confidences.append(
                        FieldConfidenceEntry(
                            path=(section_name, i, "title"), level="medium"
                        )
                    )

    if profile_block_indices:
        header_text = "\n".join(blocks[i].text for i in profile_block_indices)
        plan = _extract_profile_fields(header_text)
        if plan.get("email"):
            confidences.append(FieldConfidenceEntry(path=("profile", "email"), level="high"))
        if plan.get("phone"):
            confidences.append(FieldConfidenceEntry(path=("profile", "phone"), level="high"))
        if plan.get("site_url"):
            confidences.append(
                FieldConfidenceEntry(path=("profile", "site_url"), level="high")
            )

    return labeled, confidences


__all__ = [
    "SECTION_ALIASES",
    "PROFILE",
    "UNCLASSIFIED",
    "LabeledBlock",
    "FieldConfidenceEntry",
    "classify",
]
