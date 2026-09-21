"""Independent lexical term inventory and whole-term CV visibility checks."""

from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from collections.abc import Sequence

from app.scanner.extraction import CandidateTextSegment, candidate_facing_segments
from app.scanner.matching import CVTextField, flatten_cv_text
from app.scanner.requirements import RequirementImportance
from app.scanner.results import (
    AnalysisStatus,
    CVLocation,
    JobTextLocation,
    LexicalAnalysis,
    LexicalEvidence,
    LexicalTerm,
    LexicalVisibility,
)
from app.services.relevance_taxonomy import ALIAS_TO_CANONICAL, TAXONOMY

_DASHES = str.maketrans({char: "-" for char in "‐‑‒–—―−﹘﹣－"})
_BOUNDARY_CHARS = r"\w"
_CUSTOM_TERMS: tuple[tuple[str, str], ...] = (
    ("ai", "AI-assisted development"),
    ("ai tools", "AI tools"),
    ("genai", "GenAI"),
    ("implementing with ai", "AI-assisted development"),
    ("automated testing", "automated testing"),
    ("automated tests", "automated testing"),
    ("monitoring", "monitoring"),
    ("containerization", "containerization"),
    ("containerisation", "containerization"),
    ("ci/cd", "CI/CD"),
    ("pair-programming", "pair programming"),
    ("pair-program", "pair programming"),
    ("code reviews", "code review"),
    ("code review", "code review"),
    ("standups", "standups"),
    ("demos", "demos"),
    ("retrospectives", "retrospectives"),
    ("industry trends", "industry trends"),
    ("full-stack", "full-stack development"),
    ("full stack", "full-stack development"),
    ("front-end", "front-end development"),
    ("front end", "front-end development"),
    ("back-end", "back-end development"),
    ("back end", "back-end development"),
    ("communication", "communication"),
    ("collaboration", "collaboration"),
)
_SURFACE_VARIANTS: dict[str, tuple[str, ...]] = {
    # These are spelling, punctuation, acronym-expansion, or inflectional
    # variants. Semantic equivalents belong only in the semantic matcher.
    "genai": ("generative AI",),
    "ai-assisted development": ("AI assisted development",),
    "ai tools": (),
    "automated testing": ("automated tests",),
    "containerization": ("containerisation",),
    "ci/cd": (),  # punctuation-only forms are caught by normalized matching
    "full-stack development": ("full stack", "fullstack", "full-stack developer"),
    "front-end development": ("frontend",),
    "back-end development": ("backend",),
    "pair programming": ("pair program",),
    "collaboration": ("collaborative",),
}


def _exact_normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).translate(_DASHES).casefold()
    return " ".join(value.split())


def _punctuation_normalize(value: str) -> str:
    value = _exact_normalize(value)
    return " ".join(re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).split())


def _contains(text: str, phrase: str, *, punctuation: bool = False) -> bool:
    normalize = _punctuation_normalize if punctuation else _exact_normalize
    haystack, needle = normalize(text), normalize(phrase)
    if not needle:
        return False
    return re.search(rf"(?<![{_BOUNDARY_CHARS}]){re.escape(needle)}(?![{_BOUNDARY_CHARS}])", haystack) is not None


def _matched_surface(text: str, phrase: str, *, punctuation: bool = False) -> str | None:
    if punctuation:
        tokens = re.findall(r"[\w+#]+", phrase, re.UNICODE)
        if not tokens:
            return None
        pattern = r"(?<!\w)" + r"[^\w]+".join(re.escape(token) for token in tokens) + r"(?!\w)"
    else:
        pattern = re.escape(phrase.strip()).replace(r"\ ", r"\s+")
    match = re.search(pattern, text, re.I | re.UNICODE)
    return match.group(0) if match else None


def _custom_id(name: str) -> str:
    return f"scanner:{_exact_normalize(name).replace(' ', '_')}"


def _display_name(name: str) -> str:
    special = {
        "ai": "AI",
        "ai tools": "AI tools",
        "ci/cd": "CI/CD",
        "c#": "C#",
        "c++": "C++",
        "genai": "GenAI",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "php": "PHP",
        "python": "Python",
        "docker": "Docker",
        "git": "Git",
        "react": "React",
    }
    return special.get(_exact_normalize(name), name[:1].upper() + name[1:])


def _term_inventory(segments: Sequence[CandidateTextSegment]) -> list[dict[str, object]]:
    inventory: OrderedDict[str, dict[str, object]] = OrderedDict()
    candidates: list[tuple[str, str]] = []
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        family = TAXONOMY.get(canonical, ("", ()))[0]
        if family not in {"hard_skill", "responsibility", "certification"}:
            continue
        candidates.append((alias, canonical))
    for alias, canonical in _CUSTOM_TERMS:
        candidates.append((alias, canonical))
    candidates.sort(key=lambda item: (-len(item[0]), item[0], item[1]))

    for segment in segments:
        folded = segment.text.casefold()
        seen_in_segment: set[str] = set()
        selected_ranges: list[tuple[int, int]] = []
        for alias, canonical in candidates:
            for match in re.finditer(
                rf"(?<![{_BOUNDARY_CHARS}]){re.escape(alias.casefold())}(?![{_BOUNDARY_CHARS}])",
                folded,
            ):
                key = _custom_id(canonical) if canonical not in TAXONOMY else canonical
                if key in seen_in_segment or any(
                    match.start() < previous_end and match.end() > previous_start
                    for previous_start, previous_end in selected_ranges
                ):
                    continue
                seen_in_segment.add(key)
                selected_ranges.append((match.start(), match.end()))
                entry = inventory.setdefault(
                    key,
                    {
                        "term": _display_name(canonical),
                        "canonical": canonical,
                        "variants": list(_SURFACE_VARIANTS.get(_exact_normalize(canonical), ())),
                        "locations": [],
                        "importance": RequirementImportance.UNKNOWN,
                    },
                )
                locations = entry["locations"]
                assert isinstance(locations, list)
                locations.append(
                    JobTextLocation(
                        source_start=segment.source_start + match.start(),
                        source_end=segment.source_start + match.end(),
                        section_title=segment.section_title,
                        section_purpose=segment.section_purpose.value,
                    )
                )
                text = segment.text
                if segment.section_purpose.value == "candidate_preferences" or re.search(
                    r"\b(?:preferred|nice\s+to\s+have|bonus|asset|desirable)\b", text, re.I
                ):
                    entry["importance"] = RequirementImportance.PREFERRED
                elif entry["importance"] is RequirementImportance.UNKNOWN and segment.section_purpose.value in {
                    "candidate_responsibilities",
                    "candidate_qualifications",
                }:
                    entry["importance"] = RequirementImportance.REQUIRED

    return list(inventory.values())


def _field_location(field: CVTextField, matched_text: str) -> CVLocation:
    return CVLocation(
        section_id=field.section_id,
        section_type=field.section_type,
        entry_id=field.entry_id,
        field_path=field.field_path,
        excerpt=field.text[:2_000] or matched_text,
    )


def analyze_lexical_visibility(job_description: str, cv: object) -> LexicalAnalysis:
    """Find candidate-facing literal terms independently of semantic extraction."""

    segments = candidate_facing_segments(job_description or "")
    inventory = _term_inventory(segments)
    fields = flatten_cv_text(cv)
    terms: list[LexicalTerm] = []
    for index, item in enumerate(inventory, start=1):
        label = str(item["term"])
        canonical = str(item["canonical"])
        key = canonical if canonical in TAXONOMY else _custom_id(canonical)
        variants = [
            variant
            for variant in dict.fromkeys(item["variants"])
            if isinstance(variant, str) and _exact_normalize(variant) != _exact_normalize(label)
        ]
        exact_hits: list[tuple[CVTextField, str, str]] = []
        normalized_hits: list[tuple[CVTextField, str, str]] = []
        variant_hits: list[tuple[CVTextField, str, str]] = []
        for field in fields:
            if _contains(field.text, label):
                exact_hits.append((field, _matched_surface(field.text, label) or label, "exact"))
            elif _contains(field.text, label, punctuation=True):
                normalized_hits.append((field, _matched_surface(field.text, label, punctuation=True) or label, "normalized"))
            else:
                for variant in variants:
                    if _contains(field.text, variant):
                        variant_hits.append((field, _matched_surface(field.text, variant) or variant, "variant"))
                        break
                    if _contains(field.text, variant, punctuation=True):
                        variant_hits.append((field, _matched_surface(field.text, variant, punctuation=True) or variant, "variant"))
                        break
        hits = exact_hits or normalized_hits or variant_hits
        visibility = (
            LexicalVisibility.EXACT
            if exact_hits
            else LexicalVisibility.NORMALIZED
            if normalized_hits
            else LexicalVisibility.VARIANT
            if variant_hits
            else LexicalVisibility.ABSENT
        )
        evidence = [
            LexicalEvidence(
                location=_field_location(field, matched_text),
                matched_text=matched_text,
                visibility=hit_visibility,
            )
            for field, matched_text, hit_visibility in hits[:50]
        ]
        locations = item["locations"]
        assert isinstance(locations, list)
        terms.append(
            LexicalTerm(
                id=f"lex-{index:04d}",
                term=label,
                canonical_concept_id=key,
                variants=variants[:100],
                importance=item["importance"],  # type: ignore[arg-type]
                source_locations=locations[:100],
                visibility=visibility,
                evidence=evidence,
            )
        )
    return LexicalAnalysis(status=AnalysisStatus.EVALUATED, terms=terms[:1_000])


__all__ = ["analyze_lexical_visibility"]
