"""High-recall source discovery for tailoring, separate from Job Fit."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from app.scanner.matching import flatten_cv_text
from app.scanner.requirements import RequirementExtraction, RequirementLeaf
from app.scanner.results import EvidenceStatus, LexicalVisibility, ScanResult
from app.scanner.skills import canonicalize_skill, extract_skills, is_known_skill
from app.services.candidate_evidence import CandidateEvidenceSource

_STOP = frozenset({
    "about", "after", "and", "are", "build", "experience", "from", "have",
    "including", "into", "more", "must", "other", "software", "such", "that",
    "their", "them", "this", "through", "using", "with", "work", "working", "years",
})


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9]+", text.casefold())
    def cue(word: str) -> str:
        for stem in ("collaborat", "document", "communicat", "consult", "test"):
            if word.startswith(stem):
                return stem
        return word[:-1] if word.endswith("s") and not word.endswith("ss") else word

    return {cue(word) for word in words if len(word) >= 4 and word not in _STOP}


def _leaves(node: Any) -> list[RequirementLeaf]:
    if isinstance(node, RequirementLeaf):
        return [node]
    children = [getattr(node, "subject", None), *getattr(node, "examples", []), *getattr(node, "children", [])]
    return [leaf for child in children if child is not None for leaf in _leaves(child)]


def map_tailoring_opportunities(
    requirements: RequirementExtraction,
    source_scan: ScanResult | None,
    linked_cv: object | None,
    library_sources: Sequence[CandidateEvidenceSource],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Find plausible source material without changing any scan status.

    Returned narratives are bounded and selected only after the independent
    job and candidate extractions have finished.
    """

    cv_fields = flatten_cv_text(linked_cv) if linked_cv is not None else []
    target_terms = [
        leaf.concept.name
        for requirement in requirements.requirements
        for leaf in _leaves(requirement.expression)
        if is_known_skill(leaf.concept.name)
        or leaf.concept.family in {"hard_skill", "technical_skill"}
    ]
    cv_skills = set().union(*(extract_skills(field.text, target_terms=target_terms, skill_section=field.section_type == "skills") for field in cv_fields))
    work_history_skills = set().union(*(
        extract_skills(field.text, target_terms=target_terms)
        for field in cv_fields
        if field.section_type in {"experience", "projects", "research"}
    ))
    status_by_id = {item.requirement_id: item.status for item in source_scan.semantic.requirements} if source_scan else {}
    source_skills = {source.source_id: extract_skills(source.text, target_terms=target_terms) for source in library_sources}
    opportunities: list[dict[str, Any]] = []
    selected_sources: set[str] = set()

    for requirement in requirements.requirements:
        status = status_by_id.get(requirement.id, EvidenceStatus.NOT_EVIDENCED)
        names = [leaf.concept for leaf in _leaves(requirement.expression)]
        skills = {canonicalize_skill(concept.name) for concept in names if concept.name in target_terms}
        # A skills-list mention supports identity matching, while a skill
        # that is only named there can still be a useful placement opportunity
        # if Library sources contain work context.
        hidden = skills & cv_skills - work_history_skills
        missing = skills - cv_skills
        if status is EvidenceStatus.SUPPORTED and not hidden:
            continue
        label = requirement.source.original_text.strip()
        label_terms = _terms(label)
        semantic_cues = [name.casefold() for name in (concept.name for concept in names) if len(name) >= 5]
        scored: list[tuple[int, CandidateEvidenceSource]] = []
        for source in library_sources:
            skill_overlap = len((missing or skills) & source_skills[source.source_id])
            prose_overlap = len(label_terms & _terms(source.text))
            cue_overlap = any(cue in source.text.casefold() for cue in semantic_cues)
            score = skill_overlap * 5 + min(prose_overlap, 4) + int(cue_overlap) * 3
            if score >= (1 if skill_overlap else 2):
                scored.append((score, source))
        scored.sort(key=lambda item: (-item[0], item[1].source_id))
        refs = [source.source_id for _, source in scored[:3]]
        selected_sources.update(refs)
        opportunities.append({
            "requirement_id": requirement.id,
            "label": label[:500],
            "current_cv_status": status.value,
            "kind": "skill" if skills else "semantic_or_structured",
            "missing_skills": sorted(missing),
            "poorly_surfaced_skills": sorted(hidden),
            "source_ids": refs,
            "operation": "PROMOTE" if hidden and refs else "SURFACE" if missing and refs else "REFRAME" if refs else "REVIEW",
            "source_note": "Potential Library material; verify before making a claim." if refs else "No relevant Library narrative retrieved; this remains a candidate gap until verified.",
        })

    if source_scan is not None:
        for term in source_scan.lexical.terms:
            if term.visibility is not LexicalVisibility.ABSENT or term.illustrative_example:
                continue
            matching = [source for source in library_sources if term.term.casefold() in source.text.casefold()]
            if not matching:
                continue
            refs = [source.source_id for source in matching[:2]]
            selected_sources.update(refs)
            opportunities.append({
                "requirement_id": None,
                "label": term.term,
                "current_cv_status": "term_absent",
                "kind": "keyword",
                "missing_skills": [],
                "poorly_surfaced_skills": [],
                "source_ids": refs,
                "operation": "REFRAME",
                "source_note": "Employer wording appears in Library material; use only if it accurately describes the work.",
            })

    rich_sources = [
        {
            "source_id": source.source_id,
            "kind": source.kind,
            "identity": source.identity,
            "structured_facts": source.structured_facts,
            "content_hash": source.source_hash,
            "narrative": source.text[:12_000],
        }
        for source in library_sources if source.source_id in selected_sources
    ][:20]
    available = {source["source_id"] for source in rich_sources}
    for opportunity in opportunities:
        opportunity["source_ids"] = [source_id for source_id in opportunity["source_ids"] if source_id in available]
    return opportunities[:100], rich_sources


__all__ = ["map_tailoring_opportunities"]
