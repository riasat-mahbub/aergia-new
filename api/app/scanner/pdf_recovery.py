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

from app.core.safe_url import normalize_url
from app.scanner.matching import flatten_cv_text
from app.scanner.results import (
    PDFCheck,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
)
from app.services.renderer.pipeline import prepare_render_source, resolve_source


PDF_ANALYSIS_VERSION = "aergia-pdf-recovery-v2"
MAX_PDF_INPUT_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_EXTRACTED_TEXT_CHARS = 2_000_000
MAX_PDF_LINKS = 500
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

    @property
    def identity(self) -> str:
        """Human-readable link identity used by persisted recovery checks."""

        return self.label


@dataclass(frozen=True, slots=True)
class _RenderExpectations:
    visible_text: tuple[str, ...]
    headings: tuple[_RenderAnchor, ...]
    entries: tuple[_RenderAnchor, ...]
    ordered_anchors: tuple[_RenderAnchor, ...]
    contacts: tuple[str, ...]
    links: tuple[_RenderLink, ...]


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
                            label = text if text and not normalize_url(text) else ""
                            if not label:
                                label = (
                                    _entry_label(section.type, entry)
                                    or ("Portfolio" if section.type == "profile" and field.key == "site" else "Link")
                                )
                            prior = sum(item.label.split(" (", 1)[0] == label for item in links)
                            if prior:
                                label = f"{label} ({prior + 1})"
                            links.append(_RenderLink(label, normalized))

    return _RenderExpectations(
        visible_text=tuple(visible_text),
        headings=tuple(headings),
        entries=tuple(entries),
        ordered_anchors=tuple(ordered_anchors),
        contacts=tuple(dict.fromkeys(contacts)),
        links=tuple(dict.fromkeys(links)),
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
        if (
            not isinstance(page_count, int)
            or isinstance(page_count, bool)
            or page_count < 0
            or not isinstance(plain_text, str)
            or len(plain_text) > MAX_EXTRACTED_TEXT_CHARS
            or not isinstance(links, list)
            or len(links) > MAX_PDF_LINKS
            or any(not isinstance(link, str) or len(link) > 2_000 for link in links)
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
        expected_items=list(dict.fromkeys(expected_items))[:100],
        recovered_items=list(dict.fromkeys(recovered_items))[:100],
        missing_items=list(dict.fromkeys(missing_items))[:100],
        affected_items=list(dict.fromkeys(affected_items))[:100],
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

    normalized_recovered_urls = [normalize_url(link) for link in recovered_links]
    retained_links: list[_RenderLink] = []
    missing_links: list[str] = []
    used_link_indexes: set[int] = set()
    for expected_link in expectations.links:
        match_index = next(
            (
                index
                for index, recovered_url in enumerate(normalized_recovered_urls)
                if index not in used_link_indexes and recovered_url == expected_link.target
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
            explanation="Checks clickable links emitted by the renderer using canonical href values; visible link text is covered by text recovery.",
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
