"""Predicate- and component-aware matching against the CV document AST."""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from difflib import SequenceMatcher

from app.scanner.aggregation import evaluate_requirement as aggregate_requirement
from app.scanner.requirements import (
    CertificationConstraint,
    Constraint,
    DegreeConstraint,
    Expectation,
    ExpectationKind,
    ExperienceDurationConstraint,
    ExamplesExpression,
    GeographicEligibilityConstraint,
    LanguageProficiencyConstraint,
    MinimumYearsConstraint,
    Requirement,
    RequirementLeaf,
    WorkAuthorizationConstraint,
)
from app.scanner.results import (
    CVLocation,
    ConstraintEvidence,
    Evidence,
    EvidenceMethod,
    EvidenceStrength,
    EvidenceStatus,
    RequirementEvaluation,
    SemanticAnalysis,
    AnalysisStatus,
)
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY

_DASHES = str.maketrans({char: "-" for char in "‐‑‒–—―−﹘﹣－"})
_WORD_RE = re.compile(r"[a-z0-9+#./-]+", re.I)
_PREDICATE_ACTION_RE = re.compile(
    r"\b(?:built|build|developed|develop|wrote|write|implemented|implement|shipped|"
    r"delivered|created|maintained|deployed|provisioned|extended|diagnosed|investigated|"
    r"resolved|tested|used|integrated|designed|led|participated|collaborated|"
    r"contributed|configured|authored|co-authored|documented|documenting|published|"
    r"worked|partnered|automated)\b",
    re.I,
)
_INTEREST_LANGUAGE_RE = re.compile(
    r"\b(?:interest(?:ed)?|keen|enthusiastic|passionate|motivated)\b",
    re.I,
)
_CURIOSITY_EVIDENCE_RE = re.compile(
    r"\b(?:curious|curiosity)\b.{0,80}\b(?:industry|technology|tech|software|market)\s+(?:trends?|developments?)\b|"
    r"\b(?:follow|track|research|monitor|read|study)(?:s|ed|ing)?\b.{0,70}"
    r"\b(?:industry|technology|tech|software|market)\s+(?:trends?|developments?)\b",
    re.I,
)
_LEARNING_RE = re.compile(r"\b(?:willing|eager|motivated|actively)\b.{0,35}\b(?:learn|learning)\b", re.I)
_PARTICIPATION_RE = re.compile(
    r"\b(?:participated|participate|paired|pair-programmed|attended|presented|"
    r"reviewed code|collaborated|worked with|mentored)\b",
    re.I,
)
_AI_CODING_USE_RE = re.compile(
    r"\b(?:used|using|leveraged|integrated|applied|relied\s+on)\b.{0,60}"
    r"\b(?:genai|generative\s+ai|llm|coding\s+agent|ai\s+coding\s+assistant|"
    r"github\s+copilot|copilot|cursor|claude\s+code)\b.{0,80}"
    r"\b(?:plan|generate|write|test|review|develop|code|coding)\b",
    re.I,
)
_LEVEL_RANK = {
    "basic": 1,
    "elementary": 1,
    "conversational": 2,
    "intermediate": 3,
    "professional": 4,
    "advanced": 4,
    "fluent": 5,
    "native": 6,
    "bilingual": 6,
}
_STOP_WORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
        "is", "of", "on", "or", "the", "to", "with", "work", "experience", "using",
    }
)
_NON_TEXT_KEYS = frozenset({"id", "url", "href", "enabled", "style", "layout", "type", "policy"})


@dataclass(frozen=True, slots=True)
class CVTextField:
    section_id: str | None
    section_type: str
    entry_id: str | None
    field_path: str
    field_key: str
    text: str


@dataclass(frozen=True, slots=True)
class _AliasHint:
    phrase: str
    status: EvidenceStatus
    method: EvidenceMethod


@dataclass(frozen=True, slots=True)
class _ConceptHit:
    status: EvidenceStatus
    method: EvidenceMethod
    matched_text: str


@dataclass(frozen=True, slots=True)
class _ConstraintResult:
    evidence: ConstraintEvidence
    fields: tuple[CVTextField, ...]


_SEMANTIC_ALIASES: dict[str, tuple[_AliasHint, ...]] = {
    "docker": (
        _AliasHint("Docker", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("Dockerized", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "ai-assisted development": (
        _AliasHint("implementing with AI", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding-agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("AI-assisted development", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("generative AI development", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("GitHub Copilot", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Copilot", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Cursor", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Claude Code", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "genai": (
        _AliasHint("GenAI", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("generative AI", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("large language model", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("LLM", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding-agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("RAG workflow", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("RAG", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Ollama", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
    ),
    "ai tools": (
        _AliasHint("AI tools", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("GenAI tools", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding-agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("coding agent", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("RAG workflow", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Ollama", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
    ),
    "containerization": (
        _AliasHint("containerization", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("containerisation", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("Docker", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Dockerized", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("containerized", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("containers", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
    ),
    "automated testing": (
        _AliasHint("automated testing", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("automated tests", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("test automation", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("unit tests", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("unit testing", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("integration tests", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("integration testing", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "software feature design": (
        _AliasHint("software feature design", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "software feature implementation": (
        _AliasHint("software feature implementation", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "software feature testing": (
        _AliasHint("software feature testing", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "software feature debugging": (
        _AliasHint("software feature debugging", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("debugged software", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("debugging software", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "bug investigation": (
        _AliasHint("bug investigation", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "bug reproduction": (_AliasHint("bug reproduction", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),),
    "bug resolution": (
        _AliasHint("bug resolution", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "full-stack development": (
        _AliasHint("full-stack", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("full-stack developer", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("full stack developer", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("fullstack developer", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "front-end development": (
        _AliasHint("front-end development", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("frontend development", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("Angular", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("React", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Ionic", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "back-end development": (
        _AliasHint("back-end development", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("backend development", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("FastAPI", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Laravel", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "documentation": (
        _AliasHint("documentation", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("technical documentation", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("documented", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("documenting", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("authored", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "collaboration": (
        _AliasHint("collaboration", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("collaborated", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("worked alongside", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("worked with", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("cross-functional", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "independent work": (
        _AliasHint("independently", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("owned", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("end-to-end", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("end to end", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
    ),
    "team environment": (
        _AliasHint("team environment", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("team", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
    ),
    "agile": (
        _AliasHint("Agile", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("Agile software development", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "microsoft cloud technologies": (
        _AliasHint("Microsoft cloud", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Microsoft cloud technologies", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("Power Platform", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("Azure", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "proactive blocker communication": (
        _AliasHint("proactive blocker communication", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
    ),
    "software development experience": (
        _AliasHint("software development experience", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("software development", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("full-stack", EvidenceStatus.PARTIAL, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("software developer", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
    "testing and quality assurance": (
        _AliasHint("testing", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("quality assurance", EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT),
        _AliasHint("unit testing", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
        _AliasHint("integration testing", EvidenceStatus.SUPPORTED, EvidenceMethod.SEMANTIC_RULE),
    ),
}

_SEMANTIC_PATTERNS: dict[str, tuple[tuple[re.Pattern[str], EvidenceStatus], ...]] = {
    "software feature design": (
        (re.compile(r"\b(?:design(?:ed|ing)?|architect(?:ed|ing)?)\b.{0,70}\b(?:software\s+)?features?\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "software feature implementation": (
        (re.compile(r"\b(?:build|built|create|created|develop|developed|implement|implemented|ship|shipped|deliver|delivered|maintain|maintained)\b.{0,100}\bfeatures?\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "software feature testing": (
        (re.compile(r"\b(?:unit|integration|automated)\s+(?:and\s+(?:unit|integration|automated)\s+)?tests?\b", re.I), EvidenceStatus.SUPPORTED),
        (re.compile(r"\b(?:write|wrote|maintain|maintained|create|created|automate|automated)\b.{0,50}\btests?\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "software feature debugging": (
        (re.compile(r"\b(?:debug|debugged|debugging|troubleshoot|troubleshot|troubleshooting)\b.{0,60}\b(?:software|code|features?|bugs?|issues?|defects?|errors?)\b", re.I), EvidenceStatus.SUPPORTED),
        (re.compile(r"\b(?:diagnose|diagnosed|diagnosing|investigate|investigated|investigating)\b.{0,60}\b(?:code[- ]quality|quality|issues?|errors?)\b", re.I), EvidenceStatus.PARTIAL),
    ),
    "bug investigation": (
        (re.compile(r"\b(?:investigate|investigated|investigating|diagnose|diagnosed|diagnosing|troubleshoot|troubleshot)\b.{0,60}\b(?:bugs?|defects?|errors?)\b", re.I), EvidenceStatus.SUPPORTED),
        (re.compile(r"\b(?:investigate|investigated|investigating|diagnose|diagnosed|diagnosing|troubleshoot|troubleshot)\b.{0,60}\b(?:code[- ]quality|quality|issues?)\b", re.I), EvidenceStatus.PARTIAL),
    ),
    "bug reproduction": (
        (re.compile(r"\breproduc(?:e|ed|ing)\b.{0,50}\b(?:bugs?|defects?|errors?|issues?)\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "bug resolution": (
        (re.compile(r"\b(?:fix|fixed|fixing|resolve|resolved|resolving|repair|repaired|repairing)\b.{0,50}\b(?:bugs?|defects?|errors?|issues?)\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "documentation": (
        (re.compile(r"\b(?:documented|documenting|authored|co-authored|published)\b.{0,100}\b(?:methods?|findings?|research|technical|documentation|report|paper)s?\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "collaboration": (
        (re.compile(r"\b(?:worked|work|partnered|collaborated)\b.{0,45}\b(?:alongside|with|across|team|developers?|designers?|engineers?)\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "independent work": (
        (re.compile(r"\b(?:owned|independently|solely)\b.{0,70}\b(?:project|implementation|development|work|delivery)?\b", re.I), EvidenceStatus.SUPPORTED),
        (re.compile(r"\bend[- ]to[- ]end\b", re.I), EvidenceStatus.PARTIAL),
    ),
    "agile": (
        (re.compile(r"\bagile\b", re.I), EvidenceStatus.SUPPORTED),
    ),
    "team environment": (
        (re.compile(r"\b(?:team|cross-functional)\b", re.I), EvidenceStatus.PARTIAL),
    ),
    "software development experience": (
        (re.compile(r"\b(?:develop(?:ed|ing)?|implement(?:ed|ing)?|engineer(?:ed|ing)?|ship(?:ped|ping)?)\b.{0,90}\b(?:software|web|mobile|features?|applications?|systems?)\b", re.I), EvidenceStatus.SUPPORTED),
        (re.compile(r"\bfull[- ]stack\b", re.I), EvidenceStatus.PARTIAL),
    ),
    "testing and quality assurance": (
        (re.compile(r"\b(?:unit|integration|automated)\s+(?:and\s+(?:unit|integration|automated)\s+)?tests?\b", re.I), EvidenceStatus.SUPPORTED),
    ),
}


def _value(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_parts(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [part for item in value for part in _text_parts(item)]
    if isinstance(value, Mapping):
        text = value.get("text")
        if isinstance(text, str):
            return [text]
        return [
            part
            for key, item in value.items()
            if str(key).casefold() not in _NON_TEXT_KEYS
            for part in _text_parts(item)
        ]
    return []


def _field_content(field: object) -> str:
    blocks = _value(field, "blocks")
    if isinstance(blocks, Sequence) and not isinstance(blocks, (str, bytes, bytearray)) and blocks:
        parts = [part for block in blocks for part in _text_parts(_value(block, "items", []))]
    else:
        parts = _text_parts(_value(field, "runs", []))
    return " ".join(part.strip() for part in parts if part.strip())


def flatten_cv_text(cv: object) -> list[CVTextField]:
    """Flatten visible AST text while preserving field and entry provenance."""

    if hasattr(cv, "model_dump"):
        cv = cv.model_dump(mode="python")  # type: ignore[union-attr]
    sections = _value(cv, "sections", [])
    if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes, bytearray)):
        return []
    fields: list[CVTextField] = []
    for section_index, section in enumerate(sections):
        if _value(section, "enabled", True) is False:
            continue
        section_id_raw = _value(section, "id")
        section_id = str(section_id_raw) if section_id_raw is not None else None
        section_type = str(_value(section, "type", "other"))
        section_fields = _value(section, "fields", [])
        found_ast_content = False
        if isinstance(section_fields, Sequence) and not isinstance(section_fields, (str, bytes, bytearray)):
            for field_index, field in enumerate(section_fields):
                text = _field_content(field)
                if not text:
                    continue
                found_ast_content = True
                key = str(_value(field, "key", f"field_{field_index}"))
                fields.append(
                    CVTextField(
                        section_id=section_id,
                        section_type=section_type,
                        entry_id=None,
                        field_path=f"sections[{section_index}].fields[{key}]",
                        field_key=key,
                        text=text,
                    )
                )
        entries = _value(section, "entries", [])
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes, bytearray)):
            entries = []
        for entry_index, entry in enumerate(entries):
            entry_id_raw = _value(entry, "id")
            entry_id = str(entry_id_raw) if entry_id_raw is not None else f"entry-{entry_index}"
            entry_fields = _value(entry, "fields", [])
            if not isinstance(entry_fields, Sequence) or isinstance(entry_fields, (str, bytes, bytearray)):
                continue
            for field_index, field in enumerate(entry_fields):
                text = _field_content(field)
                if not text:
                    continue
                found_ast_content = True
                key = str(_value(field, "key", f"field_{field_index}"))
                fields.append(
                    CVTextField(
                        section_id=section_id,
                        section_type=section_type,
                        entry_id=entry_id,
                        field_path=f"sections[{section_index}].entries[{entry_index}].fields[{key}]",
                        field_key=key,
                        text=text,
                    )
                )

        # Persisted/editor wire sections store profile values in a mapping and
        # entry-based values in a list under `data`; flatten both that shape
        # and the renderer Document AST above.
        if found_ast_content:
            continue
        data = _value(section, "data")
        if isinstance(data, Mapping):
            for key, value in data.items():
                values = list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else [value]
                for value_index, item in enumerate(values):
                    text = " ".join(part.strip() for part in _text_parts(item) if part.strip())
                    if text:
                        suffix = f"[{value_index}]" if len(values) > 1 else ""
                        fields.append(
                            CVTextField(
                                section_id=section_id,
                                section_type=section_type,
                                entry_id=None,
                                field_path=f"sections[{section_index}].data[{key}]{suffix}",
                                field_key=str(key),
                                text=text,
                            )
                        )
        elif isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
            for entry_index, entry in enumerate(data):
                if not isinstance(entry, Mapping):
                    continue
                entry_id_raw = entry.get("id")
                entry_id = str(entry_id_raw) if entry_id_raw is not None else f"entry-{entry_index}"
                for key, value in entry.items():
                    if str(key).casefold() in _NON_TEXT_KEYS:
                        continue
                    values = list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else [value]
                    for value_index, item in enumerate(values):
                        text = " ".join(part.strip() for part in _text_parts(item) if part.strip())
                        if text:
                            suffix = f"[{value_index}]" if len(values) > 1 else ""
                            fields.append(
                                CVTextField(
                                    section_id=section_id,
                                    section_type=section_type,
                                    entry_id=entry_id,
                                    field_path=f"sections[{section_index}].data[{entry_index}][{key}]{suffix}",
                                    field_key=str(key),
                                    text=text,
                                )
                            )
    return fields


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(_DASHES).casefold()
    return " ".join(normalized.split())


def _contains_phrase(haystack: str, needle: str) -> bool:
    normalized_haystack = _normalize(haystack)
    normalized_needle = _normalize(needle)
    if not normalized_needle:
        return False
    return re.search(rf"(?<![\w]){re.escape(normalized_needle)}(?![\w])", normalized_haystack) is not None


def _concept_aliases(concept: object) -> tuple[_AliasHint, ...]:
    name = str(_value(concept, "name", ""))
    normalized = _normalize(name)
    if normalized in _SEMANTIC_ALIASES:
        specific = _SEMANTIC_ALIASES[normalized]
    else:
        canonical_id = _value(concept, "canonical_id")
        canonical = str(canonical_id) if canonical_id is not None else None
        canonical = canonical if canonical in TAXONOMY else ALIAS_TO_CANONICAL.get(normalized)
        aliases = TAXONOMY.get(canonical, ("", ()))[1] if canonical else ()
        specific = tuple(
            _AliasHint(alias, EvidenceStatus.SUPPORTED, EvidenceMethod.TAXONOMY if _normalize(alias) != normalized else EvidenceMethod.EXACT)
            for alias in aliases
        )
    if not any(_normalize(item.phrase) == normalized for item in specific):
        specific = (_AliasHint(name, EvidenceStatus.SUPPORTED, EvidenceMethod.EXACT), *specific)
    deduped: list[_AliasHint] = []
    seen: set[str] = set()
    for item in specific:
        key = _normalize(item.phrase)
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return tuple(deduped)


def _semantic_pattern_hit(text: str, concept: object) -> _ConceptHit | None:
    normalized_name = _normalize(str(_value(concept, "name", "")))
    for pattern, status in _SEMANTIC_PATTERNS.get(normalized_name, ()):
        match = pattern.search(text)
        if match:
            return _ConceptHit(status, EvidenceMethod.SEMANTIC_RULE, match.group(0))
    return None


def _group_key(field: CVTextField) -> tuple[str, str]:
    if field.entry_id:
        return field.section_type, field.entry_id
    return field.section_type, field.field_path


def _field_groups(fields: Sequence[CVTextField]) -> list[list[CVTextField]]:
    grouped: dict[tuple[str, str], list[CVTextField]] = defaultdict(list)
    for field in fields:
        grouped[_group_key(field)].append(field)
    return list(grouped.values())


def _locations(fields: Sequence[CVTextField]) -> list[CVLocation]:
    locations: list[CVLocation] = []
    seen: set[str] = set()
    for field in fields:
        if field.field_path in seen:
            continue
        seen.add(field.field_path)
        locations.append(
            CVLocation(
                section_id=field.section_id,
                section_type=field.section_type,
                entry_id=field.entry_id,
                field_path=field.field_path,
                excerpt=field.text[:2_000],
            )
        )
    return locations[:50]


def _best_concept_hit(text: str, concept: object) -> _ConceptHit | None:
    hits: list[_ConceptHit] = []
    for alias in _concept_aliases(concept):
        if _contains_phrase(text, alias.phrase):
            hits.append(_ConceptHit(alias.status, alias.method, alias.phrase))
    if hits:
        for desired in (EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL):
            best = next((hit for hit in hits if hit.status is desired), None)
            if best is not None:
                return best

    pattern_hit = _semantic_pattern_hit(text, concept)
    if pattern_hit is not None:
        return pattern_hit

    tokens = [token for token in _WORD_RE.findall(_normalize(str(_value(concept, "name", "")))) if token not in _STOP_WORDS]
    if not tokens:
        return None
    fts = _fts_overlap(tokens, text)
    if fts >= 0.60:
        return _ConceptHit(EvidenceStatus.PARTIAL, EvidenceMethod.FTS5, str(_value(concept, "name", "")))
    if len(" ".join(tokens)) >= 7 and _fuzzy_overlap(tokens, text) >= 0.92:
        return _ConceptHit(EvidenceStatus.PARTIAL, EvidenceMethod.FUZZY, str(_value(concept, "name", "")))
    return None


def _fts_overlap(terms: Sequence[str], text: str) -> float:
    terms = list(dict.fromkeys(term for term in terms if len(term) > 1))
    if not terms or not text.strip():
        return 0.0
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE cv_terms USING fts5(content)")
        connection.execute("INSERT INTO cv_terms(content) VALUES (?)", (text,))
        query = " OR ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
        found = connection.execute("SELECT content FROM cv_terms WHERE cv_terms MATCH ?", (query,)).fetchone()
    except sqlite3.OperationalError:
        return 0.0
    finally:
        connection.close()
    if not found:
        return 0.0
    text_tokens = set(_WORD_RE.findall(_normalize(str(found[0]))))
    return len(set(terms) & text_tokens) / len(set(terms))


def _fuzzy_overlap(terms: Sequence[str], text: str) -> float:
    words = _WORD_RE.findall(_normalize(text))
    if not words:
        return 0.0
    width = len(terms)
    best = 0.0
    for index in range(max(1, len(words) - width + 1)):
        window = " ".join(words[index : index + width])
        best = max(best, SequenceMatcher(None, " ".join(terms), window).ratio())
    return best


def _is_experience_context(fields: Sequence[CVTextField]) -> bool:
    return any(field.section_type in {"experience", "work_experience", "projects", "project"} for field in fields)


def _matched_contexts(fields: Sequence[CVTextField], hit: _ConceptHit) -> tuple[list[CVTextField], list[str]]:
    matched_fields: list[CVTextField] = []
    contexts: list[str] = []
    pattern = re.compile(re.escape(hit.matched_text), re.I)
    for field in fields:
        matches = list(pattern.finditer(field.text))
        if not matches:
            continue
        matched_fields.append(field)
        for match in matches:
            left = max(
                field.text.rfind(".", 0, match.start()),
                field.text.rfind("!", 0, match.start()),
                field.text.rfind("?", 0, match.start()),
                field.text.rfind("\n", 0, match.start()),
            ) + 1
            endings = [position for char in ".!?\n" if (position := field.text.find(char, match.end())) >= 0]
            right = min(endings) if endings else len(field.text)
            context = field.text[left:right].strip()
            if context:
                contexts.append(context)
    if matched_fields:
        return matched_fields, contexts
    # FTS/fuzzy overlap has no stable span. Keep it as partial concept evidence
    # and never let unrelated text in the same entry establish a predicate.
    return list(fields), []


def _expectation_support(expectation: Expectation, concept: object, fields: Sequence[CVTextField], concept_hit: _ConceptHit | None) -> tuple[EvidenceStatus, list[CVTextField]]:
    if concept_hit is None:
        return EvidenceStatus.NOT_EVIDENCED, []
    matched_fields, contexts = _matched_contexts(fields, concept_hit)
    text = "\n".join(contexts)
    kind = expectation.kind
    experience = _is_experience_context(matched_fields)
    has_action = bool(_PREDICATE_ACTION_RE.search(text))
    normalized_concept = _normalize(str(_value(concept, "name", "")))
    qualifier = _normalize(expectation.qualifier or "")

    if concept_hit.status is EvidenceStatus.PARTIAL:
        return EvidenceStatus.PARTIAL, matched_fields

    if normalized_concept in {"proactive blocker communication", "open progress sharing", "asking thoughtful questions"}:
        if re.search(r"\b(?:blockers?|risks?|delays?)\b", text, re.I) and re.search(
            r"\b(?:early|proactively|escalat|raise|share)\b", text, re.I
        ):
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.NOT_EVIDENCED, []

    if normalized_concept == "documentation" and re.search(
        r"\b(?:as[- ]built|support|client\s+solution|internal\s+team)\b", qualifier, re.I
    ):
        # Research/publication documentation transfers to technical
        # documentation, but it does not prove the posting's client-solution
        # or support-documentation context.
        return EvidenceStatus.PARTIAL, matched_fields

    if any(field.section_type == "education" for field in matched_fields) and normalized_concept not in {
        "equivalent practical experience",
    }:
        return EvidenceStatus.SUPPORTED, matched_fields

    if kind is ExpectationKind.FAMILIARITY:
        if any(field.section_type == "skills" for field in matched_fields):
            return EvidenceStatus.SUPPORTED, matched_fields
        if any(field.field_key.casefold() not in {"position", "title", "start_date", "end_date"} for field in matched_fields):
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.PARTIAL, matched_fields
    if kind is ExpectationKind.PROFICIENCY:
        explicit_level = bool(re.search(r"\b(?:advanced|fluent|native|professional|proficient|expert)\b", text, re.I))
        return (EvidenceStatus.SUPPORTED if explicit_level or experience and has_action else EvidenceStatus.PARTIAL), matched_fields
    if kind is ExpectationKind.PRIOR_EXPERIENCE:
        return (EvidenceStatus.SUPPORTED if experience and has_action else EvidenceStatus.PARTIAL), matched_fields
    if kind is ExpectationKind.PRACTICAL_USE:
        if normalized_concept in {"genai", "ai tools", "ai-assisted development"}:
            return (EvidenceStatus.SUPPORTED, matched_fields) if _AI_CODING_USE_RE.search(text) else (EvidenceStatus.NOT_EVIDENCED, [])
        return (EvidenceStatus.SUPPORTED if experience and has_action else EvidenceStatus.PARTIAL), matched_fields
    if kind is ExpectationKind.ABILITY_TO_PERFORM:
        if normalized_concept in {"genai", "ai tools", "ai-assisted development"}:
            return (EvidenceStatus.SUPPORTED, matched_fields) if _AI_CODING_USE_RE.search(text) else (EvidenceStatus.NOT_EVIDENCED, [])
        return (EvidenceStatus.SUPPORTED if experience and has_action else EvidenceStatus.PARTIAL), matched_fields
    if kind is ExpectationKind.DEMONSTRATED_APPLICATION:
        if normalized_concept in {"genai", "ai tools", "ai-assisted development"} or re.search(
            r"\b(?:day[- ]to[- ]day|daily)\s+work\b", qualifier
        ):
            return (EvidenceStatus.SUPPORTED, matched_fields) if _AI_CODING_USE_RE.search(text) else (EvidenceStatus.NOT_EVIDENCED, [])
        return (EvidenceStatus.SUPPORTED if experience and has_action else EvidenceStatus.PARTIAL), matched_fields
    if kind is ExpectationKind.PARTICIPATION:
        if _PARTICIPATION_RE.search(text) and experience:
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.PARTIAL, matched_fields
    if kind is ExpectationKind.KNOWLEDGE:
        if any(field.section_type == "skills" for field in matched_fields) or experience and has_action:
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.PARTIAL, matched_fields
    if kind is ExpectationKind.INTEREST:
        if _INTEREST_LANGUAGE_RE.search(text):
            return EvidenceStatus.SUPPORTED, matched_fields
        # A related personal project is some evidence of interest, but does
        # not establish a general motivational trait.
        if any(field.section_type in {"projects", "project"} for field in matched_fields):
            return EvidenceStatus.PARTIAL, matched_fields
        return EvidenceStatus.NOT_EVIDENCED, []
    if kind is ExpectationKind.DEVELOPMENTAL_INTEREST:
        if _INTEREST_LANGUAGE_RE.search(text) or _LEARNING_RE.search(text):
            return EvidenceStatus.SUPPORTED, matched_fields
        # Demonstrated practical use is stronger evidence than a statement of
        # interest when the JD frames use of a tool as a junior learning goal.
        if experience and has_action:
            return EvidenceStatus.SUPPORTED, matched_fields
        if any(field.section_type in {"projects", "project"} for field in matched_fields):
            return EvidenceStatus.PARTIAL, matched_fields
        return EvidenceStatus.NOT_EVIDENCED, []
    if kind is ExpectationKind.CURIOSITY:
        if _CURIOSITY_EVIDENCE_RE.search(text):
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.NOT_EVIDENCED, []
    if kind is ExpectationKind.WILLINGNESS_TO_LEARN:
        if _LEARNING_RE.search(text):
            return EvidenceStatus.SUPPORTED, matched_fields
        if experience and has_action:
            return EvidenceStatus.SUPPORTED, matched_fields
        return EvidenceStatus.NOT_EVIDENCED, []
    if concept_hit.status is EvidenceStatus.SUPPORTED:
        return EvidenceStatus.PARTIAL, matched_fields
    return EvidenceStatus.NOT_EVIDENCED, []


def _parse_date(value: str, *, end: bool = False) -> date | None:
    value = value.strip()
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%Y-%m", "%B %Y", "%b %Y", "%Y"):
        try:
            parsed = datetime.strptime(value[:20], pattern).date()
            if pattern == "%Y-%m" and end:
                year, month = parsed.year, parsed.month
                month_end = 28
                while True:
                    try:
                        date(year, month, month_end + 1)
                        month_end += 1
                    except ValueError:
                        break
                return date(year, month, month_end)
            return parsed
        except ValueError:
            continue
    return None


def _entry_groups(fields: Sequence[CVTextField], section_types: set[str] | None = None) -> list[list[CVTextField]]:
    groups = _field_groups(fields)
    return [group for group in groups if not section_types or group[0].section_type in section_types]


def _year_intervals(fields: Sequence[CVTextField], concept: object, as_of: date) -> tuple[list[tuple[date, date]], list[CVTextField]]:
    intervals: list[tuple[date, date]] = []
    relevant: list[CVTextField] = []
    aliases = [item.phrase for item in _concept_aliases(concept)]
    for group in _entry_groups(fields, {"experience", "work_experience"}):
        text = " ".join(field.text for field in group)
        concept_name = _normalize(str(_value(concept, "name", "")))
        software_experience_context = (
            (
                str(_value(concept, "family", "")) == "experience"
                or "experience" in concept_name
                or "software development" in concept_name
            )
            and bool(re.search(r"\b(?:software|developer|development|engineering|programming|full[- ]stack)\b", text, re.I))
            and bool(_PREDICATE_ACTION_RE.search(text) or re.search(r"\bexperience\b", text, re.I))
        )
        if not any(_contains_phrase(text, alias) for alias in aliases) and not software_experience_context:
            continue
        values = {field.field_key.casefold(): field.text.strip() for field in group}
        start = _parse_date(values.get("start_date", values.get("start", "")))
        end_value = values.get("end_date", values.get("end", ""))
        current = values.get("current", "").casefold() in {"true", "yes", "1", "current"}
        end = as_of if current else _parse_date(end_value, end=True)
        if start and end and end >= start:
            intervals.append((start, end))
            relevant.extend(group)
    return intervals, relevant


def _merged_years(intervals: Sequence[tuple[date, date]]) -> float:
    if not intervals:
        return 0.0
    merged: list[list[date]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum((end - start).days for start, end in merged) / 365.25


def _constraint_result(constraint: Constraint, fields: Sequence[CVTextField], concept: object, as_of: date) -> _ConstraintResult:
    status = EvidenceStatus.UNVERIFIABLE
    evidence_text: str | None = None
    observation: str | None = None
    matched_fields: list[CVTextField] = []
    if isinstance(constraint, MinimumYearsConstraint):
        intervals, matched_fields = _year_intervals(fields, concept, as_of)
        if intervals:
            years = _merged_years(intervals)
            met = years > constraint.years if constraint.operator == "gt" else years >= constraint.years
            status = EvidenceStatus.SUPPORTED if met else EvidenceStatus.CONFLICTING
            evidence_text = f"{years:.1f} documented years; requirement is {constraint.operator} {constraint.years:g} years."
            observation = "meets_minimum" if met else "below_minimum"
        else:
            status = EvidenceStatus.UNVERIFIABLE
            observation = "duration_unknown"
    elif isinstance(constraint, ExperienceDurationConstraint):
        intervals, matched_fields = _year_intervals(fields, concept, as_of)
        if intervals:
            years = _merged_years(intervals)
            minimum_met = (
                constraint.min_years is None
                or years > constraint.min_years
                if constraint.min_operator == "gt"
                else constraint.min_years is None
                or years >= constraint.min_years
            )
            maximum_met = (
                constraint.max_years is None
                or years < constraint.max_years
                if constraint.max_operator == "lt"
                else constraint.max_years is None
                or years <= constraint.max_years
            )
            if not minimum_met:
                status = EvidenceStatus.CONFLICTING
                observation = "below_minimum"
            elif not maximum_met and constraint.approximate:
                # An approximate upper range is an observation about the
                # posting, not evidence absence or a contradiction in the CV.
                status = EvidenceStatus.SUPPORTED
                observation = "above_approximate_range"
            elif not maximum_met:
                status = EvidenceStatus.CONFLICTING
                observation = "above_maximum"
            else:
                status = EvidenceStatus.SUPPORTED
                observation = "within_range"
            evidence_text = f"{years:.1f} documented years; posting range is {constraint.min_years:g}–{constraint.max_years:g} years." if constraint.min_years is not None and constraint.max_years is not None else f"{years:.1f} documented years."
        else:
            status = EvidenceStatus.UNVERIFIABLE
            observation = "duration_unknown"
    elif isinstance(constraint, DegreeConstraint):
        candidates = [
            field
            for field in fields
            if field.section_type == "education" and field.field_key.casefold() in {"degree", "title", "credential", "qualification"}
        ]
        required_rank = _degree_rank(constraint.level)
        degree_fields = [(field, _degree_rank(field.text)) for field in candidates]
        degree_fields = [(field, rank) for field, rank in degree_fields if rank > 0]
        if degree_fields:
            matched_fields = [field for field, _rank in degree_fields]
            rank = max(value for _field, value in degree_fields)
            status = EvidenceStatus.SUPPORTED if rank >= required_rank else EvidenceStatus.CONFLICTING
            evidence_text = max((field.text for field, value in degree_fields if value == rank), key=len)
        else:
            status = EvidenceStatus.NOT_EVIDENCED
    elif isinstance(constraint, CertificationConstraint):
        candidates = [field for field in fields if field.section_type in {"certifications", "education", "experience", "projects"}]
        matched_fields = [field for field in candidates if _contains_phrase(field.text, constraint.name)]
        status = EvidenceStatus.SUPPORTED if matched_fields else EvidenceStatus.NOT_EVIDENCED
        evidence_text = constraint.name if matched_fields else None
    elif isinstance(constraint, LanguageProficiencyConstraint):
        matched_fields = [field for field in fields if _contains_phrase(field.text, constraint.language)]
        if matched_fields:
            level_matches = [
                match.group(0).casefold()
                for field in matched_fields
                for match in re.finditer(r"\b(?:basic|elementary|conversational|intermediate|professional|advanced|fluent|native|bilingual)\b", field.text, re.I)
            ]
            if constraint.level is None:
                status = EvidenceStatus.PARTIAL
            else:
                expected = _LEVEL_RANK.get(constraint.level.casefold(), 0)
                actual = max((_LEVEL_RANK.get(level, 0) for level in level_matches), default=0)
                status = EvidenceStatus.SUPPORTED if actual >= expected else EvidenceStatus.PARTIAL
            evidence_text = constraint.language
        else:
            status = EvidenceStatus.NOT_EVIDENCED
    elif isinstance(constraint, WorkAuthorizationConstraint):
        candidates = [field for field in fields if field.section_type == "profile"]
        matched_fields = [field for field in candidates if re.search(r"\b(?:authorized|eligible|right)\s+to\s+work\b", field.text, re.I)]
        status = EvidenceStatus.SUPPORTED if matched_fields else EvidenceStatus.NOT_EVIDENCED
        evidence_text = matched_fields[0].text if matched_fields else None
    elif isinstance(constraint, GeographicEligibilityConstraint):
        candidates = [field for field in fields if field.section_type == "profile"]
        location_matches = [
            field
            for field in candidates
            if any(_contains_phrase(field.text, location) for location in constraint.locations)
        ]
        relocation = [field for field in candidates if re.search(r"\bopen to relocation\b", field.text, re.I)]
        if location_matches:
            matched_fields = location_matches
            status = EvidenceStatus.SUPPORTED
            evidence_text = location_matches[0].text
        elif relocation:
            matched_fields = relocation
            status = EvidenceStatus.PARTIAL
            evidence_text = relocation[0].text
        else:
            status = EvidenceStatus.NOT_EVIDENCED
    return _ConstraintResult(
        evidence=ConstraintEvidence(
            constraint_id=constraint.id,
            status=status,
            evidence_text=evidence_text,
            observation=observation,
        ),
        fields=tuple(matched_fields),
    )


def _degree_rank(value: str) -> int:
    normalized = _normalize(value)
    if re.search(r"\b(?:ph\.?d|doctorate|doctoral)\b", normalized):
        return 4
    if re.search(r"\b(?:master|msc|mba|m\.s)\b", normalized):
        return 3
    if re.search(r"\b(?:bachelor|bsc|b\.s|b\.a|undergraduate)\b", normalized):
        return 2
    if re.search(r"\bassociate(?:'s)?\b", normalized):
        return 1
    return 0


def _walk_leaves(node: object) -> list[RequirementLeaf]:
    if isinstance(node, RequirementLeaf):
        return [node]
    if isinstance(node, ExamplesExpression):
        return [
            *_walk_leaves(node.subject),
            *[leaf for item in node.examples for leaf in _walk_leaves(item)],
        ]
    children = _value(node, "children", [])
    if isinstance(children, Sequence):
        return [leaf for child in children for leaf in _walk_leaves(child)]
    return []


def concepts_semantically_overlap(left: object, right: object) -> bool:
    """Return whether two concepts share a semantic alias for gap explanation."""

    left_aliases = {_normalize(item.phrase) for item in _concept_aliases(left)}
    right_aliases = {_normalize(item.phrase) for item in _concept_aliases(right)}
    return bool(left_aliases & right_aliases)


def _evidence_strength(
    leaf: RequirementLeaf,
    expectation_status: EvidenceStatus,
    concept_hit: _ConceptHit | None,
    fields: Sequence[CVTextField],
) -> EvidenceStrength:
    if concept_hit is None or expectation_status is EvidenceStatus.NOT_EVIDENCED:
        return EvidenceStrength.UNSUPPORTED
    if expectation_status is EvidenceStatus.CONFLICTING:
        return EvidenceStrength.UNSUPPORTED
    if concept_hit.status is EvidenceStatus.PARTIAL:
        return EvidenceStrength.PARTIAL_TRANSFER
    if expectation_status is EvidenceStatus.PARTIAL:
        return EvidenceStrength.PARTIAL_TRANSFER
    context = "\n".join(field.text for field in fields)
    if any(field.section_type == "education" for field in fields):
        return EvidenceStrength.DIRECT_DEMONSTRATION
    if leaf.expectation.kind is ExpectationKind.INTEREST and _INTEREST_LANGUAGE_RE.search(context):
        return EvidenceStrength.DIRECT_DEMONSTRATION
    if _is_experience_context(fields) and _PREDICATE_ACTION_RE.search(context):
        return EvidenceStrength.DIRECT_DEMONSTRATION
    if any(field.section_type == "projects" for field in fields) and _PREDICATE_ACTION_RE.search(context):
        return EvidenceStrength.DIRECT_DEMONSTRATION
    if any(field.section_type == "skills" for field in fields):
        if leaf.expectation.kind in {
            ExpectationKind.FAMILIARITY,
            ExpectationKind.KNOWLEDGE,
            ExpectationKind.INTEREST,
        }:
            return EvidenceStrength.STRONG_RELATED_EVIDENCE
        return EvidenceStrength.PARTIAL_TRANSFER
    return EvidenceStrength.STRONG_RELATED_EVIDENCE


def _evidence_for_leaf(
    leaf: RequirementLeaf,
    fields: Sequence[CVTextField],
    as_of: date,
) -> list[Evidence]:
    groups = _field_groups(fields)
    constraint_results = [_constraint_result(item, fields, leaf.concept, as_of) for item in leaf.constraints]
    global_constraint_fields = [field for item in constraint_results for field in item.fields]
    constraint_evidence = [item.evidence for item in constraint_results]
    results: list[Evidence] = []
    evidence_index = 0
    for group in groups:
        group_text = "\n".join(field.text for field in group)
        concept_hit = _best_concept_hit(group_text, leaf.concept)
        expectation_status, expectation_fields = _expectation_support(leaf.expectation, leaf.concept, group, concept_hit)
        concept_status = concept_hit.status if concept_hit else EvidenceStatus.NOT_EVIDENCED
        relevant_fields = list(group) if concept_hit else []
        relevant_fields.extend(expectation_fields)
        relevant_fields.extend(
            field
            for field in global_constraint_fields
            if group and _group_key(field) == _group_key(group[0])
        )
        relevant_fields = list({field.field_path: field for field in relevant_fields}.values())
        if not relevant_fields:
            continue
        evidence_index += 1
        group_constraints = [
            item.evidence
            for item in constraint_results
            if any(group and _group_key(field) == _group_key(group[0]) for field in item.fields)
        ]
        strength = _evidence_strength(
            leaf,
            expectation_status,
            concept_hit,
            relevant_fields,
        )
        results.append(
            Evidence(
                id=f"ev-{leaf.id}-{evidence_index:03d}",
                locations=_locations(relevant_fields),
                concept_status=concept_status,
                expectation_status=expectation_status,
                constraints=group_constraints,
                confidence=min(
                    0.92
                    if concept_hit is not None and concept_hit.status is EvidenceStatus.SUPPORTED
                    else 0.64,
                    leaf.expectation.confidence if expectation_status is EvidenceStatus.SUPPORTED else 0.62,
                ),
                method=concept_hit.method if concept_hit else EvidenceMethod.SEMANTIC_RULE,
                strength=strength,
            )
        )
    if not results and global_constraint_fields:
        results.append(
            Evidence(
                id=f"ev-{leaf.id}-001",
                locations=_locations(global_constraint_fields),
                concept_status=EvidenceStatus.NOT_EVIDENCED,
                expectation_status=EvidenceStatus.NOT_EVIDENCED,
                constraints=constraint_evidence,
                confidence=0.6,
                method=EvidenceMethod.STRUCTURED,
                strength=EvidenceStrength.STRONG_RELATED_EVIDENCE,
            )
        )
    elif results and constraint_evidence:
        attached = {
            item.constraint_id
            for result in results
            for item in result.constraints
        }
        missing_constraints = [
            item for item in constraint_evidence
            if item.constraint_id not in attached
        ]
        if missing_constraints:
            results[0] = results[0].model_copy(
                update={"constraints": [*results[0].constraints, *missing_constraints]}
            )
    return results


def evaluate_semantic_coverage(
    requirements: Sequence[Requirement],
    cv: object,
    *,
    as_of: date | None = None,
) -> SemanticAnalysis:
    """Evaluate each expression leaf and preserve its evidence dimensions."""

    fields = flatten_cv_text(cv)
    as_of_date = as_of or date.today()
    evidence: list[Evidence] = []
    evaluations: list[RequirementEvaluation] = []
    for requirement in requirements:
        evidence_by_node: dict[str, list[Evidence]] = {}
        for leaf in _walk_leaves(requirement.expression):
            leaf_evidence = _evidence_for_leaf(leaf, fields, as_of_date)
            evidence_by_node[leaf.id] = leaf_evidence
            evidence.extend(leaf_evidence)
        evaluations.append(aggregate_requirement(requirement, evidence_by_node))
    return SemanticAnalysis(
        status=AnalysisStatus.EVALUATED,
        requirements=evaluations,
        evidence=evidence[:1_000],
    )


__all__ = [
    "CVTextField",
    "concepts_semantically_overlap",
    "evaluate_semantic_coverage",
    "flatten_cv_text",
]
