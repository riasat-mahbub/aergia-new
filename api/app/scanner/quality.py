"""Bounded presentation checks separate from job-fit and keyword visibility."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from app.core.safe_url import normalize_url
from app.scanner.matching import CVTextField, flatten_cv_text
from app.scanner.results import (
    AnalysisStatus,
    BulletAssessment,
    BulletEvidenceClass,
    CVLocation,
    FindingSeverity,
    PresentationFinding,
    PresentationQualityAnalysis,
)
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY

QUALITY_VERSION = "resume-presentation-v1"
_ACTION_RE = re.compile(
    r"\b(?:built|created|designed|developed|implemented|delivered|shipped|wrote|"
    r"maintained|led|managed|launched|improved|reduced|increased|automated|"
    r"configured|deployed|migrated|analyzed|analysed|tested|resolved|extended|"
    r"collaborated|supported|contributed|provisioned|refactored|optimized|optimised)\b",
    re.I,
)
_OUTCOME_RE = re.compile(
    r"\b(?:improv(?:e|ed|ing)|reduc(?:e|ed|ing)|increas(?:e|ed|ing)|"
    r"accelerat(?:e|ed|ing)|enabl(?:e|ed|ing)|streamlin(?:e|ed|ing)|"
    r"result(?:ed|ing)\s+in|which\s+(?:improved|reduced|increased)|"
    r"so\s+that|thereby)\b",
    re.I,
)
_NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[,.]\d+)?\s*(?:%|x|k|m|million|billion)?\b", re.I)
_URL_KEYS = frozenset({"url", "link", "site_url", "photo_url", "paper_url", "credential_url"})
_BULLET_KEYS = frozenset({"description", "bullet", "bullets", "highlights", "responsibilities", "summary"})
_BULLET_PREFIX_RE = re.compile(r"^\s*[-*•▪‣]+\s*")


def _value(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _dump(cv: object) -> object:
    if hasattr(cv, "model_dump"):
        return cv.model_dump(mode="python")  # type: ignore[union-attr]
    if hasattr(cv, "sections"):
        return {"sections": getattr(cv, "sections")}
    return cv


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _text_parts(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if _is_sequence(value):
        return [part for item in value for part in _text_parts(item)]
    if isinstance(value, Mapping):
        text = value.get("text")
        if isinstance(text, str):
            return [text]
        return [part for key, item in value.items() if key in {"items", "runs"} for part in _text_parts(item)]
    return []


def _bullet_texts(cv: object, fields: Sequence[CVTextField]) -> list[tuple[CVTextField, str]]:
    source = _dump(cv)
    sections = _value(source, "sections", [])
    if not _is_sequence(sections):
        return []
    field_by_path = {field.field_path: field for field in fields}
    bullets: list[tuple[CVTextField, str]] = []
    for section_index, section in enumerate(sections):
        if _value(section, "enabled", True) is False:
            continue
        section_type = str(_value(section, "type", "other"))
        if section_type not in {"experience", "work_experience", "projects", "project", "research"}:
            continue
        entries = _value(section, "entries", [])
        if not _is_sequence(entries):
            continue
        for entry_index, entry in enumerate(entries):
            entry_fields = _value(entry, "fields", [])
            if not _is_sequence(entry_fields):
                continue
            for field_index, field in enumerate(entry_fields):
                key = str(_value(field, "key", f"field_{field_index}"))
                if key.casefold() not in _BULLET_KEYS:
                    continue
                path = f"sections[{section_index}].entries[{entry_index}].fields[{key}]"
                flattened = field_by_path.get(path)
                if flattened is None:
                    continue
                blocks = _value(field, "blocks", [])
                item_texts: list[str] = []
                if _is_sequence(blocks):
                    for block in blocks:
                        items = _value(block, "items")
                        if _is_sequence(items):
                            item_texts.extend(_text_parts(items))
                if not item_texts:
                    item_texts = [flattened.text]
                for source_text in item_texts:
                    for line in re.split(r"\n+", source_text):
                        value = _BULLET_PREFIX_RE.sub("", line).strip()
                        if value:
                            bullets.append((flattened, value))
    used_paths = {field.field_path for field, _text in bullets}
    for field in fields:
        if field.field_path in used_paths or field.field_key.casefold() not in _BULLET_KEYS:
            continue
        if field.section_type not in {"experience", "work_experience", "projects", "project", "research"}:
            continue
        if ".data[" not in field.field_path:
            continue
        for chunk in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+", field.text):
            value = _BULLET_PREFIX_RE.sub("", chunk).strip()
            if value:
                bullets.append((field, value))
    return bullets[:1_000]


def _has_technical_specificity(text: str) -> bool:
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if TAXONOMY.get(canonical, ("", ()))[0] != "hard_skill":
            continue
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.I):
            return True
    return bool(re.search(r"\b(?:api|apis|database|databases|backend|frontend|codebase|pipeline)\b", text, re.I))


def _classify_bullet(text: str) -> BulletEvidenceClass:
    has_action = bool(_ACTION_RE.search(text))
    has_technical = _has_technical_specificity(text)
    has_outcome = bool(_OUTCOME_RE.search(text))
    has_number = bool(_NUMBER_RE.search(text))
    if not has_action:
        return BulletEvidenceClass.RESPONSIBILITY_ONLY
    if has_outcome and has_number:
        return BulletEvidenceClass.ACTION_WITH_QUANTIFIED_OUTCOME
    if has_number:
        return BulletEvidenceClass.ACTION_WITH_QUANTIFIED_SCOPE
    if has_outcome:
        return BulletEvidenceClass.ACTION_WITH_QUALITATIVE_OUTCOME
    if has_technical:
        return BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY
    return BulletEvidenceClass.ACTION_ONLY


def _walk_urls(value: object, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            item_path = f"{path}.{key_text}" if path else key_text
            if (key_text in _URL_KEYS or key_text.endswith("_url")) and isinstance(item, str) and item.strip():
                found.append((item_path, item))
            found.extend(_walk_urls(item, item_path))
    elif _is_sequence(value):
        for index, item in enumerate(value):
            found.extend(_walk_urls(item, f"{path}[{index}]"))
    return found


def analyze_presentation_quality(cv: object) -> PresentationQualityAnalysis:
    """Return a small set of structural findings and per-bullet classifications."""

    source = _dump(cv)
    sections = _value(source, "sections", [])
    section_items = list(sections) if _is_sequence(sections) else []
    fields = flatten_cv_text(cv)
    findings: list[PresentationFinding] = []

    if not any(field.section_type == "profile" and field.field_key.casefold() in {"name", "full_name"} and field.text.strip() for field in fields):
        findings.append(
            PresentationFinding(
                code="missing_name",
                severity=FindingSeverity.ERROR,
                explanation="The profile does not expose a readable name field.",
            )
        )
    if not any(
        field.section_type == "profile" and field.field_key.casefold() in {"email", "phone", "telephone"} and field.text.strip()
        for field in fields
    ):
        findings.append(
            PresentationFinding(
                code="missing_contact",
                severity=FindingSeverity.WARNING,
                explanation="The profile does not expose an email address or phone number field.",
            )
        )

    section_types = {
        str(_value(section, "type", "other"))
        for section in section_items
        if _value(section, "enabled", True) is not False
    }
    if not section_types.intersection({"experience", "work_experience", "projects", "project", "research"}):
        findings.append(
            PresentationFinding(
                code="missing_work_examples",
                severity=FindingSeverity.WARNING,
                explanation="No work, project, or research section is available to show applied experience.",
            )
        )

    for path, url in _walk_urls(source):
        if url.startswith("/api/v1/assets/"):
            safe = ".." not in url and "\\" not in url
        else:
            safe = bool(normalize_url(url))
        if not safe:
            findings.append(
                PresentationFinding(
                    code="malformed_link",
                    severity=FindingSeverity.WARNING,
                    explanation="A link field does not contain a supported safe URL.",
                    evidence=path[:2_000],
                )
            )

    bullet_assessments: list[BulletAssessment] = []
    for field, text in _bullet_texts(cv, fields):
        classification = _classify_bullet(text)
        location = CVLocation(
            section_id=field.section_id,
            section_type=field.section_type,
            entry_id=field.entry_id,
            field_path=field.field_path,
            excerpt=text[:2_000],
        )
        bullet_assessments.append(BulletAssessment(location=location, classification=classification))
        if classification is BulletEvidenceClass.RESPONSIBILITY_ONLY:
            findings.append(
                PresentationFinding(
                    code="bullet_without_clear_action",
                    severity=FindingSeverity.WARNING,
                    location=location,
                    evidence=text[:2_000],
                    explanation="This bullet reads as a duty or description; consider stating the action you took when accurate.",
                )
            )
        elif classification is BulletEvidenceClass.ACTION_ONLY:
            findings.append(
                PresentationFinding(
                    code="bullet_action_only",
                    severity=FindingSeverity.INFO,
                    location=location,
                    evidence=text[:2_000],
                    explanation="This bullet states an action. Add accurate technical detail or a qualitative outcome if it would clarify the work.",
                )
            )

    return PresentationQualityAnalysis(
        status=AnalysisStatus.EVALUATED,
        findings=findings[:1_000],
        bullet_assessments=bullet_assessments[:1_000],
    )


__all__ = ["QUALITY_VERSION", "analyze_presentation_quality"]
