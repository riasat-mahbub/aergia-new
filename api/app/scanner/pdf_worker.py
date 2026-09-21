"""Resource-bounded worker for scanner-only PDF text recovery.

This module is launched in a short-lived subprocess. It emits a small JSON
summary and never logs document content or parser exceptions.
"""

from __future__ import annotations

import json
import sys

try:
    import resource
except ImportError:  # pragma: no cover - the worker still has a wall-time cap
    resource = None  # type: ignore[assignment]

from app.scanner.pdf_recovery import (
    MAX_EXTRACTED_TEXT_CHARS,
    MAX_PDF_INPUT_BYTES,
    MAX_PDF_PAGES,
    MAX_PDF_LINKS,
    PDF_WORKER_MEMORY_LIMIT_BYTES,
)
from app.services.parser._extract_pdfplumber import extract_with_pdfplumber

MAX_WORKER_INPUT_BYTES = MAX_PDF_INPUT_BYTES + 1
MAX_WORKER_LINK_CHARS = 2_000


def _set_limit(resource_id: int, soft_limit: int, hard_limit: int) -> None:
    current_soft, current_hard = resource.getrlimit(resource_id)
    ceiling = hard_limit if current_hard == resource.RLIM_INFINITY else min(hard_limit, current_hard)
    requested_soft = min(soft_limit, ceiling)
    if current_soft != resource.RLIM_INFINITY:
        requested_soft = min(requested_soft, current_soft)
    resource.setrlimit(resource_id, (requested_soft, ceiling))


def _apply_resource_limits() -> None:
    """Bound CPU, virtual memory, open handles, and accidental file writes."""

    if not hasattr(resource, "RLIMIT_AS"):
        return
    _set_limit(resource.RLIMIT_CPU, 9, 10)
    _set_limit(
        resource.RLIMIT_AS,
        PDF_WORKER_MEMORY_LIMIT_BYTES,
        PDF_WORKER_MEMORY_LIMIT_BYTES,
    )
    _set_limit(resource.RLIMIT_NOFILE, 64, 64)
    _set_limit(resource.RLIMIT_FSIZE, 8 * 1024 * 1024, 8 * 1024 * 1024)


def _safe_text(text: str) -> str:
    return "".join(
        char if char in "\n\r\t" or ord(char) >= 32 else " "
        for char in text[:MAX_EXTRACTED_TEXT_CHARS]
    )


def _response(pdf_bytes: bytes) -> dict[str, object]:
    extracted = extract_with_pdfplumber(
        pdf_bytes,
        max_pages=MAX_PDF_PAGES,
        max_text_chars=MAX_EXTRACTED_TEXT_CHARS,
        max_total_links=MAX_PDF_LINKS,
    )
    links: list[str] = []
    seen: set[str] = set()
    for block in extracted.blocks:
        for link in block.links:
            if link in seen:
                continue
            seen.add(link)
            links.append(link[:MAX_WORKER_LINK_CHARS])
            if len(links) >= MAX_PDF_LINKS:
                break
        if len(links) >= MAX_PDF_LINKS:
            break
    return {
        "ok": True,
        "page_count": extracted.page_count,
        "page_limit_exceeded": extracted.page_limit_exceeded,
        "text_truncated": extracted.text_truncated,
        "plain_text": _safe_text(extracted.plain_text),
        "links": links,
    }


def main() -> int:
    _apply_resource_limits()
    pdf_bytes = sys.stdin.buffer.read(MAX_WORKER_INPUT_BYTES)
    if not pdf_bytes or len(pdf_bytes) > MAX_PDF_INPUT_BYTES:
        payload: dict[str, object] = {"ok": False, "error": "input_size_limit"}
    else:
        try:
            payload = _response(pdf_bytes)
        except Exception as exc:  # parser libraries expose varied format errors
            payload = {"ok": False, "error": type(exc).__name__}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
