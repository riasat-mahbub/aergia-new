"""Deterministic ATS compatibility facts and platform guidance.

This module intentionally sits on top of the existing scanner branches.  It
does not implement another keyword matcher, semantic matcher, or PDF parser.
The generic checks either inspect the resolved renderer model or reference the
already computed semantic, lexical, and PDF results.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.scanner.matching import flatten_cv_text
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import (
    EvidenceStatus,
    LexicalAnalysis,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
    SemanticAnalysis,
)
from app.scanner.ats_results import (
    ATS_GUIDANCE_VERSION,
    AcronymCoverage,
    AtsFinding,
    AtsGuidance,
    AtsGuidanceSummary,
    AtsPlatformGuidance,
    AtsRule,
    AtsSource,
    DateCompatibilityFinding,
    EntryCompletenessFinding,
    HeadingConventionFinding,
    HeadingConventionStatus,
    DateCompatibilityStatus,
    AcronymCoverageStatus,
    EntryCompletenessStatus,
    AtsFindingSeverity,
)
from app.services.renderer.pipeline import prepare_render_source, resolve_source


SUPPORTED_ATS_PLATFORMS: tuple[str, ...] = (
    "workday",
    "greenhouse",
    "lever",
    "icims",
    "successfactors",
    "oracle_recruiting",
    "taleo",
    "ashby",
    "smartrecruiters",
    "bamboohr",
    "rippling",
    "workable",
    "jazzhr",
    "breezy",
)

@dataclass(frozen=True, slots=True)
class _RenderedEntry:
    section_id: str
    section_type: str
    entry_id: str
    fields: Mapping[str, str]
    label: str


@dataclass(frozen=True, slots=True)
class _RenderedFacts:
    headings: tuple[tuple[str, str, str], ...]
    entries: tuple[_RenderedEntry, ...]
    dates: tuple[tuple[str, str, str, str], ...]
    visible_text: str


def _value(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _field_text(field: object) -> str:
    blocks = _value(field, "blocks")
    if isinstance(blocks, Sequence) and not isinstance(blocks, (str, bytes, bytearray)) and blocks:
        values: list[str] = []
        for block in blocks:
            for item in _value(block, "items", []) or []:
                text = _value(item, "text")
                if text:
                    values.append(str(text).strip())
        return " ".join(item for item in values if item)
    return " ".join(
        str(text).strip()
        for run in (_value(field, "runs", []) or [])
        if (text := _value(run, "text"))
    ).strip()


def _resolved_facts(cv: object, render_manifest: object | None) -> _RenderedFacts:
    source = cv.model_dump(mode="python") if hasattr(cv, "model_dump") else cv
    sections = _value(source, "sections", []) or []
    customizations = _value(source, "customizations", {}) or {}
    try:
        model = resolve_source(
            prepare_render_source(sections, render_manifest, customizations)
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return _RenderedFacts((), (), (), " ".join(item.text for item in flatten_cv_text(cv)))

    headings: list[tuple[str, str, str]] = []
    entries: list[_RenderedEntry] = []
    dates: list[tuple[str, str, str, str]] = []
    visible: list[str] = []
    for zone in model.zones:
        for section_id in zone.section_ids:
            section = model.sections.get(section_id)
            if section is None or not section.enabled:
                continue
            if section.policy is None or section.policy.show_title:
                title = str(section.title or "").strip()
                if title:
                    headings.append((section.id, section.type, title))
                    visible.append(title)
            for entry in section.entries:
                field_map: dict[str, str] = {}
                for field in entry.fields:
                    text = _field_text(field)
                    if not text:
                        continue
                    key = str(field.key)
                    field_map[key] = f"{field_map[key]} {text}".strip() if key in field_map else text
                    visible.append(text)
                    if key.casefold() == "date":
                        dates.append((section.id, section.type, entry.id, text))
                label = next(
                    (field_map[key] for key in ("position", "project", "paper", "certification", "degree", "name", "title", "institution") if field_map.get(key)),
                    entry.id,
                )
                entries.append(_RenderedEntry(section.id, section.type, entry.id, field_map, label))
    return _RenderedFacts(tuple(headings), tuple(entries), tuple(dates), " ".join(visible))


_STANDARD_HEADINGS: dict[str, set[str]] = {
    "profile": {"profile", "summary", "professional summary", "objective"},
    "experience": {"experience", "professional experience", "work experience", "employment history", "work history"},
    "education": {"education", "academic background", "academic experience"},
    "projects": {"projects", "selected projects", "project experience"},
    "skills": {"skills", "technical skills", "core skills", "technical toolkit", "technologies"},
    "research": {"research", "publications", "research experience"},
    "certifications": {"certifications", "certificates", "credentials"},
    "languages": {"languages", "language skills"},
}
_RECOGNIZABLE_HEADINGS = {
    "employment", "professional background", "academic history", "selected work",
    "toolbox", "what i bring", "technical expertise", "awards and certifications",
}


def _heading_findings(facts: _RenderedFacts) -> list[HeadingConventionFinding]:
    findings: list[HeadingConventionFinding] = []
    for section_id, section_type, title in facts.headings:
        normalized = " ".join(title.casefold().split())
        if " & " in title or " and " in normalized:
            status: HeadingConventionStatus = "ambiguous"
            explanation = "This heading combines multiple resume sections; separate conventional headings are easier for parsers to interpret."
        elif normalized in _STANDARD_HEADINGS.get(section_type, set()):
            status = "standard"
            explanation = "The visible heading uses a conventional label for this section."
        elif normalized in _RECOGNIZABLE_HEADINGS or any(
            candidate in normalized for candidate in _STANDARD_HEADINGS.get(section_type, set())
        ):
            status = "recognizable"
            explanation = "The heading is recognizable for this section, although a conventional label may be clearer."
        else:
            status = "nonstandard"
            explanation = "The heading is not a common label for this section; a conventional label may improve parser interpretation."
        findings.append(
            HeadingConventionFinding(
                section_id=section_id,
                section_type=section_type,
                visible_heading=title,
                canonical_section=section_type,
                status=status,
                explanation=explanation,
            )
        )
    return findings


_CONVENTIONAL_DATE_RE = re.compile(
    r"^(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[- ]\d{4}|"
    r"(?:\d{2}[./-]\d{4}|\d{4}(?:[./-]\d{2})?)\s*[–-]\s*(?:Present|\d{4})|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[–-]\s*(?:Present|\d{4})|"
    r"\d{2}[./-]\d{4}|\d{4}(?:[./-]\d{2})?)$",
    re.IGNORECASE,
)


def _date_findings(facts: _RenderedFacts) -> list[DateCompatibilityFinding]:
    findings: list[DateCompatibilityFinding] = []
    for section_id, _section_type, entry_id, rendered in facts.dates:
        if _CONVENTIONAL_DATE_RE.fullmatch(rendered.strip()):
            status: DateCompatibilityStatus = "conventional"
            explanation = "The rendered date uses a common month/year or numeric year format."
        elif re.search(r"\b(?:spring|summer|fall|autumn|winter|q[1-4]|early|late|mid)\b", rendered, re.I):
            status = "potentially_ambiguous"
            explanation = "The rendered date uses a seasonal, quarter, or approximate label that some parsers may interpret inconsistently."
        else:
            status = "nonstandard"
            explanation = "The rendered date is outside Aergia's conventional month/year and numeric year formats."
        findings.append(
            DateCompatibilityFinding(
                section_id=section_id,
                entry_id=entry_id,
                rendered_text=rendered,
                status=status,
                explanation=explanation,
            )
        )
    return findings


_ENTRY_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "experience": (("position", "title"), ("company", "employer"), ("date", "dates")),
    "work_experience": (("position", "title"), ("company", "employer"), ("date", "dates")),
    "education": (("degree", "degree or program"), ("institution", "institution")),
    "certifications": (("certification", "certification"), ("issuer", "issuer")),
    "projects": (("project", "project title"),),
    "research": (("paper", "research title"),),
}


def _entry_findings(facts: _RenderedFacts) -> list[EntryCompletenessFinding]:
    findings: list[EntryCompletenessFinding] = []
    for entry in facts.entries:
        requirements = _ENTRY_FIELDS.get(entry.section_type)
        if requirements is None:
            continue
        missing = [label for key, label in requirements if not entry.fields.get(key)]
        ambiguous = entry.section_type in {"experience", "work_experience"} and bool(
            re.search(r"\s(?:/|&|\band\b)\s", entry.label, re.I)
        )
        if ambiguous:
            status: EntryCompletenessStatus = "ambiguous"
            explanation = "This entry appears to combine more than one role; separate entries make title, employer, and dates easier to associate."
        elif missing:
            status = "incomplete"
            explanation = f"The rendered entry is missing: {', '.join(missing)}."
        else:
            status = "complete"
            explanation = "The rendered entry exposes the key identifying fields for this section."
        findings.append(
            EntryCompletenessFinding(
                section_id=entry.section_id,
                entry_id=entry.entry_id,
                section_type=entry.section_type,
                label=entry.label,
                status=status,
                missing_fields=missing,
                explanation=explanation,
            )
        )
    return findings


_ACRONYM_MAP: tuple[tuple[str, str], ...] = (
    ("Project Management Professional", "PMP"),
    ("Search Engine Optimization", "SEO"),
    ("Customer Relationship Management", "CRM"),
    ("Continuous Integration / Continuous Delivery", "CI/CD"),
    ("Application Programming Interface", "API"),
    ("User Experience", "UX"),
    ("User Interface", "UI"),
    ("Software as a Service", "SaaS"),
)


def _contains_term(text: str, term: str) -> bool:
    if term in {"CI/CD", "C++", "C#", ".NET"}:
        return term.casefold() in text.casefold()
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I))


def _acronym_pairs(job_description: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for expanded, acronym in _ACRONYM_MAP:
        explicit = bool(
            re.search(rf"{re.escape(expanded)}\s*\(\s*{re.escape(acronym)}\s*\)", job_description, re.I)
            or re.search(rf"{re.escape(acronym)}\s*\(\s*{re.escape(expanded)}\s*\)", job_description, re.I)
        )
        if explicit or _contains_term(job_description, expanded) or _contains_term(job_description, acronym):
            pairs.append((expanded, acronym))
    return pairs


def _semantic_support(lexical: LexicalAnalysis, expanded: str, acronym: str) -> EvidenceStatus | None:
    statuses = [
        term.semantic_support
        for term in lexical.terms
        if _contains_term(term.term, expanded) or _contains_term(term.term, acronym)
    ]
    if EvidenceStatus.SUPPORTED in statuses:
        return EvidenceStatus.SUPPORTED
    if EvidenceStatus.PARTIAL in statuses:
        return EvidenceStatus.PARTIAL
    if EvidenceStatus.CONFLICTING in statuses:
        return EvidenceStatus.CONFLICTING
    if EvidenceStatus.NOT_EVIDENCED in statuses:
        return EvidenceStatus.NOT_EVIDENCED
    return None


def _acronym_coverage(job_description: str, cv: object, lexical: LexicalAnalysis) -> list[AcronymCoverage]:
    cv_text = " ".join(item.text for item in flatten_cv_text(cv))
    results: list[AcronymCoverage] = []
    for expanded, acronym in _acronym_pairs(job_description):
        job_acronym = _contains_term(job_description, acronym)
        job_expanded = _contains_term(job_description, expanded)
        cv_acronym = _contains_term(cv_text, acronym)
        cv_expanded = _contains_term(cv_text, expanded)
        if cv_acronym and cv_expanded:
            status: AcronymCoverageStatus = "both"
        elif cv_acronym:
            status = "acronym_only"
        elif cv_expanded:
            status = "expanded_only"
        else:
            status = "absent"
        results.append(
            AcronymCoverage(
                concept=expanded,
                acronym=acronym,
                expanded_form=expanded,
                job_uses_acronym=job_acronym,
                job_uses_expanded=job_expanded,
                cv_uses_acronym=cv_acronym,
                cv_uses_expanded=cv_expanded,
                status=status,
                semantic_support=_semantic_support(lexical, expanded, acronym),
            )
        )
    return results


def _pdf_findings(pdf: PDFTextRecoveryAnalysis) -> list[AtsFinding]:
    findings: list[AtsFinding] = []
    for check in pdf.checks:
        if check.status is PDFRecoveryStatus.PASS:
            severity: AtsFindingSeverity = "pass"
        elif check.status is PDFRecoveryStatus.UNAVAILABLE:
            severity = "info"
        elif check.code == "link_recovery":
            severity = "recommendation"
        else:
            severity = "warning"
        findings.append(
            AtsFinding(
                id=f"pdf-{check.code}",
                rule_id=check.code,
                title=check.code.replace("_", " ").title(),
                category="parsing" if check.code in {"text_retention", "reading_order"} else "links" if check.code == "link_recovery" else "parsing",
                scope="common",
                severity=severity,
                explanation=check.explanation or "Aergia PDF recovery check completed.",
                affected_items=check.affected_items,
                recovered_items=check.recovered_items,
                missing_items=check.missing_items,
            )
        )
    return findings


def _heading_guidance(findings: Sequence[HeadingConventionFinding]) -> list[AtsFinding]:
    result: list[AtsFinding] = []
    for finding in findings:
        severity: AtsFindingSeverity = "pass" if finding.status == "standard" else "info" if finding.status == "recognizable" else "warning"
        result.append(
            AtsFinding(
                id=f"heading-{finding.section_id}",
                rule_id="conventional_section_headings",
                title="Conventional section heading",
                category="headings",
                scope="common",
                severity=severity,
                explanation=f"{finding.visible_heading}: {finding.explanation}",
                action=("Use a conventional section label when it fits the content." if severity == "warning" else None),
                affected_items=[finding.visible_heading] if severity == "warning" else [],
            )
        )
    return result


def _date_guidance(findings: Sequence[DateCompatibilityFinding]) -> list[AtsFinding]:
    result: list[AtsFinding] = []
    for finding in findings:
        severity: AtsFindingSeverity = "pass" if finding.status == "conventional" else "warning"
        result.append(
            AtsFinding(
                id=f"date-{finding.section_id}-{finding.entry_id}",
                rule_id="conventional_dates",
                title="Conventional dates",
                category="dates",
                scope="common",
                severity=severity,
                explanation=f"{finding.rendered_text}: {finding.explanation}",
                action="Use a month/year or numeric year format when the date is under your control." if severity == "warning" else None,
                affected_items=[finding.rendered_text] if severity == "warning" else [],
            )
        )
    return result


def _entry_guidance(findings: Sequence[EntryCompletenessFinding]) -> list[AtsFinding]:
    result: list[AtsFinding] = []
    for finding in findings:
        severity: AtsFindingSeverity = "pass" if finding.status == "complete" else "warning"
        result.append(
            AtsFinding(
                id=f"entry-{finding.section_id}-{finding.entry_id}",
                rule_id="structured_entry_completeness",
                title="Structured entry fields",
                category="experience" if finding.section_type in {"experience", "work_experience"} else "education" if finding.section_type == "education" else "parsing",
                scope="common",
                severity=severity,
                explanation=f"{finding.label}: {finding.explanation}",
                action="Keep the title, organization, and date fields visually distinct where they apply." if severity == "warning" else None,
                affected_items=[finding.label] if severity == "warning" else [],
            )
        )
    return result


def _acronym_guidance(coverage: Sequence[AcronymCoverage]) -> list[AtsFinding]:
    result: list[AtsFinding] = []
    for item in coverage:
        if item.status == "both":
            severity: AtsFindingSeverity = "pass"
            action = None
            explanation = f"Both {item.expanded_form} and {item.acronym} are visible where the job uses this concept."
        elif item.status in {"acronym_only", "expanded_only"}:
            severity = "recommendation" if item.semantic_support in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL} else "info"
            action = "Consider including the employer's alternate form when it is accurate and natural." if severity == "recommendation" else "Only add the alternate form if it accurately describes the candidate's experience."
            explanation = f"The CV uses {item.acronym if item.status == 'acronym_only' else item.expanded_form}, while the job also uses the other form."
        else:
            severity = "recommendation" if item.semantic_support in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL} else "info"
            action = "Consider using the employer's wording only if the CV provides supporting evidence." if severity == "recommendation" else "This concept is not currently evidenced by the CV; do not add it merely for searchability."
            explanation = f"Neither {item.expanded_form} nor {item.acronym} appears in the CV."
        result.append(
            AtsFinding(
                id=f"acronym-{item.acronym.casefold().replace('/', '-')}",
                rule_id="important_acronym_coverage",
                title="Acronym and expanded form",
                category="acronyms",
                scope="common",
                severity=severity,
                explanation=explanation,
                action=action,
                affected_items=[item.acronym, item.expanded_form] if severity != "pass" else [],
            )
        )
    return result


def _semantic_keyword_guidance(lexical: LexicalAnalysis) -> list[AtsFinding]:
    findings: list[AtsFinding] = []
    for term in lexical.terms:
        if term.visibility.value != "absent":
            continue
        if term.semantic_support in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL}:
            severity: AtsFindingSeverity = "recommendation"
            action = "Consider using the employer's wording where it is accurate and natural."
            explanation = "The CV provides semantic support for this concept, but the employer's literal term is not visible."
        else:
            severity = "info"
            action = "Only add this term if the CV can support it accurately."
            explanation = "The employer term is absent and the current semantic analysis does not establish supporting CV evidence."
        findings.append(
            AtsFinding(
                id=f"keyword-{term.id}",
                rule_id="employer_wording_with_evidence",
                title=term.term,
                category="keywords",
                scope="common",
                severity=severity,
                explanation=explanation,
                action=action,
                affected_items=[term.term],
            )
        )
    return findings


_PLATFORM_NAMES = {
    "workday": "Workday",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "icims": "iCIMS",
    "successfactors": "SuccessFactors",
    "oracle_recruiting": "Oracle Recruiting",
    "taleo": "Taleo",
    "ashby": "Ashby",
    "smartrecruiters": "SmartRecruiters",
    "bamboohr": "BambooHR",
    "rippling": "Rippling",
    "workable": "Workable",
    "jazzhr": "JazzHR",
    "breezy": "Breezy HR",
}

# Platform-specific behavior is intentionally empty until a claim has a
# verified source. Every platform still receives the complete common
# interpretation, so changing the UI filter never triggers a rescan.
ATS_SOURCES: dict[str, AtsSource] = {}
ATS_RULES: dict[str, AtsRule] = {
    "searchable_text": AtsRule(
        id="searchable_text", title="Searchable text", description="Visible document text should survive PDF extraction.", category="parsing", scope="common", severity="pass"
    ),
    "structural_reading_order": AtsRule(
        id="structural_reading_order", title="Structural reading order", description="Rendered structural anchors should remain in their intended order.", category="parsing", scope="common", severity="pass"
    ),
    "readable_contacts": AtsRule(
        id="readable_contacts", title="Readable contacts", description="Visible contact fields should survive PDF extraction.", category="parsing", scope="common", severity="pass"
    ),
    "visible_section_recovery": AtsRule(
        id="visible_section_recovery", title="Visible section recovery", description="Visible section headings should survive PDF extraction.", category="parsing", scope="common", severity="pass"
    ),
    "entry_recovery": AtsRule(
        id="entry_recovery", title="Entry recovery", description="Rendered entry anchors should survive PDF extraction.", category="parsing", scope="common", severity="pass"
    ),
    "conventional_section_headings": AtsRule(
        id="conventional_section_headings", title="Conventional section headings", description="Section labels should be recognizable for their semantic section type.", category="headings", scope="common", severity="recommendation"
    ),
    "conventional_dates": AtsRule(
        id="conventional_dates", title="Conventional dates", description="Rendered dates should use common month/year or numeric year formats.", category="dates", scope="common", severity="recommendation"
    ),
    "structured_entry_completeness": AtsRule(
        id="structured_entry_completeness", title="Structured entry completeness", description="Important entry fields should remain visually distinct.", category="experience", scope="common", severity="recommendation"
    ),
    "important_acronym_coverage": AtsRule(
        id="important_acronym_coverage", title="Acronym coverage", description="Explicit job acronym and expanded forms can be compared without inventing mappings.", category="acronyms", scope="common", severity="recommendation"
    ),
    "employer_wording_with_evidence": AtsRule(
        id="employer_wording_with_evidence", title="Employer wording with evidence", description="Literal wording opportunities are separated from unsupported terms.", category="keywords", scope="common", severity="recommendation"
    ),
}

_COMMON_RULE_IDS = tuple(ATS_RULES)


def _validate_registry() -> None:
    for rule in ATS_RULES.values():
        if len(set(rule.applies_to)) != len(rule.applies_to):
            raise ValueError(f"duplicate ATS rule platform in {rule.id}")
        for platform in rule.applies_to:
            if platform not in SUPPORTED_ATS_PLATFORMS:
                raise ValueError(f"unsupported ATS platform {platform}")
        for source_id in rule.source_ids:
            if source_id not in ATS_SOURCES:
                raise ValueError(f"missing ATS source {source_id}")


_validate_registry()


def analyze_ats_guidance(
    job_description: str,
    cv: object,
    *,
    extraction: RequirementExtraction,
    semantic: SemanticAnalysis,
    lexical: LexicalAnalysis,
    pdf_recovery: PDFTextRecoveryAnalysis,
    render_manifest: object | None = None,
) -> AtsGuidance:
    """Produce common ATS facts and all platform interpretations."""

    facts = _resolved_facts(cv, render_manifest)
    headings = _heading_findings(facts)
    dates = _date_findings(facts)
    entries = _entry_findings(facts)
    acronyms = _acronym_coverage(job_description, cv, lexical)

    common_findings = [
        *_pdf_findings(pdf_recovery),
        *_heading_guidance(headings),
        *_date_guidance(dates),
        *_entry_guidance(entries),
        *_acronym_guidance(acronyms),
        *_semantic_keyword_guidance(lexical),
    ]

    # Platform interpretations deliberately share rule evaluations.  No
    # platform-specific vendor claim is emitted without a source entry.
    platforms = {
        platform: AtsPlatformGuidance(
            id=platform,
            name=_PLATFORM_NAMES[platform],
            findings=[item.model_copy(update={"applies_to": [platform]}) for item in common_findings],
            tips=[],
            source_ids=[],
        )
        for platform in SUPPORTED_ATS_PLATFORMS
    }
    warnings = sum(item.severity == "warning" for item in common_findings)
    recommendations = sum(item.severity == "recommendation" for item in common_findings)
    informational = sum(item.severity == "info" for item in common_findings)
    passes = sum(item.severity == "pass" for item in common_findings)
    return AtsGuidance(
        common_findings=common_findings,
        platform_sensitive_findings=[],
        platforms=platforms,
        heading_conventions=headings,
        date_compatibility=dates,
        acronym_coverage=acronyms,
        entry_completeness=entries,
        summary=AtsGuidanceSummary(
            platforms_checked=len(platforms),
            common_pass_count=passes,
            common_warning_count=warnings,
            recommendation_count=recommendations,
            informational_count=informational,
        ),
    )


__all__ = [
    "ATS_GUIDANCE_VERSION",
    "ATS_RULES",
    "ATS_SOURCES",
    "SUPPORTED_ATS_PLATFORMS",
    "AcronymCoverage",
    "AtsFinding",
    "AtsGuidance",
    "AtsPlatformGuidance",
    "AtsRule",
    "AtsSource",
    "DateCompatibilityFinding",
    "EntryCompletenessFinding",
    "HeadingConventionFinding",
    "analyze_ats_guidance",
]
