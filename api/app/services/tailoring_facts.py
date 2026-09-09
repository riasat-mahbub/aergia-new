"""Conservative fact checks for prose changed by a tailoring patch.

Local agent validation improves the repair loop, but this module is the final
server-side guard. It trusts the write target's before-image plus explicit
current-CV/Library/web evidence references declared by the patch; the
complete Library is never treated as an implicit source of claims.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from app.models.library import LibraryEntry
from app.services.tailoring_policy import TailoringPolicyError, entry_by_id, protected_fields, section_by_id


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
    if field_path == "*":
        return source
    value: Any = source
    for component in field_path.split("."):
        if not isinstance(value, Mapping) or component not in value:
            return None
        value = value[component]
    return value


def _library_source_row(
    library_entry_id: str | None,
    source_row_id: str | None,
    library_entries: Mapping[str, LibraryEntry],
) -> Mapping[str, Any] | None:
    entry = library_entries.get(library_entry_id or "")
    if entry is None:
        return None
    return next(
        (
            candidate
            for candidate in (entry.payload or [])
            if isinstance(candidate, Mapping) and candidate.get("id") == source_row_id
        ),
        None,
    )


def _library_source_text(reference: Any, library_entries: Mapping[str, LibraryEntry]) -> str:
    row = _library_source_row(reference.library_entry_id, reference.source_row_id, library_entries)
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


def _web_source_text(reference: Any) -> str:
    """Return the bounded citation material supplied for a web reference.

    The URL and citation text are useful for auditing and conservative claim
    checks, but the server does not fetch or independently endorse the page.
    Web citations must not be used as proof of a candidate's personal history.
    """

    return " ".join(
        value
        for value in (reference.title, reference.excerpt, reference.url)
        if isinstance(value, str)
    )


def _added_library_rows(
    changes: Iterable[Any], library_entries: Mapping[str, LibraryEntry]
) -> dict[tuple[str, str], Mapping[str, Any]]:
    """Map explicit add-operation IDs to their authoritative source rows."""

    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for change in changes:
        if getattr(change, "operation", None) != "add_library_entry" or not getattr(change, "entry_id", None):
            continue
        row = _library_source_row(change.library_entry_id, change.source_row_id, library_entries)
        if row is not None:
            result[(change.section_id, change.entry_id)] = row
    return result


def _target_before_value(
    source_sections: list[dict[str, Any]],
    change: Any,
    added_library_rows: Mapping[tuple[str, str], Mapping[str, Any]],
) -> Any:
    """Read a target from the original CV or an explicitly added Library row."""

    try:
        return _target_value(source_sections, change)
    except TailoringFactError:
        source = added_library_rows.get((change.section_id, getattr(change, "entry_id", None)))
        if source is None:
            raise
        return source.get(getattr(change, "field", None) or "description")


def _declared_evidence_text(
    change: Any,
    source_sections: list[dict[str, Any]],
    library_entries: Mapping[str, LibraryEntry],
    added_library_rows: Mapping[tuple[str, str], Mapping[str, Any]],
    evidence_sections: list[dict[str, Any]] | None = None,
) -> str:
    # The original target text is implicit evidence for a rewrite. Do not use
    # the whole CV or the whole Library here: a metric or technology belonging
    # to one job must not authorize a new claim in another job.
    values: list[str] = []
    try:
        values.append(flatten_text(_target_before_value(source_sections, change, added_library_rows)))
    except TailoringFactError:
        pass
    evidence_sections = evidence_sections if evidence_sections is not None else source_sections
    for reference in getattr(change, "evidence", None) or []:
        if reference.source == "cv":
            values.append(_cv_source_text(reference, evidence_sections))
        elif reference.source == "library":
            values.append(_library_source_text(reference, library_entries))
        else:
            values.append(_web_source_text(reference))
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
    *,
    evidence_sections: list[dict[str, Any]] | None = None,
) -> None:
    """Reject unsupported claims introduced by editable prose operations.

    ``source_sections`` is the before-image of the write target. Fresh
    tailoring uses an empty target scaffold, while ``evidence_sections`` can
    point at the linked CV that remains available as optional citation source.
    """

    library_by_id = {entry.id: entry for entry in library_entries}
    changes = list(changes)
    added_library_rows = _added_library_rows(changes, library_by_id)
    for change in changes:
        candidate = _candidate_value(change)
        if candidate is None:
            continue
        before = flatten_text(_target_before_value(source_sections, change, added_library_rows))
        after = flatten_text(candidate)
        allowed = _declared_evidence_text(
            change,
            source_sections,
            library_by_id,
            added_library_rows,
            evidence_sections,
        )
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


def _section_claim_text(section: Mapping[str, Any] | None) -> str:
    if not isinstance(section, Mapping):
        return ""
    return flatten_text(section.get("data"))


def _reference_text(
    change: Any,
    evidence_sections: list[dict[str, Any]],
    library_entries: Mapping[str, LibraryEntry],
    *,
    personal_only: bool = False,
) -> str:
    values: list[str] = []
    for reference in getattr(change, "evidence", None) or []:
        if reference.source == "cv":
            values.append(_cv_source_text(reference, evidence_sections))
        elif reference.source == "library":
            values.append(_library_source_text(reference, library_entries))
        elif not personal_only:
            values.append(_web_source_text(reference))
    return " ".join(values)


def _value_leaves(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in {"id", "style"}:
                continue
            yield from _value_leaves(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from _value_leaves(child)
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        yield str(value)


def _changed_protected_values(
    before: Mapping[str, Any] | None,
    after: Mapping[str, Any],
) -> Iterable[tuple[str, Any]]:
    """Yield changed structured fact fields from a section replacement."""

    before_data = before.get("data") if isinstance(before, Mapping) else None
    after_data = after.get("data")
    if isinstance(after_data, Mapping):
        before_rows = {"__profile__": before_data} if isinstance(before_data, Mapping) else {}
        after_rows = {"__profile__": after_data}
    elif isinstance(after_data, list):
        before_rows = {
            row.get("id"): row
            for row in before_data or []
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        } if isinstance(before_data, list) else {}
        after_rows = {
            row.get("id"): row
            for row in after_data
            if isinstance(row, Mapping) and isinstance(row.get("id"), str)
        }
    else:
        return

    section_type = str(after.get("type", ""))
    fields = protected_fields(section_type)
    if "*" in fields:
        return
    for row_id, after_row in after_rows.items():
        before_row = before_rows.get(row_id)
        for field in sorted(fields - {"id"}):
            after_value = after_row.get(field)
            if after_value in (None, "", [], {}):
                continue
            before_value = before_row.get(field) if isinstance(before_row, Mapping) else None
            if before_value != after_value:
                yield field, after_value


def validate_tailoring_section_facts(
    before_sections: list[dict[str, Any]],
    updated_sections: list[dict[str, Any]],
    changes: Iterable[Any],
    library_entries: Iterable[LibraryEntry],
    *,
    evidence_sections: list[dict[str, Any]] | None = None,
) -> None:
    """Check facts introduced by complete section create/replace operations.

    Structural operations intentionally give the local agent more latitude
    than the narrow patch operations. Every such operation still has required
    citations and a reason. Numeric, technology, URL, and named-claim checks
    apply to the whole resulting section; structured identity fields must also
    be present in an explicit CV or Library citation rather than being
    justified only by a web page.
    """

    structural_changes = [
        change
        for change in changes
        if getattr(change, "operation", None) in {"create_section", "replace_section"}
    ]
    if not structural_changes:
        return
    library_by_id = {entry.id: entry for entry in library_entries}
    before_by_id = {str(section.get("id")): section for section in before_sections}
    after_by_id = {str(section.get("id")): section for section in updated_sections}
    evidence_sections = evidence_sections if evidence_sections is not None else before_sections

    for change in structural_changes:
        proposed = getattr(change, "section", None)
        proposed_id = getattr(proposed, "id", None)
        target_id = getattr(change, "section_id", None) or proposed_id
        after = after_by_id.get(str(target_id))
        if after is None:
            raise TailoringFactError("Structural section target is missing from the resulting CV")
        before = before_by_id.get(str(target_id))
        # A complete freeform candidate may intentionally assign a new stable
        # ID to the profile section.  Its server-owned identity is still the
        # same profile, so compare prose against the existing profile by type
        # rather than treating every immutable contact field as newly invented.
        if before is None and after.get("type") == "profile":
            before = next(
                (section for section in before_sections if section.get("type") == "profile"),
                None,
            )
        before_text = _section_claim_text(before)
        after_text = _section_claim_text(after)
        allowed = _reference_text(change, evidence_sections, library_by_id)
        new_numbers, new_technologies, new_urls = _new_claims(before_text, after_text, allowed)
        named_claims = _unsupported_named_claims(before_text, after_text, allowed)
        if new_numbers:
            raise TailoringFactError(f"Unsupported numeric claim(s): {', '.join(sorted(new_numbers))}")
        if new_technologies:
            raise TailoringFactError(f"Unsupported technology claim(s): {', '.join(sorted(new_technologies))}")
        if new_urls:
            raise TailoringFactError("Unsupported URL claim in rewritten section")
        if named_claims:
            raise TailoringFactError(f"Unsupported named claim(s): {', '.join(named_claims)}")

        personal_allowed = _reference_text(
            change,
            evidence_sections,
            library_by_id,
            personal_only=True,
        ).casefold()
        for field, value in _changed_protected_values(before, after):
            unsupported = [
                leaf
                for leaf in _value_leaves(value)
                if leaf.casefold() not in personal_allowed
            ]
            if unsupported:
                raise TailoringFactError(
                    f"Structured field {field!r} is not supported by the declared CV or Library evidence"
                )


__all__ = [
    "TailoringFactError",
    "flatten_text",
    "normalize_number",
    "number_claims",
    "technology_claims",
    "validate_tailoring_section_facts",
    "validate_tailoring_facts",
]
