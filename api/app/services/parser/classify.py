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

# Bare domain in a contact line: "rmahbub.com" between middots/space.
# Must be preceded by whitespace/middot (not "@") so email hosts don't match.
_BARE_DOMAIN_RE = re.compile(
    r"(?:^|[\s·])([a-z0-9-]+\.(?:com|io|dev|me|net|org|co|ai|app))(?:[\s·]|$)",
    re.IGNORECASE,
)

# "Programming Languages: TypeScript, JavaScript" -> ("Programming Languages", …)
_SKILL_CATEGORY_RE = re.compile(r"^([A-Z][A-Za-z0-9 &/+-]+):\s*(.*)$")

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
    # URIs attached to the underlying :class:`TextBlock` via PDF
    # ``/Annots`` link annotations. Mirrors the same field on
    # :class:`TextBlock` so classifier→mapper boundary stays
    # lossless.
    links: list[str] = []


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


def _looks_like_position_title(line: str) -> bool:
    """A line that could open a new experience entry.

    A title is short (<= 6 words), contains no internal punctuation
    (period / comma / colon / semicolon), and is not a date range.
    Description paragraphs are long sentences or contain punctuation,
    so they don't qualify — this is what keeps paragraph wraps like
    "patterns across 482 large-scale repositories. Leveraged" (has a
    period) out of the title role on the benchmark CV.
    """
    if DATE_RANGE_RE.search(line):
        return False
    if any(ch in line for ch in (".", ",", ":", ";")):
        return False
    words = line.split()
    return 0 < len(words) <= 6


def _extract_experience_fields(text: str) -> list[dict[str, str]]:
    """Split an experience section into entries.

    The old implementation split on blank lines only; modern resumes
    omit blank lines between entries, so every entry collapsed into
    one. The new splitter walks lines in order and opens a new entry
    when a title-shaped line appears AFTER the current entry already
    has a date (i.e. the position line of the next entry). Within an
    entry, the second title-shaped line before any date is the company.

    Description lines — the ones that fail the title shape (long or
    punctuated) — accumulate into the current entry's description,
    bullets stripped. This recovers running-paragraph descriptions
    that the old bullet-only gate dropped entirely.
    """
    entries: list[dict[str, str]] = []
    bullet_re = re.compile(r"^\s*[•\-*]\s+")
    for lines in _split_entries(text):
        if not lines:
            continue
        position = ""
        company = ""
        date_text = ""
        description_lines: list[str] = []

        def _flush() -> None:
            entries.append(
                {
                    "position": position,
                    "company": company,
                    "date_text": date_text,
                    "description": "\n".join(description_lines).strip(),
                }
            )

        for line in lines:
            if bullet_re.match(line):
                description_lines.append(bullet_re.sub("", line))
                continue
            if DATE_RANGE_RE.search(line):
                date_text = line
                continue
            if _looks_like_position_title(line):
                # A title-shaped line after the current entry has a date
                # opens the NEXT entry; a title-shaped line with no date
                # yet is this entry's company (title/company pair).
                if date_text and (position or description_lines):
                    _flush()
                    position = ""
                    company = ""
                    date_text = ""
                    description_lines = []
                if not position:
                    for sep in (" — ", " – ", " - ", " at ", " @ "):
                        if sep in line:
                            position, company = line.split(sep, 1)
                            break
                    else:
                        position = line
                elif not company:
                    company = line
                continue
            description_lines.append(line)

        _flush()
    return entries


def _extract_education_fields(text: str) -> list[dict[str, str]]:
    """Split an education section into entries.

    The old implementation split on blank lines only; resumes that join
    entries without blank lines (degree, institution, date, next
    degree, …) collapsed into a single entry with the last date winning.
    The new splitter walks lines in order and closes the current entry
    when a second degree-keyword line appears, so each
    degree / institution / date triple becomes its own entry.
    """
    entries: list[dict[str, str]] = []
    for lines in _split_entries(text):
        if not lines:
            continue
        degree = ""
        institution = ""
        date_text = ""
        summary = ""

        def _flush() -> None:
            if degree or institution:
                entries.append(
                    {
                        "degree": degree,
                        "institution": institution,
                        "date_text": date_text,
                        "summary": summary,
                    }
                )

        for line in lines:
            if any(k.lower() in line.lower() for k in DEGREE_KEYWORDS):
                if degree:
                    _flush()
                    degree = ""
                    institution = ""
                    date_text = ""
                    summary = ""
                degree = line
                continue
            if DATE_RANGE_RE.search(line):
                date_text = line
                continue
            if not institution:
                institution = line
            else:
                summary = (summary + "\n" + line).strip() if summary else line
        _flush()
    return entries


def _is_letterspaced_junk(token: str) -> bool:
    """True when the token is letter-spaced filler (``A u g u s t``).

    Chromium letter-spaces right-rail date labels, and pypdf extracts
    each letter with a space between. Legit skill tokens like "GitHub
    Actions" have one space in a long token; letter-spaced junk has a
    space after nearly every character (> 1/3 of the token is spaces).
    """
    if not token or " " not in token:
        return False
    return token.count(" ") > len(token) / 3


def _extract_skills_fields(text: str) -> list[dict[str, list[str]]]:
    """Split a skills section into ``{"category", "items"}`` groups.

    Lines starting with ``Category: item1, item2`` peel the category
    prefix; subsequent lines without a prefix accumulate into the most
    recent category. Unprefixed input (``Python, Go, Rust``) becomes a
    single group with an empty category, matching the mapper's
    existing contract.

    Letter-spaced junk (Chromium date labels) is dropped so skills
    stay clean on real-world exports.
    """
    groups: list[dict[str, list[str]]] = []
    category = ""
    items: list[str] = []

    def _flush() -> None:
        if items:
            groups.append({"category": category, "items": list(items)})
            items.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _SKILL_CATEGORY_RE.match(line)
        if m:
            _flush()
            category = m.group(1)
            rest = m.group(2)
        else:
            rest = line
        for token in re.split(r"[,\n;•]+", rest):
            cleaned = token.strip()
            if not cleaned or len(cleaned) > SKILL_TOKEN_MAX_LEN:
                continue
            if _is_letterspaced_junk(cleaned):
                continue
            items.append(cleaned)
    _flush()
    return groups


def _extract_simple_entries(
    blocks: list[TextBlock],
) -> list[dict[str, str]]:
    """Split a title + description section (projects, research, …) into entries.

    Titles are the bold lines of the section when any body line is bold
    (the reliable signal from the font-family extractor); otherwise the
    title-shaped text heuristic applies. Description lines accumulate
    until the next title. This handles real resumes where entries are
    joined without blank lines and titles are long (paper titles),
    which the old blank-line splitter collapsed into one entry.
    """
    texts = [b.text for b in blocks]
    if not texts:
        return []

    bold_idx = [i for i, b in enumerate(blocks) if b.is_bold]
    # First bold line is the section heading (already skipped by the
    # mapper, but the confidence path passes the raw span).
    if bold_idx and len(bold_idx) >= 1:
        title_indices = {i for i in bold_idx}
        # If the very first bold line is the heading, drop it — the
        # caller passes the section body without the heading when it
        # can, so this only guards the classify() confidence path.
        first_text = texts[0]
        if bold_idx[0] == 0 and len(bold_idx) > 1 and _normalize_title(first_text) in (
            alias
            for aliases in SECTION_ALIASES.values()
            for alias in aliases
        ):
            title_indices.discard(0)
    else:
        title_indices = {
            i for i, t in enumerate(texts) if _looks_like_position_title(t)
        }

    entries: list[dict[str, str]] = []
    current_title = ""
    desc_lines: list[str] = []
    for i, text in enumerate(texts):
        if i in title_indices:
            if current_title:
                entries.append(
                    {"title": current_title, "description": "\n".join(desc_lines).strip()}
                )
            current_title = text
            desc_lines = []
        else:
            desc_lines.append(text)
    if current_title:
        entries.append(
            {"title": current_title, "description": "\n".join(desc_lines).strip()}
        )
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
    if not site_url:
        # Real-world contact lines omit the scheme: "rmahbub.com".
        # Only accept the domain when it's delimited by whitespace or
        # a middot, so an email host ("gmail.com" inside an address)
        # never leaks into site_url.
        bare = _BARE_DOMAIN_RE.search(text)
        if bare:
            site_url = "https://" + bare.group(1)
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
                    links=list(block.links),
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
                    links=list(block.links),
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
                links=list(block.links),
            )
        )


    for start, end_idx, section_name, _heading in sections:
        # Skip the heading block itself (it would otherwise be parsed
        # as the first entry's title by the text-based extractors).
        body_blocks = blocks[start + 1 : end_idx + 1]
        body = "\n".join(b.text for b in body_blocks)
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
            for j in range(sum(len(g.get("items", [])) for g in plan)):
                confidences.append(
                    FieldConfidenceEntry(path=("skills", "items", j), level="high")
                )
        elif section_name in ("projects", "certifications", "languages", "research"):
            plan = _extract_simple_entries(body_blocks)
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
