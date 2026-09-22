"""Typed contracts for ATS compatibility findings."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from app.scanner.requirements import ScannerModel


ATS_GUIDANCE_VERSION = "ats-guidance-v1"

HeadingConventionStatus = Literal["standard", "recognizable", "ambiguous", "nonstandard"]
DateCompatibilityStatus = Literal["conventional", "potentially_ambiguous", "nonstandard"]
AcronymCoverageStatus = Literal["both", "acronym_only", "expanded_only", "absent"]
EntryCompletenessStatus = Literal["complete", "incomplete", "ambiguous"]
AtsFindingSeverity = Literal["pass", "info", "recommendation", "warning"]
AtsRuleCategory = Literal[
    "parsing", "headings", "keywords", "acronyms", "dates", "experience",
    "education", "links", "application_fields",
]
AtsRuleScope = Literal["common", "ats_family", "platform_specific"]
AtsSourceType = Literal[
    "vendor_documentation", "independent_testing", "third_party_testing", "general_best_practice",
]


class AtsSource(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    platform: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=2_000)
    source_type: AtsSourceType
    last_verified_at: date | None = None


class AtsRule(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=2_000)
    category: AtsRuleCategory
    scope: AtsRuleScope
    severity: AtsFindingSeverity
    applies_to: list[str] = Field(default_factory=list, max_length=20)
    source_ids: list[str] = Field(default_factory=list, max_length=20)


class HeadingConventionFinding(ScannerModel):
    section_id: str = Field(min_length=1, max_length=128)
    section_type: str = Field(min_length=1, max_length=64)
    visible_heading: str = Field(min_length=1, max_length=255)
    canonical_section: str = Field(min_length=1, max_length=64)
    status: HeadingConventionStatus
    explanation: str = Field(min_length=1, max_length=2_000)


class DateCompatibilityFinding(ScannerModel):
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str = Field(min_length=1, max_length=128)
    rendered_text: str = Field(min_length=1, max_length=300)
    status: DateCompatibilityStatus
    explanation: str = Field(min_length=1, max_length=2_000)


class AcronymCoverage(ScannerModel):
    concept: str = Field(min_length=1, max_length=300)
    acronym: str = Field(min_length=1, max_length=50)
    expanded_form: str = Field(min_length=1, max_length=300)
    job_uses_acronym: bool
    job_uses_expanded: bool
    cv_uses_acronym: bool
    cv_uses_expanded: bool
    status: AcronymCoverageStatus
    semantic_support: Literal[
        "supported", "partial", "not_evidenced", "conflicting", "unverifiable"
    ] | None = None


class EntryCompletenessFinding(ScannerModel):
    section_id: str = Field(min_length=1, max_length=128)
    entry_id: str = Field(min_length=1, max_length=128)
    section_type: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=500)
    status: EntryCompletenessStatus
    missing_fields: list[str] = Field(default_factory=list, max_length=20)
    explanation: str = Field(min_length=1, max_length=2_000)


class AtsFinding(ScannerModel):
    id: str = Field(min_length=1, max_length=160)
    rule_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=300)
    category: AtsRuleCategory
    scope: AtsRuleScope
    severity: AtsFindingSeverity
    explanation: str = Field(min_length=1, max_length=2_000)
    action: str | None = Field(default=None, max_length=2_000)
    affected_items: list[str] = Field(default_factory=list, max_length=100)
    recovered_items: list[str] = Field(default_factory=list, max_length=100)
    missing_items: list[str] = Field(default_factory=list, max_length=100)
    applies_to: list[str] = Field(default_factory=list, max_length=20)
    source_ids: list[str] = Field(default_factory=list, max_length=20)


class AtsPlatformGuidance(ScannerModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    findings: list[AtsFinding] = Field(default_factory=list, max_length=200)
    tips: list[AtsFinding] = Field(default_factory=list, max_length=100)
    source_ids: list[str] = Field(default_factory=list, max_length=20)


class AtsGuidanceSummary(ScannerModel):
    platforms_checked: int = Field(ge=0)
    common_pass_count: int = Field(ge=0)
    common_warning_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    informational_count: int = Field(ge=0)


class AtsGuidance(ScannerModel):
    schema_version: Literal["ats-guidance-v1"] = "ats-guidance-v1"
    version: str = ATS_GUIDANCE_VERSION
    common_findings: list[AtsFinding] = Field(default_factory=list, max_length=500)
    platform_sensitive_findings: list[AtsFinding] = Field(default_factory=list, max_length=500)
    platforms: dict[str, AtsPlatformGuidance] = Field(default_factory=dict, max_length=20)
    heading_conventions: list[HeadingConventionFinding] = Field(default_factory=list, max_length=100)
    date_compatibility: list[DateCompatibilityFinding] = Field(default_factory=list, max_length=500)
    acronym_coverage: list[AcronymCoverage] = Field(default_factory=list, max_length=100)
    entry_completeness: list[EntryCompletenessFinding] = Field(default_factory=list, max_length=500)
    summary: AtsGuidanceSummary


__all__ = [
    "ATS_GUIDANCE_VERSION", "AcronymCoverage", "AtsFinding", "AtsGuidance",
    "AtsGuidanceSummary", "AtsPlatformGuidance", "AtsRule", "AtsSource",
    "DateCompatibilityFinding", "EntryCompletenessFinding", "HeadingConventionFinding",
]
