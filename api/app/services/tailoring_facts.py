"""Conservative fact checks for prose changed by a tailoring patch.

Local agent validation improves the repair loop, but this module is the final
server-side guard. It only trusts the current CV and evidence references
declared by the patch; the complete Library is never treated as an unrestricted
source of claims.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from app.models.library import LibraryEntry
from app.services.tailoring_policy import TailoringPolicyError, entry_by_id, section_by_id


NUMBER_PATTERN = re.compile(r"(?:[$€£]\s*)?\b\d[\d,.]*(?:\s*%|\s*[kKmMbB])?(?=$|[^\w])")
URL_PATTERN = re.compile(r"https?://[^\s)\]}>,]+", re.IGNORECASE)
TECHNOLOGIES = (
    "aws",
    "azure",
    "docker",
    "fastapi",
    "graphql",
    "java",
    "javascript",
    "kafka",
    "kubernetes",
    "linux",
    "node.js",
    "postgresql",
    "python",
    "react",
    "redis",
    "rust",
    "sql",
    "terraform",
    "typescript",
)
EMPLOYER_CLAIM_PATTERN = re.compile(
    r"\b(?:at|for|with)\s+([A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,4})"
)
TITLE_CLAIM_PATTERN = re.compile(
    r"\b(?:as|role(?:d)?\s+as)\s+(?:an?\s+|the\s+)?([A-Z][\w/&-]*(?:\s+[A-Z][\w/&-]*){0,4})"
)


class TailoringFactError(ValueError):
    """A changed prose claim cannot be supported by the declared evidence."""


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if isinstance(value, Mapping):
        return " ".join(
            flatten_text(child)
            for key, child in value.items()
            if key not in {"id", "style", "link", "url"}
        )
    return ""


def normalize_number(value: str) -> str:
    return value.replace("$", "").replace("€", "").replace("£", "").replace(" ", "").replace(",", "").lower()


def number_claims(value: str) -> set[str]:
    return {normalize_number(match.group(0)) for match in NUMBER_PATTERN.finditer(value)}


def technology_claims(value: str) -> set[str]:
    normalized = value.casefold()
    return {
        technology
        for technology in TECHNOLOGIES
        if re.search(rf"(?<![a-z0-9+#]){re.escape(technology)}(?![a-z0-9+#])", normalized)
    }


def _read_field(source: Mapping[str, Any], field_path: str) -> Any:
    value: Any = source
    for component in field_path.split("."):
        if not isinstance(value, Mapping) or component not in value:
            return None
        value = value[component]
    return value


def _library_source_text(reference: Any, library_entries: Mapping[str, LibraryEntry]) -> str:
    entry = library_entries.get(reference.library_entry_id or "")
    if entry is None:
        return ""
    row = next(
        (
            candidate
            for candidate in (entry.payload or [])
            if isinstance(candidate, Mapping) and candidate.get("id") == reference.source_row_id
        ),
        None,
    )
    if row is None:
        return ""
    value = _read_field(row, reference.field_path)
    return flatten_text(value)


def _cv_source_text(reference: Any, sections: list[dict[str, Any]]) -> str:
    try:
        section = section_by_id(sections, reference.section_id or "")
        entry = entry_by_id(section, reference.entry_id)
    except TailoringPolicyError:
        return ""
    return flatten_text(_read_field(entry, reference.field_path))


def _declared_evidence_text(
    change: Any,
    source_sections: list[dict[str, Any]],
    library_entries: Mapping[str, LibraryEntry],
) -> str:
    # The original target text is implicit evidence for a rewrite. Do not use
    # the whole CV or the whole Library here: a metric or technology belonging
    # to one job must not authorize a new claim in another job.
    values: list[str] = []
    try:
        values.append(flatten_text(_target_value(source_sections, change)))
    except TailoringFactError:
        pass
    for reference in getattr(change, "evidence", None) or []:
        if reference.source == "cv":
            values.append(_cv_source_text(reference, source_sections))
        else:
            values.append(_library_source_text(reference, library_entries))
    return " ".join(values)


def _target_value(sections: list[dict[str, Any]], change: Any) -> Any:
    try:
        section = section_by_id(sections, change.section_id)
        entry = entry_by_id(section, getattr(change, "entry_id", None))
    except TailoringPolicyError as exc:
        raise TailoringFactError(str(exc)) from exc
    return entry.get(getattr(change, "field", None) or "description")


def _candidate_value(change: Any) -> Any:
    if change.operation in {"replace_description", "replace_rich_text"}:
        return change.value
    if change.operation == "rewrite_rich_text":
        return [block.model_dump(mode="json", exclude_none=True) for block in change.value]
    return None


def _new_claims(before: str, after: str, allowed: str) -> tuple[set[str], set[str], set[str]]:
    before_numbers = number_claims(before)
    allowed_numbers = number_claims(allowed)
    before_technologies = technology_claims(before)
    allowed_technologies = technology_claims(allowed)
    before_urls = {url.casefold() for url in URL_PATTERN.findall(before)}
    allowed_urls = {url.casefold() for url in URL_PATTERN.findall(allowed)}
    return (
        number_claims(after) - before_numbers - allowed_numbers,
        technology_claims(after) - before_technologies - allowed_technologies,
        {url.casefold() for url in URL_PATTERN.findall(after)} - before_urls - allowed_urls,
    )


def _unsupported_named_claims(before: str, after: str, allowed: str) -> list[str]:
    allowed_folded = allowed.casefold()
    claims: list[str] = []
    for pattern, label in (
        (EMPLOYER_CLAIM_PATTERN, "employer"),
        (TITLE_CLAIM_PATTERN, "title"),
    ):
        for match in pattern.finditer(after):
            claim = " ".join(match.group(1).split()).strip(".,;:")
            if not claim:
                continue
            if claim.casefold() in before.casefold() or claim.casefold() in allowed_folded:
                continue
            claims.append(f"{label}: {claim}")
    return claims


def validate_tailoring_facts(
    source_sections: list[dict[str, Any]],
    updated_sections: list[dict[str, Any]],
    changes: Iterable[Any],
    library_entries: Iterable[LibraryEntry],
) -> None:
    """Reject unsupported claims introduced by editable prose operations."""

    library_by_id = {entry.id: entry for entry in library_entries}
    for change in changes:
        candidate = _candidate_value(change)
        if candidate is None:
            continue
        before = flatten_text(_target_value(source_sections, change))
        after = flatten_text(candidate)
        allowed = _declared_evidence_text(change, source_sections, library_by_id)
        new_numbers, new_technologies, new_urls = _new_claims(before, after, allowed)
        named_claims = _unsupported_named_claims(before, after, allowed)
        if new_numbers:
            raise TailoringFactError(f"Unsupported numeric claim(s): {', '.join(sorted(new_numbers))}")
        if new_technologies:
            raise TailoringFactError(f"Unsupported technology claim(s): {', '.join(sorted(new_technologies))}")
        if new_urls:
            raise TailoringFactError("Unsupported URL claim in rewritten prose")
        if named_claims:
            raise TailoringFactError(f"Unsupported named claim(s): {', '.join(named_claims)}")


__all__ = [
    "TailoringFactError",
    "flatten_text",
    "normalize_number",
    "number_claims",
    "technology_claims",
    "validate_tailoring_facts",
]
