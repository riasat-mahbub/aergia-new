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
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from app.scanner.matching import CVTextField, flatten_cv_text
from app.scanner.results import (
    PDFCheck,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
)


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
_TOKEN_RE = re.compile(r"[a-z0-9+#./-]+", re.I)
_DASHES = str.maketrans({char: "-" for char in "‐‑‒–—―−﹘﹣－"})
_URL_KEYS = frozenset({"url", "link", "site_url", "paper_url", "credential_url"})


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
    """Count how much expected text survives as an ordered subsequence."""

    cursor = 0
    count = 0
    for token in expected:
        while cursor < len(recovered) and recovered[cursor] != token:
            cursor += 1
        if cursor == len(recovered):
            break
        count += 1
        cursor += 1
    return count


def _urls(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            if (str(key) in _URL_KEYS or str(key).endswith("_url")) and isinstance(item, str) and item.strip():
                found.append(item.strip())
            found.extend(_urls(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            found.extend(_urls(item))
    return found


def _entry_titles(cv: object, allowed_types: set[str]) -> list[tuple[str, str]]:
    fields = flatten_cv_text(cv)
    grouped: dict[tuple[str, str], list[CVTextField]] = {}
    for field in fields:
        if field.section_type not in allowed_types or not field.entry_id:
            continue
        grouped.setdefault((field.section_type, field.entry_id), []).append(field)
    titles: list[tuple[str, str]] = []
    for (section_type, _entry_id), entry_fields in grouped.items():
        title = next(
            (
                field.text.strip()
                for field in entry_fields
                if field.field_key.casefold()
                in {"position", "title", "degree", "program", "organization", "company"}
                and field.text.strip()
            ),
            "",
        )
        if title:
            titles.append((section_type, title))
    return titles[:500]


def _check_status(ratio: float) -> PDFRecoveryStatus:
    if ratio >= 0.96:
        return PDFRecoveryStatus.PASS
    if ratio >= 0.80:
        return PDFRecoveryStatus.WARNING
    return PDFRecoveryStatus.FAIL


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


def analyze_pdf_recovery(pdf_bytes: bytes | None, cv: object) -> PDFTextRecoveryAnalysis:
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
    recovered_text = extracted["plain_text"]
    recovered_links = extracted["links"]
    text_truncated = extracted.get("text_truncated") is True
    fields = flatten_cv_text(cv)
    expected_tokens = _tokens("\n".join(field.text for field in fields))
    recovered_tokens = _tokens(recovered_text)
    expected_counts = Counter(expected_tokens)
    recovered_counts = Counter(recovered_tokens)
    retained = sum(min(count, recovered_counts[token]) for token, count in expected_counts.items())
    retention = retained / max(1, len(expected_tokens))
    ordered = _ordered_match_count(expected_tokens, recovered_tokens)
    order_ratio = ordered / max(1, len(expected_tokens))
    checks: list[PDFCheck] = [
        PDFCheck(
            code="text_retention",
            status=_check_status(retention),
            expected_count=len(expected_tokens),
            recovered_count=retained,
            evidence=[f"{retention:.1%} of source words recovered"],
            explanation="Compares visible CV text with text recovered by Aergia's PDF parser.",
        ),
        PDFCheck(
            code="reading_order",
            status=_check_status(order_ratio),
            expected_count=len(expected_tokens),
            recovered_count=ordered,
            evidence=[f"{order_ratio:.1%} of source words remain in order"],
            explanation="Checks whether the recovered word sequence follows the CV source order.",
        ),
    ]
    if text_truncated:
        checks.append(
            PDFCheck(
                code="text_limit",
                status=PDFRecoveryStatus.WARNING,
                expected_count=MAX_EXTRACTED_TEXT_CHARS,
                recovered_count=len(recovered_text),
                explanation="PDF text recovery reached the configured character limit; later document text was not analyzed.",
            )
        )

    contact_fields = [
        field
        for field in fields
        if field.section_type == "profile" and field.field_key.casefold() in {"email", "phone", "telephone"}
    ]
    contact_recovered = [field for field in contact_fields if _normalize(field.text) in _normalize(recovered_text)]
    checks.append(
        PDFCheck(
            code="contact_recovery",
            status=(
                PDFRecoveryStatus.PASS
                if len(contact_recovered) == len(contact_fields)
                else PDFRecoveryStatus.WARNING
                if contact_recovered or not contact_fields
                else PDFRecoveryStatus.FAIL
            ),
            expected_count=len(contact_fields),
            recovered_count=len(contact_recovered),
            evidence=[field.field_key for field in contact_fields],
            explanation="Checks whether source contact fields are present in recovered PDF text.",
        )
    )

    source = _dump(cv)
    sections = _value(source, "sections", [])
    expected_headings = [
        str(title).strip()
        for section in sections if isinstance(sections, Sequence) and not isinstance(sections, (str, bytes, bytearray))
        if _value(section, "enabled", True) is not False
        if (title := _value(section, "title")) and str(title).strip()
    ] if isinstance(sections, Sequence) and not isinstance(sections, (str, bytes, bytearray)) else []
    recovered_headings = [title for title in expected_headings if _normalize(title) in _normalize(recovered_text)]
    checks.append(
        PDFCheck(
            code="section_heading_recovery",
            status=(
                _check_status(len(recovered_headings) / len(expected_headings))
                if expected_headings
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(expected_headings),
            recovered_count=len(recovered_headings),
            evidence=recovered_headings[:100],
            explanation="Checks visible source section titles against recovered text.",
        )
    )

    entry_titles = _entry_titles(cv, {"experience", "work_experience", "projects", "project", "research", "education"})
    recovered_entries = [title for _section_type, title in entry_titles if _normalize(title) in _normalize(recovered_text)]
    checks.append(
        PDFCheck(
            code="entry_recovery",
            status=_check_status(len(recovered_entries) / len(entry_titles)) if entry_titles else PDFRecoveryStatus.UNAVAILABLE,
            expected_count=len(entry_titles),
            recovered_count=len(recovered_entries),
            evidence=[f"{section_type}: {title[:160]}" for section_type, title in entry_titles[:100] if title in recovered_entries],
            explanation="Checks whether experience, project, research, and education entry labels survive extraction.",
        )
    )

    expected_urls = list(dict.fromkeys(_urls(source)))
    recovered_urls = list(dict.fromkeys(str(link) for link in recovered_links))
    retained_urls = [url for url in expected_urls if any(_normalize(url) == _normalize(link) for link in recovered_urls)]
    checks.append(
        PDFCheck(
            code="link_recovery",
            status=(
                _check_status(len(retained_urls) / len(expected_urls))
                if expected_urls
                else PDFRecoveryStatus.UNAVAILABLE
            ),
            expected_count=len(expected_urls),
            recovered_count=len(retained_urls),
            evidence=["link targets recovered" for _ in retained_urls],
            explanation="Checks whether source URL targets are attached to extracted PDF text blocks.",
        )
    )

    statuses = [check.status for check in checks if check.status is not PDFRecoveryStatus.UNAVAILABLE]
    overall = (
        PDFRecoveryStatus.FAIL
        if PDFRecoveryStatus.FAIL in statuses
        else PDFRecoveryStatus.WARNING
        if PDFRecoveryStatus.WARNING in statuses
        else PDFRecoveryStatus.PASS
    )
    return PDFTextRecoveryAnalysis(status=overall, page_count=page_count, checks=checks)


__all__ = [
    "MAX_EXTRACTED_TEXT_CHARS",
    "MAX_PDF_INPUT_BYTES",
    "MAX_PDF_LINKS",
    "MAX_PDF_PAGES",
    "PDF_ANALYSIS_VERSION",
    "analyze_pdf_recovery",
]
