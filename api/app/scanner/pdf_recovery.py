"""Aergia-parser text recovery checks for actual CV PDFs.

This reports what Aergia's own parser recovered. It does not claim universal
compatibility with third-party ATS products.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import unicodedata
from bisect import bisect_left
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.core.safe_url import normalize_url
from app.scanner.matching import flatten_cv_text
from app.scanner.results import (
    PDFCheck,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
)
from app.services.renderer.pipeline import prepare_render_source, resolve_source


PDF_ANALYSIS_VERSION = "aergia-pdf-recovery-v3"
MAX_PDF_INPUT_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_EXTRACTED_TEXT_CHARS = 2_000_000
MAX_PDF_LINKS = 500
MAX_DATE_ASSOCIATION_TOKEN_DISTANCE = 32
PDF_WORKER_TIMEOUT_SECONDS = 12.0
PDF_WORKER_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
PDF_WORKER_MAX_CONCURRENCY = 2
PDF_WORKER_MEMORY_LIMIT_BYTES = 1_500_000_000
_PDF_WORKER_SLOTS = threading.BoundedSemaphore(PDF_WORKER_MAX_CONCURRENCY)
# Keep technical tokens intact while allowing all Unicode word characters.
# ``\w`` is Unicode-aware in Python's default regex mode; the punctuation
# alternatives preserve common CV terms such as C++, C#, .NET, CI/CD, and
# Node.js.
_TOKEN_RE = re.compile(
    r"(?:\.[^\W_][\w+#.-]*|[^\W_][\w]*(?:[+#]+|(?:[./-][\w+#]+)+)*)",
    re.UNICODE,
)
_DASHES = str.maketrans({char: "-" for char in "‐‑‒–—―−﹘﹣－"})

_CRITICAL_CHECKS = frozenset({"text_retention", "reading_order", "contact_recovery"})
_ENTRY_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "experience": ("position", "company"),
    "work_experience": ("position", "company"),
    "projects": ("project", "name"),
    "project": ("project", "name"),
    "research": ("paper", "title", "venue"),
    "education": ("degree", "institution"),
    "certifications": ("certification", "issuer"),
}
_ENTRY_RECOVERY_TYPES = frozenset(_ENTRY_LABEL_FIELDS)


@dataclass(frozen=True, slots=True)
class _RenderAnchor:
    """One structural text anchor in the renderer's intended order."""

    identity: str
    text: str
    kind: str
    section_type: str = ""


@dataclass(frozen=True, slots=True)
class _RenderLink:
    label: str
    target: str
    visible_text: str = ""

    @property
    def identity(self) -> str:
        """Human-readable link identity used by persisted recovery checks."""

        return self.label


@dataclass(frozen=True, slots=True)
class _DateAssociation:
    identity: str
    section_type: str
    label: str
    date_text: str
    body_anchor: str = ""


@dataclass(frozen=True, slots=True)
class _RenderExpectations:
    visible_text: tuple[str, ...]
    headings: tuple[_RenderAnchor, ...]
    entries: tuple[_RenderAnchor, ...]
    ordered_anchors: tuple[_RenderAnchor, ...]
    contacts: tuple[str, ...]
    links: tuple[_RenderLink, ...]
    date_associations: tuple[_DateAssociation, ...]


def _value(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _dump(cv: object) -> object:
    if hasattr(cv, "model_dump"):
        return cv.model_dump(mode="python")  # type: ignore[union-attr]
    if hasattr(cv, "sections"):
        return {
            "sections": getattr(cv, "sections"),
            "customizations": getattr(cv, "customizations", None),
            "template_id": getattr(cv, "template_id", None),
        }
    return cv


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).translate(_DASHES).casefold()
    return " ".join(value.split())


def _tokens(value: str) -> list[str]:
    return [_normalize(token) for token in _TOKEN_RE.findall(value)]


def _ordered_match_count(expected: Sequence[str], recovered: Sequence[str]) -> int:
    """Count an ordered subsequence without consuming a missing token.

    The previous greedy scan advanced through all recovered tokens while
    looking for a missing expected token and then terminated.  Matching from
    per-token positions skips that missing token and still preserves order.
    """

    positions: dict[str, list[int]] = {}
    for index, token in enumerate(recovered):
        positions.setdefault(token, []).append(index)
    cursor = 0
    count = 0
    for token in expected:
        candidates = positions.get(token)
        if not candidates:
            continue
        position_index = bisect_left(candidates, cursor)
        if position_index == len(candidates):
            continue
        cursor = candidates[position_index] + 1
        count += 1
    return count


def _check_status(ratio: float, code: str | None = None) -> PDFRecoveryStatus:
    """Map a check ratio to status using check-specific severity.

    Text/order/contact failures are critical.  Headings, entries, and links
    still report a warning when substantially incomplete, but cannot by
    themselves mark the whole PDF as unusable.
    """

    if ratio >= 0.96:
        return PDFRecoveryStatus.PASS
    if code == "contact_recovery" and ratio > 0:
        # A partially recovered contact set is actionable, but it is not the
        # same as losing every primary contact field.
        return PDFRecoveryStatus.WARNING
    if ratio >= 0.80:
        return PDFRecoveryStatus.WARNING
    if code not in _CRITICAL_CHECKS:
        return PDFRecoveryStatus.WARNING
    return PDFRecoveryStatus.FAIL


def _field_visible_text(field: object) -> str:
    blocks = _value(field, "blocks")
    if isinstance(blocks, Sequence) and not isinstance(blocks, (str, bytes, bytearray)) and blocks:
        parts: list[str] = []
        for block in blocks:
            items = _value(block, "items", [])
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                parts.extend(
                    str(text).strip()
                    for item in items
                    if (text := _value(item, "text")) is not None and str(text).strip()
                )
        return " ".join(parts)
    runs = _value(field, "runs", [])
    if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes, bytearray)):
        return ""
    return " ".join(
        str(text).strip()
        for run in runs
        if (text := _value(run, "text")) is not None and str(text).strip()
    )


def _section_policy_visible(section: object) -> bool:
    if _value(section, "enabled", True) is False:
        return False
    policy = _value(section, "policy")
    if policy is None:
        style = _value(section, "style")
        policy = _value(style, "policy") if style is not None else None
    if policy is not None:
        return _value(policy, "show_title", True) is not False
    section_type = str(_value(section, "type", ""))
    # Keep this fallback aligned with the canonical renderer defaults.
    return section_type != "profile"


def _entry_label(section_type: str, entry: object) -> str:
    fields = _value(entry, "fields", [])
    if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes, bytearray)):
        return ""
    allowed = _ENTRY_LABEL_FIELDS.get(section_type, ("title", "name", "category"))
    for key in allowed:
        for field in fields:
            if str(_value(field, "key", "")).casefold() == key.casefold():
                text = _field_visible_text(field).strip()
                if text:
                    return text
    return ""


def _render_expectations(cv: object, render_manifest: object | None = None) -> _RenderExpectations | None:
    """Build recovery expectations from the canonical renderer model.

    Wire CV data is transformed by the same builders and policies used for
    HTML/PDF output.  This prevents raw dates, hidden headings, metadata, and
    arbitrary URL-shaped fields from becoming false recovery obligations.
    """

    source = _dump(cv)
    sections = _value(source, "sections", [])
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes, bytearray)):
        return None
    try:
        prepared = prepare_render_source(
            sections,
            render_manifest,
            _value(source, "customizations", {}) or {},
        )
        model = resolve_source(prepared)
    except (TypeError, ValueError, AttributeError, KeyError):
        return None

    visible_text: list[str] = []
    headings: list[_RenderAnchor] = []
    entries: list[_RenderAnchor] = []
    contacts: list[str] = []
    links: list[_RenderLink] = []
    date_associations: list[_DateAssociation] = []
    ordered_anchors: list[_RenderAnchor] = []

    for zone in model.zones:
        for section_id in zone.section_ids:
            section = model.sections.get(section_id)
            if section is None or not section.enabled:
                continue
            if section.policy is None or section.policy.show_title:
                title = str(section.title or "").strip()
                if title:
                    anchor = _RenderAnchor(f"heading:{section.id}", title, "heading", section.type)
                    headings.append(anchor)
                    ordered_anchors.append(anchor)
                    visible_text.append(title)
            for entry in section.entries:
                label = _entry_label(section.type, entry)
                if label and section.type in _ENTRY_RECOVERY_TYPES:
                    anchor = _RenderAnchor(f"entry:{section.id}:{entry.id}", label, "entry", section.type)
                    entries.append(anchor)
                    ordered_anchors.append(anchor)
                    date_text = next(
                        (
                            text
                            for field in entry.fields
                            if str(field.key).casefold() == "date"
                            and (text := _field_visible_text(field).strip())
                        ),
                        "",
                    )
                    if date_text:
                        body_anchor = next(
                            (
                                text
                                for field in entry.fields
                                if str(_value(field, "group", "")).casefold() in {"body", "summary"}
                                and (text := _field_visible_text(field).strip())
                            ),
                            "",
                        )
                        date_associations.append(
                            _DateAssociation(anchor.identity, section.type, label, date_text, body_anchor)
                        )
                for field in entry.fields:
                    text = _field_visible_text(field)
                    if text:
                        visible_text.append(text)
                    if section.type == "profile" and field.key.casefold() in {"email", "phone", "telephone"}:
                        contacts.append(field.key)
                    for run in field.runs:
                        target = _value(_value(run, "style"), "link")
                        normalized = normalize_url(target)
                        if normalized:
                            text = _field_visible_text(field).strip()
                            run_text = str(_value(run, "text") or "").strip()
                            looks_like_url = bool(
                                re.match(r"^(?:https?://|www\.|[^\s]+\.[^\s]+$)", text, re.I)
                            )
                            label = text if text and not looks_like_url else ""
                            if not label:
                                label = (
                                    _entry_label(section.type, entry)
                                    or ("Portfolio" if section.type == "profile" and field.key == "site" else "Link")
                                )
                            prior = sum(item.label.split(" (", 1)[0] == label for item in links)
                            if prior:
                                label = f"{label} ({prior + 1})"
                            links.append(_RenderLink(label, normalized, run_text or text))

    return _RenderExpectations(
        visible_text=tuple(visible_text),
        headings=tuple(headings),
        entries=tuple(entries),
        ordered_anchors=tuple(ordered_anchors),
        contacts=tuple(dict.fromkeys(contacts)),
        links=tuple(dict.fromkeys(links)),
        date_associations=tuple(date_associations),
    )


def _fallback_expectations(cv: object) -> _RenderExpectations:
    """Best-effort expectations for legacy AST-shaped test/input objects."""

    source = _dump(cv)
    fields = flatten_cv_text(cv)
    visible_text = [field.text for field in fields]
    headings: list[_RenderAnchor] = []
    entries: list[_RenderAnchor] = []
    contacts: list[str] = []
    source_sections = _value(source, "sections", [])
    if isinstance(source_sections, Sequence) and not isinstance(source_sections, (str, bytes, bytearray)):
        for section in source_sections:
            if not _section_policy_visible(section):
                continue
            title = str(_value(section, "title", "") or "").strip()
            section_id = str(_value(section, "id", "") or "")
            section_type = str(_value(section, "type", "other"))
            if title:
                headings.append(_RenderAnchor(f"heading:{section_id}", title, "heading", section_type))
            data = _value(section, "data", [])
            if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
                for index, row in enumerate(data):
                    if not isinstance(row, Mapping):
                        continue
                    label = next((str(row[key]).strip() for key in _ENTRY_LABEL_FIELDS.get(section_type, ("title", "name")) if row.get(key)), "")
                    if label:
                        entries.append(_RenderAnchor(f"entry:{section_id}:{row.get('id', index)}", label, "entry", section_type))
            if section_type == "profile" and isinstance(data, Mapping):
                contacts.extend(key for key in ("email", "phone", "telephone") if data.get(key))
    return _RenderExpectations(
        visible_text=tuple(visible_text),
        headings=tuple(headings),
        entries=tuple(entries),
        ordered_anchors=tuple([*headings, *entries]),
        contacts=tuple(dict.fromkeys(contacts)),
        links=(),
        date_associations=(),
    )


def _expectations_for(cv: object, render_manifest: object | None = None) -> _RenderExpectations:
    return _render_expectations(cv, render_manifest) or _fallback_expectations(cv)


def _entry_titles(cv: object, allowed_types: set[str]) -> list[tuple[str, str]]:
    expectations = _expectations_for(cv)
    return [(item.section_type, item.text) for item in expectations.entries if item.section_type in allowed_types][:500]


def _run_bounded_pdf_worker(pdf_bytes: bytes) -> dict[str, object]:
    """Extract PDF text in an isolated process with time and concurrency caps."""

    if not _PDF_WORKER_SLOTS.acquire(timeout=0.25):
        return {"error": "worker_busy"}
    try:
        api_root = Path(__file__).resolve().parents[2]
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "app.scanner.pdf_worker"],
                cwd=api_root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return {"error": "worker_unavailable"}

        try:
            stdout, _ = process.communicate(
                input=pdf_bytes,
                timeout=PDF_WORKER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return {"error": "worker_timeout"}

        if process.returncode != 0:
            return {"error": "worker_resource_limit"}
        if len(stdout) > PDF_WORKER_MAX_RESPONSE_BYTES:
            return {"error": "worker_output_limit"}
        try:
            payload = json.loads(stdout)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"error": "worker_invalid_response"}
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            error = payload.get("error") if isinstance(payload, dict) else None
            return {"error": error if isinstance(error, str) else "pdf_extraction_failed"}
        page_count = payload.get("page_count")
        plain_text = payload.get("plain_text")
        links = payload.get("links")
        secondary_plain_text = payload.get("secondary_plain_text")
        if (
            not isinstance(page_count, int)
            or isinstance(page_count, bool)
            or page_count < 0
            or not isinstance(plain_text, str)
            or len(plain_text) > MAX_EXTRACTED_TEXT_CHARS
            or not isinstance(links, list)
            or len(links) > MAX_PDF_LINKS
            or any(not isinstance(link, str) or len(link) > 2_000 for link in links)
            or secondary_plain_text is not None
            and (
                not isinstance(secondary_plain_text, str)
                or len(secondary_plain_text) > MAX_EXTRACTED_TEXT_CHARS
            )
        ):
            return {"error": "worker_invalid_response"}
        return payload
    finally:
        _PDF_WORKER_SLOTS.release()


def _worker_failure(code: str) -> PDFTextRecoveryAnalysis:
    explanations = {
        "worker_busy": "PDF text recovery was skipped because all scanner workers are busy.",
        "worker_unavailable": "The bounded PDF text-recovery worker could not be started.",
        "worker_timeout": "PDF text recovery exceeded its processing-time limit.",
        "worker_resource_limit": "PDF text recovery stopped after reaching a processing resource limit.",
        "worker_output_limit": "PDF text recovery exceeded the configured result-size limit.",
        "worker_invalid_response": "The PDF text-recovery worker returned an invalid result.",
    }
    is_busy_or_timeout = code in {"worker_busy", "worker_timeout"}
    status = PDFRecoveryStatus.WARNING if is_busy_or_timeout else PDFRecoveryStatus.FAIL
    return PDFTextRecoveryAnalysis(
        status=status,
        checks=[
            PDFCheck(
                code=code if code in explanations else "pdf_extraction_failed",
                status=status,
                explanation=explanations.get(
                    code,
                    "Aergia could not recover readable PDF text within the configured limits.",
                ),
            )
        ],
    )


def _line_token_spans(text: str) -> list[tuple[str, int, int]]:
    """Return normalized line text and its token span in the full document."""

    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for line in text.splitlines():
        tokens = _tokens(line)
        if tokens:
            spans.append((_normalize(line), cursor, cursor + len(tokens)))
            cursor += len(tokens)
    return spans


def _find_token_occurrence(
    tokens: Sequence[str],
    pattern: Sequence[str],
    used: set[int],
    *,
    candidates: Sequence[int] | None = None,
) -> tuple[int, int] | None:
    if not pattern:
        return None
    starts = candidates if candidates is not None else range(max(0, len(tokens) - len(pattern) + 1))
    for start in starts:
        end = start + len(pattern)
        if end > len(tokens) or any(index in used for index in range(start, end)):
            continue
        if list(tokens[start:end]) == list(pattern):
            return start, end
    return None


def _anchor_matches(
    anchors: Sequence[_RenderAnchor],
    recovered_text: str,
) -> tuple[list[_RenderAnchor], list[str], list[str], list[str]]:
    """Match structural anchors with occurrence accounting.

    Headings use exact extracted lines to avoid counting a body mention. Entry
    labels use token occurrences because a parser may place adjacent fields on
    one line. One token occurrence can satisfy only one anchor.
    """

    tokens = _tokens(recovered_text)
    line_spans = _line_token_spans(recovered_text)
    used: set[int] = set()
    recovered: list[_RenderAnchor] = []
    missing: list[str] = []
    positions: list[int] = []
    for anchor in anchors:
        pattern = _tokens(anchor.text)
        candidates: list[int] | None = None
        if anchor.kind == "heading":
            candidates = [start for line, start, end in line_spans if _tokens(line) == pattern and end - start == len(pattern)]
        match = _find_token_occurrence(tokens, pattern, used, candidates=candidates)
        if match is None:
            missing.append(anchor.text)
            continue
        start, end = match
        used.update(range(start, end))
        positions.append(start)
        recovered.append(anchor)

    if len(positions) < 2:
        ordered_count = len(positions)
    else:
        # Longest increasing subsequence over recovered positions identifies
        # how many matched anchors retain their intended relative order.
        tails: list[int] = []
        for position in positions:
            index = bisect_left(tails, position)
            if index == len(tails):
                tails.append(position)
            else:
                tails[index] = position
        ordered_count = len(tails)
    affected: list[str] = []
    if ordered_count < len(positions):
        for index, current_position in enumerate(positions):
            for previous_index in range(index):
                if positions[previous_index] <= current_position:
                    continue
                # A compact explanation is enough for the UI; detailed
                # positions remain available through anchor identities in
                # diagnostics.
                affected.append(f"{recovered[previous_index].text} ↔ {recovered[index].text}")
                if len(affected) >= 20:
                    break
            if len(affected) >= 20:
                break
    return recovered, missing, affected[:20], [f"{ordered_count}/{len(positions)} matched anchors remain ordered"]


def _anchor_sequence(anchors: Sequence[_RenderAnchor], recovered_text: str) -> list[str]:
    """Return renderer anchors in the order a local parser emits them."""

    tokens = _tokens(recovered_text)
    line_spans = _line_token_spans(recovered_text)
    used: set[int] = set()
    found: list[tuple[int, str]] = []
    for anchor in anchors:
        pattern = _tokens(anchor.text)
        candidates: list[int] | None = None
        if anchor.kind == "heading":
            candidates = [
                start
                for line, start, end in line_spans
                if _tokens(line) == pattern and end - start == len(pattern)
            ]
        match = _find_token_occurrence(tokens, pattern, used, candidates=candidates)
        if match is None:
            continue
        start, end = match
        used.update(range(start, end))
        found.append((start, anchor.identity))
    return [identity for _, identity in sorted(found)]


def _date_association_matches(
    expectations: _RenderExpectations,
    recovered_text: str,
) -> tuple[list[_DateAssociation], list[str]]:
    """Match each rendered entry date to a nearby, unique entry-label occurrence.

    Tokens cross line and page boundaries, so wrapping does not split a date
    match. Repeated labels and dates consume separate occurrences. A generous
    local token window tolerates date/title wrapping while avoiding dates that
    appear after an entry's body text.
    """

    if not expectations.date_associations:
        return [], []
    tokens = _tokens(recovered_text)
    label_spans: dict[str, tuple[int, int]] = {}
    used_label_tokens: set[int] = set()
    for anchor in expectations.entries:
        match = _find_token_occurrence(tokens, _tokens(anchor.text), used_label_tokens)
        if match is not None:
            label_spans[anchor.identity] = match
            used_label_tokens.update(range(*match))

    body_spans: dict[str, tuple[int, int]] = {}
    used_body_tokens: set[int] = set()
    for association in expectations.date_associations:
        body_pattern = _tokens(association.body_anchor)[:5]
        if not body_pattern:
            continue
        match = _find_token_occurrence(tokens, body_pattern, used_body_tokens)
        if match is not None:
            body_spans[association.identity] = match
            used_body_tokens.update(range(*match))

    # Collect each text occurrence once, then assign it to the closest dated
    # entry whose expected date has those tokens. This prevents one repeated
    # date from satisfying several entries.
    patterns: dict[tuple[str, ...], list[_DateAssociation]] = {}
    for association in expectations.date_associations:
        pattern = tuple(_tokens(association.date_text))
        if pattern:
            patterns.setdefault(pattern, []).append(association)
    occurrences: dict[tuple[str, ...], list[tuple[int, int]]] = {pattern: [] for pattern in patterns}
    pattern_widths = {len(pattern) for pattern in patterns}
    for start in range(len(tokens)):
        for width in pattern_widths:
            end = start + width
            pattern = tuple(tokens[start:end])
            if len(pattern) == width and pattern in occurrences:
                occurrences[pattern].append((start, end))

    candidates: list[tuple[int, int, int, int, int, _DateAssociation]] = []
    association_order = {item.identity: index for index, item in enumerate(expectations.date_associations)}
    for pattern, pattern_occurrences in occurrences.items():
        for start, end in pattern_occurrences:
            for association in patterns[pattern]:
                label_span = label_spans.get(association.identity)
                if label_span is None:
                    continue
                label_start, label_end = label_span
                distance = max(label_start - end, start - label_end, 0)
                if distance > MAX_DATE_ASSOCIATION_TOKEN_DISTANCE:
                    continue
                closer_to_other_entry = any(
                    identity != association.identity
                    and max(span[0] - end, start - span[1], 0) < distance
                    for identity, span in label_spans.items()
                )
                if closer_to_other_entry:
                    continue
                between_label_and_date = [
                    span
                    for identity, span in label_spans.items()
                    if identity != association.identity
                    and min(label_start, start) <= span[0]
                    and span[1] <= max(label_end, end)
                ]
                if between_label_and_date:
                    continue
                body_span = body_spans.get(association.identity)
                if body_span is not None:
                    body_start, _body_end = body_span
                    if start >= label_end and body_start < start:
                        # A date after the entry's first rendered body field
                        # has been detached by extraction order.
                        continue
                if end <= label_start:
                    previous_label = max(
                        (
                            (span[1], identity)
                            for identity, span in label_spans.items()
                            if identity != association.identity and span[1] <= label_start
                        ),
                        default=None,
                    )
                    if previous_label is not None:
                        previous_body = body_spans.get(previous_label[1])
                        if previous_body is not None and previous_body[0] > start:
                            # A date before this title but still inside the
                            # preceding entry's header is not attributable to
                            # this entry.
                            continue
                if distance <= MAX_DATE_ASSOCIATION_TOKEN_DISTANCE:
                    candidates.append(
                        (
                            distance,
                            -len(pattern),
                            association_order[association.identity],
                            start,
                            end,
                            association,
                        )
                    )
    matched: dict[str, _DateAssociation] = {}
    consumed_occurrences: set[tuple[int, int]] = set()
    for _distance, _pattern_length, _order, start, end, association in sorted(candidates):
        occurrence = (start, end)
        if occurrence in consumed_occurrences or association.identity in matched:
            continue
        consumed_occurrences.add(occurrence)
        matched[association.identity] = association

    recovered = [item for item in expectations.date_associations if item.identity in matched]
    missing = [
        f"{item.section_type}: {item.label} — {item.date_text}"
        for item in expectations.date_associations
        if item.identity not in matched
    ]
    return recovered, missing


def _normalized_visible_web_url(link: _RenderLink) -> str:
    """Return the canonical visible address when the label exposes its href."""

    target = normalize_url(link.target, allowed_schemes={"http", "https"})
    display = normalize_url(link.visible_text, allowed_schemes={"http", "https"})
    target_parts = _web_url_identity(target)
    display_parts = _web_url_identity(display)
    return display if target_parts and display_parts == target_parts else ""


def _web_url_identity(value: str) -> tuple[str, str, str, str] | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return None
    if hostname.casefold().startswith("www."):
        hostname = hostname[4:]
    authority = hostname.casefold()
    if port is not None:
        authority = f"{authority}:{port}"
    return authority, parsed.path or "/", parsed.query, parsed.fragment


def _normalize_annotation_url(value: object) -> str:
    """Canonicalize only equivalent empty/root paths for extracted hrefs."""

    normalized = normalize_url(value)
    if not normalized:
        return ""
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        return normalized
    if parsed.scheme in {"http", "https"} and not parsed.path:
        return parsed._replace(path="/").geturl()
    return normalized


def _visible_web_url_recovered(link: _RenderLink, recovered_text: str) -> bool:
    expected = _normalized_visible_web_url(link)
    if not expected:
        return False
    # Remember real text boundaries while joining wrapped URL fragments. A
    # plain substring search would accept example.com/foo inside either
    # notexample.com/foo or example.com/foobar. Checking boundaries only after
    # stripping whitespace would instead reject URLs following a title/date.
    chunks = re.findall(r"\S+", recovered_text)
    boundaries = {0}
    offset = 0
    for chunk in chunks:
        offset += len(chunk)
        boundaries.add(offset)
    compact_text = "".join(chunks)
    try:
        parsed = urlsplit(expected)
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return False
    if hostname.casefold().startswith("www."):
        hostname = hostname[4:]
    authority_pattern = rf"(?i:(?:https?://)?(?:www\.)?{re.escape(hostname)})"
    if port is not None:
        authority_pattern += rf":{port}"
    path_pattern = re.escape(parsed.path)
    if parsed.path == "/" and not parsed.query and not parsed.fragment:
        path_pattern = r"/?"
    url_pattern = re.compile(
        rf"{authority_pattern}{path_pattern}"
        rf"{re.escape('?' + parsed.query) if parsed.query else ''}"
        rf"{re.escape('#' + parsed.fragment) if parsed.fragment else ''}"
    )
    # The host comparison is case-insensitive and optional www/scheme are
    # accepted. Escaped path/query/fragment text stays case-sensitive.
    for match in url_pattern.finditer(compact_text):
        start, end = match.span()
        starts_at_boundary = start in boundaries or compact_text[start - 1] in '<("\'|'
        ends_at_boundary = end in boundaries or compact_text[end] in '>)"\'|'
        if starts_at_boundary and ends_at_boundary:
            return True
    return False


def _web_links(expectations: _RenderExpectations) -> list[_RenderLink]:
    return [
        link
        for link in expectations.links
        if normalize_url(link.target, allowed_schemes={"http", "https"})
    ]


def _check(
    *,
    code: str,
    status: PDFRecoveryStatus,
    expected_count: int | None = None,
    recovered_count: int | None = None,
    evidence: Sequence[str] = (),
    expected_items: Sequence[str] = (),
    recovered_items: Sequence[str] = (),
    missing_items: Sequence[str] = (),
    affected_items: Sequence[str] = (),
    explanation: str,
) -> PDFCheck:
    return PDFCheck(
        code=code,
        status=status,
        expected_count=expected_count,
        recovered_count=recovered_count,
        evidence=list(evidence)[:100],
        expected_items=list(expected_items)[:100],
        recovered_items=list(recovered_items)[:100],
        missing_items=list(missing_items)[:100],
        affected_items=list(affected_items)[:100],
        explanation=explanation,
    )


def _overall_status(checks: Sequence[PDFCheck]) -> PDFRecoveryStatus:
    statuses = [check.status for check in checks if check.status is not PDFRecoveryStatus.UNAVAILABLE]
    if not statuses:
        return PDFRecoveryStatus.UNAVAILABLE
    if any(check.status is PDFRecoveryStatus.FAIL and check.code in _CRITICAL_CHECKS for check in checks):
        return PDFRecoveryStatus.FAIL
    if any(check.status in {PDFRecoveryStatus.FAIL, PDFRecoveryStatus.WARNING} for check in checks):
        return PDFRecoveryStatus.WARNING
    return PDFRecoveryStatus.PASS


def analyze_pdf_recovery(
    pdf_bytes: bytes | None,
    cv: object,
    *,
    render_manifest: object | None = None,
) -> PDFTextRecoveryAnalysis:
    """Compare CV source text and important fields with Aergia PDF extraction."""

    if not pdf_bytes:
        return PDFTextRecoveryAnalysis(
            status=PDFRecoveryStatus.UNAVAILABLE,
            checks=[
                PDFCheck(
                    code="pdf_not_supplied",
                    status=PDFRecoveryStatus.UNAVAILABLE,
                    explanation="No rendered or uploaded PDF was supplied for text-recovery analysis.",
                )
            ],
        )
    if len(pdf_bytes) > MAX_PDF_INPUT_BYTES:
        return PDFTextRecoveryAnalysis(
            status=PDFRecoveryStatus.WARNING,
            checks=[
                PDFCheck(
                    code="input_size_limit",
                    status=PDFRecoveryStatus.WARNING,
                    expected_count=MAX_PDF_INPUT_BYTES,
                    recovered_count=len(pdf_bytes),
                    explanation="PDF text recovery was skipped because the input exceeds the configured size limit.",
                )
            ],
        )

    extracted = _run_bounded_pdf_worker(pdf_bytes)
    error = extracted.get("error")
    if isinstance(error, str):
        return _worker_failure(error)
    page_count = extracted["page_count"]
    if extracted.get("page_limit_exceeded") is True:
        return PDFTextRecoveryAnalysis(
            status=PDFRecoveryStatus.WARNING,
            page_count=page_count,
            checks=[
                PDFCheck(
                    code="page_limit",
                    status=PDFRecoveryStatus.WARNING,
                    expected_count=MAX_PDF_PAGES,
                    recovered_count=page_count,
                    explanation="PDF text recovery was skipped because the document exceeds the configured page limit.",
                )
            ],
        )
    recovered_text = str(extracted["plain_text"])
    recovered_links = [str(link) for link in extracted["links"]]
    secondary_text = extracted.get("secondary_plain_text")
    text_truncated = extracted.get("text_truncated") is True
    expectations = _expectations_for(cv, render_manifest)
    expected_tokens = _tokens("\n".join(expectations.visible_text))
    recovered_tokens = _tokens(recovered_text)
    expected_counts = Counter(expected_tokens)
    recovered_counts = Counter(recovered_tokens)
    retained = sum(min(count, recovered_counts[token]) for token, count in expected_counts.items())
    retention = retained / len(expected_tokens) if expected_tokens else 0.0
    text_status = _check_status(retention, "text_retention") if expected_tokens else PDFRecoveryStatus.UNAVAILABLE
    recovered_anchors, missing_anchors, affected_anchors, order_evidence = _anchor_matches(
        expectations.ordered_anchors,
        recovered_text,
    )
    matched_anchor_count = len(recovered_anchors)
    ordered_anchor_count = int(order_evidence[0].split("/", 1)[0]) if order_evidence else 0
    order_ratio = (
        ordered_anchor_count / matched_anchor_count
        if matched_anchor_count
        else 0.0
    )
    order_status = (
        _check_status(order_ratio, "reading_order")
        if expectations.ordered_anchors
        else PDFRecoveryStatus.UNAVAILABLE
    )
    checks: list[PDFCheck] = [
        _check(
            code="text_retention",
            status=text_status,
            expected_count=len(expected_tokens) if expected_tokens else None,
            recovered_count=retained if expected_tokens else None,
            evidence=[f"{retention:.1%} of rendered words recovered"] if expected_tokens else (),
            expected_items=expectations.visible_text,
            explanation="Compares visible text intended by the renderer with text recovered by Aergia's PDF parser.",
        ),
        _check(
            code="reading_order",
            status=order_status,
            # Missing anchors are a text-recovery issue.  The numeric order
            # check is scored only over anchors that were actually found.
            expected_count=matched_anchor_count if matched_anchor_count else None,
            recovered_count=ordered_anchor_count if matched_anchor_count else None,
            evidence=order_evidence,
            expected_items=[anchor.text for anchor in expectations.ordered_anchors],
            recovered_items=[anchor.text for anchor in recovered_anchors],
            missing_items=missing_anchors,
            affected_items=affected_anchors,
            explanation="Compares the relative order of rendered section and entry anchors; missing text is reported by text retention.",
        ),
    ]
    if text_truncated:
        checks.append(
            _check(
                code="text_limit",
                status=PDFRecoveryStatus.WARNING,
                expected_count=MAX_EXTRACTED_TEXT_CHARS,
                recovered_count=len(recovered_text),
                explanation="PDF text recovery reached the configured character limit; later document text was not analyzed.",
            )
        )

    recovered_text_normalized = _normalize(recovered_text)
    recovered_contacts = [
        contact
        for contact in expectations.contacts
        if contact.casefold() in {"email", "phone", "telephone"}
        and any(
            field.field_key.casefold() == contact.casefold()
            and _normalize(field.text) in recovered_text_normalized
            for field in flatten_cv_text(cv)
        )
    ]
    missing_contacts = [contact for contact in expectations.contacts if contact not in recovered_contacts]
    contact_status = (
        PDFRecoveryStatus.UNAVAILABLE
        if not expectations.contacts
        else _check_status(
            len(recovered_contacts) / len(expectations.contacts),
            "contact_recovery",
        )
    )
    checks.append(
        _check(
            code="contact_recovery",
            status=contact_status,
            expected_count=len(expectations.contacts) if expectations.contacts else None,
            recovered_count=len(recovered_contacts) if expectations.contacts else None,
            evidence=recovered_contacts,
            expected_items=expectations.contacts,
            recovered_items=recovered_contacts,
            missing_items=missing_contacts,
            explanation="Checks whether visible source contact fields are present in recovered PDF text.",
        )
    )

    recovered_heading_anchors, missing_headings, _heading_affected, _ = _anchor_matches(
        expectations.headings,
        recovered_text,
    )
    checks.append(
        _check(
            code="section_heading_recovery",
            status=(
                _check_status(len(recovered_heading_anchors) / len(expectations.headings), "section_heading_recovery")
                if expectations.headings
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(expectations.headings) if expectations.headings else None,
            recovered_count=len(recovered_heading_anchors) if expectations.headings else None,
            evidence=[anchor.text for anchor in recovered_heading_anchors],
            expected_items=[anchor.text for anchor in expectations.headings],
            recovered_items=[anchor.text for anchor in recovered_heading_anchors],
            missing_items=missing_headings,
            explanation="Checks effective visible section titles against extracted lines, with occurrence-aware matching.",
        )
    )

    recovered_entry_anchors, missing_entries, _entry_affected, _ = _anchor_matches(
        expectations.entries,
        recovered_text,
    )
    checks.append(
        _check(
            code="entry_recovery",
            status=(
                _check_status(len(recovered_entry_anchors) / len(expectations.entries), "entry_recovery")
                if expectations.entries
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(expectations.entries) if expectations.entries else None,
            recovered_count=len(recovered_entry_anchors) if expectations.entries else None,
            evidence=[f"{anchor.section_type}: {anchor.text[:160]}" for anchor in recovered_entry_anchors],
            expected_items=[anchor.text for anchor in expectations.entries],
            recovered_items=[anchor.text for anchor in recovered_entry_anchors],
            missing_items=missing_entries,
            explanation="Checks renderer-defined experience, project, research, education, and certification anchors.",
        )
    )

    dated_entries = expectations.date_associations
    recovered_dated_entries, missing_dated_entries = _date_association_matches(
        expectations,
        recovered_text,
    )
    secondary_dated_entries, secondary_missing_dates = (
        _date_association_matches(expectations, secondary_text)
        if isinstance(secondary_text, str)
        else ([], [])
    )
    primary_date_ids = {item.identity for item in recovered_dated_entries}
    secondary_date_ids = {item.identity for item in secondary_dated_entries}
    if isinstance(secondary_text, str):
        date_match_ids = primary_date_ids & secondary_date_ids
        missing_date_items = [
            *(
                f"pdfplumber: {item}"
                for item in missing_dated_entries
            ),
            *(
                f"PDFium: {item}"
                for item in secondary_missing_dates
            ),
        ]
        date_evidence = [
            f"{len(primary_date_ids)}/{len(dated_entries)} associated in pdfplumber; "
            f"{len(secondary_date_ids)}/{len(dated_entries)} in PDFium"
        ]
    else:
        date_match_ids = primary_date_ids
        missing_date_items = missing_dated_entries
        date_evidence = [f"{len(primary_date_ids)}/{len(dated_entries)} associated in pdfplumber"]
    jointly_recovered_dates = [
        item for item in dated_entries if item.identity in date_match_ids
    ]
    date_items = [
        f"{item.section_type}: {item.label} — {item.date_text}"
        for item in dated_entries
    ]
    date_recovery_status = (
        _check_status(len(jointly_recovered_dates) / len(dated_entries), "entry_date_association")
        if dated_entries
        else PDFRecoveryStatus.UNAVAILABLE
    )
    checks.append(
        _check(
            code="entry_date_association",
            status=date_recovery_status,
            expected_count=len(dated_entries) if dated_entries else None,
            recovered_count=len(jointly_recovered_dates) if dated_entries else None,
            evidence=date_evidence if dated_entries else (),
            expected_items=date_items,
            recovered_items=[
                f"{item.section_type}: {item.label} — {item.date_text}"
                for item in jointly_recovered_dates
            ],
            missing_items=missing_date_items,
            explanation=(
                "Checks whether each rendered entry date stays near its own title and before the entry body. "
                "Repeated labels and dates are matched as separate occurrences; this is a local extraction check."
            ),
        )
    )

    normalized_recovered_urls = [_normalize_annotation_url(link) for link in recovered_links]
    retained_links: list[_RenderLink] = []
    missing_links: list[str] = []
    used_link_indexes: set[int] = set()
    for expected_link in expectations.links:
        match_index = next(
            (
                index
                for index, recovered_url in enumerate(normalized_recovered_urls)
                if index not in used_link_indexes
                and recovered_url == _normalize_annotation_url(expected_link.target)
            ),
            None,
        )
        if match_index is None:
            missing_links.append(expected_link.identity)
        else:
            used_link_indexes.add(match_index)
            retained_links.append(expected_link)
    checks.append(
        _check(
            code="link_recovery",
            status=(
                _check_status(len(retained_links) / len(expectations.links), "link_recovery")
                if expectations.links
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(expectations.links) if expectations.links else None,
            recovered_count=len(retained_links) if expectations.links else None,
            evidence=[link.identity for link in retained_links],
            expected_items=[link.identity for link in expectations.links],
            recovered_items=[link.identity for link in retained_links],
            missing_items=missing_links,
            explanation="Checks clickable links emitted by the renderer using canonical href values; visible URL text is checked separately.",
        )
    )

    web_links = _web_links(expectations)
    visible_url_links = [link for link in web_links if _normalized_visible_web_url(link)]
    recovered_visible_urls = [
        link for link in visible_url_links if _visible_web_url_recovered(link, recovered_text)
    ]
    checks.append(
        _check(
            code="visible_url_recovery",
            status=(
                _check_status(len(recovered_visible_urls) / len(visible_url_links), "visible_url_recovery")
                if visible_url_links
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(visible_url_links) if visible_url_links else None,
            recovered_count=len(recovered_visible_urls) if visible_url_links else None,
            expected_items=[link.identity for link in visible_url_links],
            recovered_items=[link.identity for link in recovered_visible_urls],
            missing_items=[
                link.identity for link in visible_url_links if link not in recovered_visible_urls
            ],
            explanation=(
                "Checks whether URL-shaped visible link text, including compact addresses without a scheme, "
                "survives PDF text extraction independently of its clickable annotation."
            ),
        )
    )
    hidden_web_links = [link for link in web_links if not _normalized_visible_web_url(link)]
    checks.append(
        _check(
            code="link_label_visibility",
            # This advisory concerns visible text only; clickable annotation
            # recovery is reported independently above.
            status=(
                PDFRecoveryStatus.WARNING
                if hidden_web_links
                else PDFRecoveryStatus.PASS
                if web_links
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(web_links) if web_links else None,
            recovered_count=len(visible_url_links) if web_links else None,
            expected_items=[link.identity for link in web_links],
            recovered_items=[link.identity for link in visible_url_links],
            missing_items=[link.identity for link in hidden_web_links],
            explanation=(
                "Advises when a web link is displayed as a generic label such as GitHub instead of its address. "
                "This is a readability advisory, not a claim about any particular ATS."
            ),
        )
    )

    if isinstance(secondary_text, str):
        primary_sequence = _anchor_sequence(expectations.ordered_anchors, recovered_text)
        secondary_sequence = _anchor_sequence(expectations.ordered_anchors, secondary_text)
        primary_url_results = [_visible_web_url_recovered(link, recovered_text) for link in web_links]
        secondary_url_results = [_visible_web_url_recovered(link, secondary_text) for link in web_links]
        anchor_agreement = primary_sequence == secondary_sequence
        agreed_anchor_count = len(expectations.ordered_anchors) if anchor_agreement else 0
        agreed_url_count = sum(
            primary == secondary
            for primary, secondary in zip(primary_url_results, secondary_url_results, strict=True)
        )
        date_agreement_ids = {
            item.identity
            for item in dated_entries
            if (item.identity in primary_date_ids) == (item.identity in secondary_date_ids)
        }
        agreed_date_count = len(date_agreement_ids)
        comparison_count = len(expectations.ordered_anchors) + len(web_links) + len(dated_entries)
        agreed_count = agreed_anchor_count + agreed_url_count + agreed_date_count
        differing_dates = [
            f"{item.section_type}: {item.label} — {item.date_text}"
            for item in dated_entries
            if (item.identity in primary_date_ids) != (item.identity in secondary_date_ids)
        ]
        parser_agreement_status = (
            PDFRecoveryStatus.UNAVAILABLE
            if comparison_count == 0
            else PDFRecoveryStatus.PASS
            if agreed_count == comparison_count
            else PDFRecoveryStatus.WARNING
        )
        checks.append(
            _check(
                code="parser_agreement",
                status=parser_agreement_status,
                expected_count=comparison_count if comparison_count else None,
                recovered_count=agreed_count if comparison_count else None,
                evidence=[
                    f"pdfplumber: {len(primary_sequence)} anchors, "
                    f"{sum(primary_url_results)}/{len(web_links)} visible URLs; "
                    f"PDFium: {len(secondary_sequence)} anchors, "
                    f"{sum(secondary_url_results)}/{len(web_links)} visible URLs"
                ],
                expected_items=primary_sequence,
                recovered_items=secondary_sequence,
                affected_items=(
                    (["Entry or heading order differs between local parsers"] if not anchor_agreement else [])
                    + differing_dates
                    + [
                        link.identity
                        for link, primary, secondary in zip(
                            web_links,
                            primary_url_results,
                            secondary_url_results,
                            strict=True,
                        )
                        if primary != secondary
                    ]
                ),
                explanation=(
                    "Compares renderer-anchor order and visible URL recovery between Aergia's pdfplumber and "
                    "PDFium extractors. Disagreement is advisory and does not predict third-party ATS behavior."
                ),
            )
        )

    overall = _overall_status(checks)
    return PDFTextRecoveryAnalysis(status=overall, page_count=page_count, checks=checks)


__all__ = [
    "MAX_EXTRACTED_TEXT_CHARS",
    "MAX_PDF_INPUT_BYTES",
    "MAX_PDF_LINKS",
    "MAX_PDF_PAGES",
    "PDF_ANALYSIS_VERSION",
    "analyze_pdf_recovery",
]
