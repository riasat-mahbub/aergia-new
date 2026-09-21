import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  CircleX,
  Info,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import type { Application, ScannerEvidenceStatus } from "../types";
import {
  buildScannerReportViewModel,
  componentStatusIcon,
  formatScannerPercent,
  scannerStatusLabel,
  type ScannerComponentViewModel,
  type ScannerKeywordViewModel,
  type ScannerReportTab,
  type ScannerReportViewModel,
  type ScannerRequirementFilter,
  type ScannerRequirementViewModel,
} from "../domain/scannerReport";

export interface ScannerAnalysisDrawerProps {
  open: boolean;
  application: Application;
  onClose: () => void;
  onScan: () => Promise<unknown>;
  onTailor?: () => void;
  scanning?: boolean;
  scanError?: string | null;
  initialTab?: ScannerReportTab;
}

const TABS: Array<{ id: ScannerReportTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "job-fit", label: "Job Fit" },
  { id: "keywords", label: "Keywords" },
  { id: "ats", label: "ATS" },
  { id: "quality", label: "Quality" },
  { id: "pdf", label: "PDF" },
];

function percentage(value: number | null | undefined): string {
  return formatScannerPercent(value);
}

function statusTone(status: ScannerEvidenceStatus | "pass" | "warning" | "fail" | "error" | "unavailable" | "info"): string {
  if (status === "supported" || status === "pass") return "border-app-primary/30 bg-app-primary-soft text-app-primary";
  if (status === "partial" || status === "warning" || status === "info") return "border-app-warning/30 bg-app-warning-soft text-app-warning";
  if (status === "conflicting" || status === "fail" || status === "error") return "border-app-danger/30 bg-app-danger-soft text-app-danger";
  return "border-app-rule bg-app-canvas text-app-ink-3";
}

function StatusMark({ status, label }: { status: ScannerEvidenceStatus | "pass" | "warning" | "fail" | "error" | "unavailable" | "info"; label?: string }) {
  const icon = status === "supported" || status === "pass"
    ? <Check className="h-4 w-4" aria-hidden="true" />
    : status === "partial" || status === "warning" || status === "info"
      ? <AlertTriangle className="h-4 w-4" aria-hidden="true" />
        : status === "conflicting" || status === "fail" || status === "error"
        ? <CircleX className="h-4 w-4" aria-hidden="true" />
        : <CircleHelp className="h-4 w-4" aria-hidden="true" />;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(status)}`}>
      {icon}
      <span>{label ?? (status === "supported" ? "Covered" : status === "not_evidenced" ? "Not shown" : status === "partial" ? "Partial" : status === "conflicting" ? "Conflicting evidence" : status === "pass" ? "Pass" : status === "warning" ? "Warning" : status === "fail" || status === "error" ? "Needs attention" : "Unavailable")}</span>
    </span>
  );
}

function PanelSection({ title, description, children, className = "" }: { title: string; description?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-app-rule bg-app-surface p-4 shadow-sm ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-app-ink">{title}</h3>
          {description && <p className="mt-1 text-xs leading-5 text-app-ink-3">{description}</p>}
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ProgressBar({ value, label }: { value: number | null; label: string }) {
  const normalized = value === null ? 0 : Math.max(0, Math.min(1, value));
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="text-app-ink-2">{label}</span>
        <span className="font-semibold text-app-ink">{percentage(value)}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-app-surface-muted" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value === null ? undefined : Math.round(normalized * 100)}>
        <div className="h-full rounded-full bg-app-primary transition-all" style={{ width: `${normalized * 100}%` }} />
      </div>
    </div>
  );
}

function EvidenceList({ evidence, allEvidence }: { evidence: ScannerComponentViewModel["evidence"]; allEvidence?: ScannerComponentViewModel["allEvidence"] }) {
  if (evidence.length === 0) return <p className="text-xs text-app-ink-3">No supporting CV evidence was found.</p>;
  const fullEvidence = allEvidence ?? evidence;
  return (
    <div className="space-y-2">
      <ul className="space-y-2">
        {evidence.map((item, index) => (
          <li key={`${item.location.field_path}-${item.excerpt}-${index}`} className="rounded-md bg-app-canvas px-3 py-2 text-xs leading-5 text-app-ink-2">
            <p>“{item.excerpt}”</p>
            <p className="mt-1 text-app-ink-3">{item.sectionLabel}</p>
          </li>
        ))}
      </ul>
      {fullEvidence.length > evidence.length && (
        <details>
          <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Show all evidence ({fullEvidence.length})</summary>
          <ul className="mt-2 space-y-2">
            {fullEvidence.slice(evidence.length).map((item, index) => (
              <li key={`${item.location.field_path}-${item.excerpt}-all-${index}`} className="rounded-md bg-app-canvas px-3 py-2 text-xs leading-5 text-app-ink-2">
                <p>“{item.excerpt}”</p>
                <p className="mt-1 text-app-ink-3">{item.sectionLabel}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ComponentRow({ component }: { component: ScannerComponentViewModel }) {
  const icon = componentStatusIcon(component.status);
  const iconLabel = icon === "check" ? "Covered" : icon === "partial" ? "Partial" : icon === "missing" ? "Not shown" : icon === "conflict" ? "Conflicting evidence" : "Could not evaluate";
  return (
    <li className="rounded-lg border border-app-rule-soft bg-app-canvas p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2">
          <span className={`mt-0.5 ${component.status === "supported" ? "text-app-primary" : component.status === "partial" ? "text-app-warning" : component.status === "conflicting" ? "text-app-danger" : "text-app-ink-3"}`} aria-hidden="true">
            {icon === "check" ? <Check className="h-4 w-4" /> : icon === "partial" ? <AlertTriangle className="h-4 w-4" /> : icon === "conflict" ? <CircleX className="h-4 w-4" /> : <CircleHelp className="h-4 w-4" />}
          </span>
          <div>
            <p className="text-sm font-medium text-app-ink">{component.title}</p>
            <p className="text-xs text-app-ink-3">{component.illustrative ? "Employer example" : component.optional ? "Optional" : iconLabel}</p>
          </div>
        </div>
        {!component.illustrative && <StatusMark status={component.status} />}
      </div>
      {component.evidence.length > 0 && <div className="mt-3"><EvidenceList evidence={component.evidence} allEvidence={component.allEvidence} /></div>}
    </li>
  );
}

function RequirementCard({ requirement }: { requirement: ScannerRequirementViewModel }) {
  return (
    <details className="group rounded-xl border border-app-rule bg-app-surface shadow-sm">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-inset">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-app-ink">{requirement.title}</h3>
            <span className="text-xs text-app-ink-3">{requirement.importanceLabel}</span>
          </div>
          <p className="mt-1 text-xs text-app-ink-3">{requirement.components.length > 1 ? `${requirement.components.filter((component) => !component.illustrative && !component.optional && component.status === "supported").length} of ${requirement.components.filter((component) => !component.illustrative && !component.optional).length} components covered` : requirement.sourceText}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusMark status={requirement.status} label={requirement.statusLabel} />
          <ChevronDown className="h-4 w-4 text-app-ink-3 transition-transform group-open:rotate-180" aria-hidden="true" />
        </div>
      </summary>
      <div className="border-t border-app-rule-soft px-4 pb-4 pt-3">
        <p className="text-sm leading-6 text-app-ink-2">{requirement.explanation}</p>
        {requirement.relationLabel && <p className="mt-2 rounded-md bg-app-primary-soft px-3 py-2 text-xs text-app-primary">{requirement.relationLabel}</p>}
        {requirement.examples.length > 0 && <p className="mt-2 text-xs text-app-ink-3">Examples mentioned by the employer: {requirement.examples.join(" · ")}</p>}
        <ul className="mt-4 space-y-2">
          {requirement.components.map((component) => <ComponentRow key={component.id} component={component} />)}
        </ul>
        {requirement.evidence.length > 0 && requirement.components.length === 0 && <div className="mt-4"><EvidenceList evidence={requirement.evidence} /></div>}
        <details className="mt-4">
          <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Why this result</summary>
          <p className="mt-2 rounded-md bg-app-canvas px-3 py-2 text-xs leading-5 text-app-ink-2">Source requirement: “{requirement.sourceText}”</p>
        </details>
      </div>
    </details>
  );
}

function Overview({ report, onTab }: { report: ScannerReportViewModel; onTab: (tab: ScannerReportTab) => void }) {
  const scoreLabel = report.score.status === "available" && report.score.jobFit !== null
    ? percentage(report.score.jobFit)
    : report.score.status === "insufficient_scorable_evidence" ? "Unavailable" : "—";
  const cards: Array<{ tab: ScannerReportTab; title: string; detail: string; status: "pass" | "warning" | "fail" | "info" }> = [
    { tab: "job-fit", title: "Job Fit", detail: `${report.gaps.length} requirement${report.gaps.length === 1 ? "" : "s"} needs attention`, status: report.gaps.length > 0 ? "warning" : "pass" },
    { tab: "keywords", title: "Keywords", detail: `${report.keywords.safeWording.length + report.keywords.reviewBeforeAdding.length} wording opportunit${report.keywords.safeWording.length + report.keywords.reviewBeforeAdding.length === 1 ? "y" : "ies"}`, status: report.keywords.safeWording.length + report.keywords.reviewBeforeAdding.length > 0 ? "warning" : "pass" },
    { tab: "ats", title: "ATS Readiness", detail: `${report.ats.checks.filter((check) => check.status === "warning" || check.status === "fail").length} issue${report.ats.checks.filter((check) => check.status === "warning" || check.status === "fail").length === 1 ? "" : "s"} detected`, status: report.ats.status === "looks_good" ? "pass" : report.ats.status === "at_risk" ? "fail" : "warning" },
    { tab: "quality", title: "Resume Quality", detail: report.quality.findings.length === 0 ? "No issues found" : `${report.quality.findings.length} finding${report.quality.findings.length === 1 ? "" : "s"}`, status: report.quality.findings.length === 0 ? "pass" : "warning" },
    { tab: "pdf", title: "PDF Compatibility", detail: report.pdf.status === "pass" ? "Recovery checks passed" : report.pdf.status === "unavailable" ? "Not available" : "Needs attention", status: report.pdf.status === "pass" ? "pass" : report.pdf.status === "fail" ? "fail" : "warning" },
  ];
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-app-primary/20 bg-app-primary-soft p-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-app-primary">Semantic job fit</p>
            <p className="mt-2 text-5xl font-semibold tracking-tight text-app-ink">{scoreLabel}</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-app-ink-2">How well the evidence in this CV supports the job’s requirements.</p>
          </div>
          <div className="grid grid-cols-2 gap-x-5 gap-y-2 text-right text-xs sm:grid-cols-4">
            <Count label="Covered" value={report.score.coveredCount} tone="text-app-primary" />
            <Count label="Partial" value={report.score.partialCount} tone="text-app-warning" />
            <Count label="Not shown" value={report.score.notShownCount} tone="text-app-danger" />
            {report.score.conflictingCount > 0 && <Count label="Conflicting" value={report.score.conflictingCount} tone="text-app-danger" />}
            {report.score.unverifiableCount > 0 && <Count label="Couldn’t evaluate" value={report.score.unverifiableCount} tone="text-app-ink-3" />}
          </div>
        </div>
        {report.score.lowClassificationWarning && <p className="mt-4 flex items-start gap-2 rounded-md border border-app-warning/30 bg-app-warning-soft px-3 py-2 text-xs leading-5 text-app-warning"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> Some job requirements could not be confidently categorized, so this score may be less complete.</p>}
      </section>

      <PanelSection title="Coverage" description="Coverage tells you how complete the scanner’s interpretation and CV evidence are.">
        <div className="space-y-4">
          <ProgressBar value={report.score.classifiedFraction} label="Requirements confidently classified" />
          <ProgressBar value={report.score.evidenceScorableFraction} label="Classified requirements evaluable against this CV" />
        </div>
        {report.score.requiredConstraintConflicts > 0 && <p className="mt-3 text-xs text-app-danger">{report.score.requiredConstraintConflicts} required constraint conflict{report.score.requiredConstraintConflicts === 1 ? "" : "s"} needs review.</p>}
      </PanelSection>

      {report.requirements.some((requirement) => requirement.unclassified) && <section className="rounded-xl border border-app-warning/30 bg-app-warning-soft p-4">
        <div className="flex items-start gap-2">
          <CircleHelp className="mt-0.5 h-4 w-4 shrink-0 text-app-warning" aria-hidden="true" />
          <div>
            <h3 className="text-sm font-semibold text-app-ink">Some requirements need review</h3>
            <p className="mt-1 text-xs leading-5 text-app-ink-2">{report.requirements.filter((requirement) => requirement.unclassified).length} job requirement{report.requirements.filter((requirement) => requirement.unclassified).length === 1 ? "" : "s"} could not be confidently categorized, so they are kept visible without affecting the headline score.</p>
            <button type="button" onClick={() => onTab("job-fit")} className="mt-3 text-xs font-semibold text-app-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Review unclassified requirements</button>
          </div>
        </div>
      </section>}

      <PanelSection title="Fit breakdown" description="Qualifications contribute most to Job Fit, followed by responsibilities and preferred criteria. Empty categories are redistributed.">
        <div className="space-y-4">
          {Object.values(report.score.buckets).map((bucket) => <ProgressBar key={bucket.label} value={bucket.totalWeight > 0 ? bucket.score : null} label={bucket.label} />)}
        </div>
      </PanelSection>

      <div className="grid gap-4 sm:grid-cols-2">
        <PanelSection title="Covered" description="Strongest requirement matches.">
          {report.strengths.length > 0 ? <ul className="space-y-2">{report.strengths.slice(0, 4).map((item) => <li key={item.id} className="flex items-start gap-2 text-sm text-app-ink-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-app-primary" aria-hidden="true" />{item.title}</li>)}</ul> : <p className="text-sm text-app-ink-2">No fully covered requirements yet.</p>}
        </PanelSection>
        <PanelSection title="Needs attention" description="Partial or unsupported requirements to review.">
          {report.gaps.length > 0 ? <ul className="space-y-2">{report.gaps.slice(0, 4).map((item) => <li key={item.id} className="flex items-start gap-2 text-sm text-app-ink-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-app-warning" aria-hidden="true" />{item.title}</li>)}</ul> : <p className="text-sm text-app-ink-2">No gaps were identified.</p>}
        </PanelSection>
      </div>

      <div className="space-y-2">
        {cards.map((card) => (
          <button key={card.tab} type="button" onClick={() => onTab(card.tab)} className="flex w-full items-center justify-between rounded-xl border border-app-rule bg-app-surface px-4 py-3 text-left shadow-sm transition-colors hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">
            <span className="flex items-center gap-3"><StatusMark status={card.status} label={card.status === "pass" ? "" : undefined} /><span><span className="block text-sm font-semibold text-app-ink">{card.title}</span><span className="block text-xs text-app-ink-3">{card.detail}</span></span></span>
            <ChevronRight className="h-4 w-4 text-app-ink-3" aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}

function Count({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div><p className={`text-lg font-semibold ${tone}`}>{value}</p><p className="text-app-ink-3">{label}</p></div>;
}

function JobFit({ report }: { report: ScannerReportViewModel }) {
  const [filter, setFilter] = useState<ScannerRequirementFilter>("needs_attention");
  const visible = report.requirements.filter((requirement) => {
    if (filter === "covered") return requirement.status === "supported";
    if (filter === "unclassified") return requirement.unclassified;
    if (filter === "all") return true;
    return requirement.status !== "supported";
  });
  const filters: Array<{ id: ScannerRequirementFilter; label: string; count: number }> = [
    { id: "needs_attention", label: "Needs attention", count: report.gaps.length },
    { id: "covered", label: "Covered", count: report.score.coveredCount },
    { id: "all", label: "All", count: report.requirements.length },
    { id: "unclassified", label: "Unclassified", count: report.requirements.filter((item) => item.unclassified).length },
  ];
  return (
    <div className="space-y-4">
      <PanelSection title="Job Fit" description="Review how the CV currently demonstrates each candidate-facing requirement. Not shown means the CV does not provide enough evidence; it does not prove the candidate lacks the skill.">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Requirement filters">
          {filters.filter((item) => item.id !== "unclassified" || item.count > 0).map((item) => <button key={item.id} type="button" role="tab" aria-selected={filter === item.id} onClick={() => setFilter(item.id)} className={`rounded-full border px-3 py-1.5 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary ${filter === item.id ? "border-app-primary bg-app-primary-soft text-app-primary" : "border-app-rule-strong text-app-ink-2 hover:bg-app-surface-muted"}`}>{item.label} ({item.count})</button>)}
        </div>
      </PanelSection>
      {visible.length > 0 ? <div className="space-y-3">{visible.map((requirement) => <RequirementCard key={requirement.id} requirement={requirement} />)}</div> : <div className="rounded-xl border border-dashed border-app-rule-strong bg-app-surface p-6 text-center text-sm text-app-ink-2">No requirements in this view.</div>}
    </div>
  );
}

function KeywordCard({ term }: { term: ScannerKeywordViewModel }) {
  return (
    <details className="group rounded-xl border border-app-rule bg-app-surface shadow-sm">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-inset">
        <div><p className="text-sm font-semibold text-app-ink">{term.term}</p><p className="mt-1 text-xs text-app-ink-3">{term.categoryLabel}{term.occurrenceCount > 0 ? ` · Found in ${term.occurrenceCount} place${term.occurrenceCount === 1 ? "" : "s"}` : ""}</p></div>
        <span className="flex shrink-0 items-center gap-2"><StatusMark status={term.category === "safe_wording" || term.category === "visible" ? "supported" : term.category === "review_before_adding" ? "partial" : term.category === "unsupported" ? "not_evidenced" : "info"} label={term.visibilityLabel} /><ChevronDown className="h-4 w-4 text-app-ink-3 transition-transform group-open:rotate-180" aria-hidden="true" /></span>
      </summary>
      <div className="border-t border-app-rule-soft px-4 pb-4 pt-3">
        <p className="text-sm leading-6 text-app-ink-2">
          {term.category === "safe_wording" ? "Your CV appears to support this idea but does not use the employer’s wording." : term.category === "review_before_adding" ? "Your CV has partial supporting evidence. Review the wording before adding this term." : term.category === "unsupported" ? "This term is missing and the current CV does not provide sufficient evidence for the capability. Only add it if it accurately reflects your experience." : term.category === "employer_vocabulary" ? "This is terminology the employer used as an example. It does not affect Term Visibility." : "This wording is already visible in the CV."}
        </p>
        {term.evidence.length > 0 && <div className="mt-3"><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-app-ink-3">CV evidence</p><EvidenceList evidence={term.evidence} allEvidence={term.allEvidence} /></div>}
      </div>
    </details>
  );
}

function Keywords({ report }: { report: ScannerReportViewModel }) {
  const groups: Array<{ title: string; description: string; terms: ScannerKeywordViewModel[]; icon: ReactNode }> = [
    { title: "Safe wording opportunities", description: "Relevant evidence exists, but the employer’s terminology is absent.", terms: report.keywords.safeWording, icon: <Sparkles className="h-4 w-4" aria-hidden="true" /> },
    { title: "Review before adding", description: "The CV provides partial evidence. Strengthen wording only to the level supported by evidence.", terms: report.keywords.reviewBeforeAdding, icon: <AlertTriangle className="h-4 w-4" aria-hidden="true" /> },
    { title: "Unsupported or not shown", description: "Missing wording and insufficient evidence are separate from a safe wording opportunity.", terms: report.keywords.unsupported, icon: <CircleX className="h-4 w-4" aria-hidden="true" /> },
    { title: "Employer vocabulary", description: "Illustrative terms used by the employer. They do not count as required lexical gaps.", terms: report.keywords.employerVocabulary, icon: <Info className="h-4 w-4" aria-hidden="true" /> },
  ];
  return (
    <div className="space-y-4">
      <PanelSection title="Keyword wording" description="Term Visibility measures how much employer terminology appears in this CV. It does not determine whether your experience supports a skill.">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-4xl font-semibold text-app-ink">{percentage(report.keywords.visibilityScore)}</p><p className="mt-1 text-xs text-app-ink-3">Term Visibility</p></div><p className="text-right text-xs text-app-ink-3">{report.keywords.exactCount} exact · {report.keywords.normalizedCount} normalized · {report.keywords.variantCount} variants · {report.keywords.absentCount} absent</p></div>
      </PanelSection>
      {groups.map((group) => <section key={group.title} className="space-y-2"><div className="flex items-start gap-2 px-1"><span className="mt-0.5 text-app-primary">{group.icon}</span><div><h3 className="text-sm font-semibold text-app-ink">{group.title} <span className="font-normal text-app-ink-3">({group.terms.length})</span></h3><p className="mt-1 text-xs leading-5 text-app-ink-3">{group.description}</p></div></div>{group.terms.length > 0 ? <div className="space-y-2">{group.terms.map((term) => <KeywordCard key={term.id} term={term} />)}</div> : <p className="rounded-lg border border-dashed border-app-rule-strong px-4 py-3 text-xs text-app-ink-3">None found.</p>}</section>)}
    </div>
  );
}

function AtsReadiness({ report }: { report: ScannerReportViewModel }) {
  return (
    <div className="space-y-4">
      <PanelSection title="ATS Readiness" description="These checks cover structural signals that commonly affect machine parsing. Actual ATS behavior varies by system.">
        <div className="flex items-center gap-3"><StatusMark status={report.ats.status === "looks_good" ? "pass" : report.ats.status === "at_risk" ? "fail" : report.ats.status === "unavailable" ? "unavailable" : "warning"} label={report.ats.statusLabel} /><Search className="ml-auto h-6 w-6 text-app-primary" aria-hidden="true" /></div>
      </PanelSection>
      <div className="space-y-2">{report.ats.checks.map((check) => <CheckCard key={check.code} check={check} />)}</div>
    </div>
  );
}

function CheckCard({ check }: { check: ScannerAnalysisCheck }) {
  return (
    <details className="group rounded-xl border border-app-rule bg-app-surface shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-inset"><span className="flex items-center gap-3"><StatusMark status={check.status} label={check.statusLabel} /><span className="text-sm font-medium text-app-ink">{check.label}</span></span><span className="flex items-center gap-2 text-xs text-app-ink-3">{check.value !== null && percentage(check.value)}<ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden="true" /></span></summary>
      <div className="border-t border-app-rule-soft px-4 pb-4 pt-3"><p className="text-xs leading-5 text-app-ink-2">{check.explanation}</p>{check.expectedCount !== null && check.recoveredCount !== null && <p className="mt-2 text-xs font-medium text-app-ink-2">{check.recoveredCount} / {check.expectedCount} recovered</p>}</div>
    </details>
  );
}

type ScannerAnalysisCheck = ScannerReportViewModel["ats"]["checks"][number];

function Quality({ report }: { report: ScannerReportViewModel }) {
  return (
    <div className="space-y-4">
      <PanelSection title="Resume Quality" description="Presentation findings are separate from semantic Job Fit and keyword visibility.">
        <div className="flex items-center justify-between gap-3"><StatusMark status={report.quality.status === "looks_good" ? "pass" : report.quality.status === "at_risk" ? "fail" : report.quality.status === "unavailable" ? "unavailable" : "warning"} label={report.quality.statusLabel} /><p className="text-xs text-app-ink-3">{report.quality.errorCount} errors · {report.quality.warningCount} warnings · {report.quality.infoCount} suggestions</p></div>
      </PanelSection>
      {report.quality.findings.length > 0 ? <div className="space-y-2">{report.quality.findings.map((finding, index) => <article key={`${finding.code}-${index}`} className="rounded-xl border border-app-rule bg-app-surface p-4 shadow-sm"><div className="flex flex-wrap items-center gap-2"><StatusMark status={finding.severity} label={finding.severityLabel} /><span className="text-sm font-semibold text-app-ink">{finding.label}</span><span className="text-xs text-app-ink-3">{finding.locationLabel}</span></div><p className="mt-2 text-sm leading-6 text-app-ink-2">{finding.explanation}</p>{finding.evidence && <p className="mt-2 rounded-md bg-app-canvas px-3 py-2 text-xs leading-5 text-app-ink-2">“{finding.evidence}”</p>}</article>)}</div> : <div className="rounded-xl border border-app-primary/20 bg-app-primary-soft p-5 text-center"><ShieldCheck className="mx-auto h-7 w-7 text-app-primary" aria-hidden="true" /><p className="mt-2 text-sm font-semibold text-app-ink">Looks good</p><p className="mt-1 text-xs text-app-ink-2">No writing or structural issues detected.</p></div>}
      {report.quality.bulletAssessmentCount > 0 && <details className="rounded-xl border border-app-rule bg-app-surface p-4"><summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">View analyzed bullets ({report.quality.bulletAssessmentCount})</summary><p className="mt-2 text-xs leading-5 text-app-ink-3">Detailed bullet classifications are available in developer diagnostics.</p></details>}
    </div>
  );
}

function PdfCompatibility({ report }: { report: ScannerReportViewModel }) {
  return (
    <div className="space-y-4">
      <PanelSection title="PDF Compatibility" description="Shows what Aergia recovered from the actual rendered PDF. It does not guarantee behavior in every ATS.">
        <div className="flex flex-wrap items-center justify-between gap-3"><StatusMark status={report.pdf.status} label={report.pdf.statusLabel} /><p className="text-3xl font-semibold text-app-ink">{percentage(report.pdf.recoveryScore)}</p></div>
      </PanelSection>
      <div className="space-y-2">{report.pdf.checks.map((check) => <CheckCard key={check.code} check={check} />)}</div>
      <p className="rounded-lg bg-app-canvas px-4 py-3 text-xs leading-5 text-app-ink-3">{report.pdf.disclaimer}</p>
    </div>
  );
}

function EmptyAnalysis({ application, onScan, scanning, scanError }: { application: Application; onScan: () => Promise<unknown>; scanning?: boolean; scanError?: string | null }) {
  const [localError, setLocalError] = useState<string | null>(null);
  const runScan = async () => {
    setLocalError(null);
    try {
      await onScan();
    } catch {
      setLocalError("We couldn’t complete the analysis. Please try again.");
    }
  };
  return (
    <div className="flex min-h-[28rem] flex-col items-center justify-center rounded-xl border border-dashed border-app-rule-strong bg-app-surface p-8 text-center">
      <Search className="h-9 w-9 text-app-primary" aria-hidden="true" />
      <h3 className="mt-4 text-lg font-semibold text-app-ink">{application.cv_id ? "Analyze this CV" : "Link a CV to analyze this application"}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-app-ink-2">{application.cv_id ? "Run the scanner to compare this CV with the job description." : "Link or create a CV from the application page before running the scanner."}</p>
      {(scanError || localError) && <p className="mt-4 text-sm text-app-danger" role="alert">{scanError ?? localError}</p>}
      <button type="button" onClick={runScan} disabled={!application.cv_id || scanning} className="mt-5 inline-flex items-center gap-2 rounded-md bg-app-primary px-4 py-2 text-sm font-medium text-white hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${scanning ? "animate-spin" : ""}`} aria-hidden="true" />{scanning ? "Analyzing…" : "Analyze CV"}</button>
    </div>
  );
}

function Diagnostics({ report }: { report: ScannerReportViewModel }) {
  return (
    <details className="mt-6 rounded-xl border border-dashed border-app-rule-strong bg-app-canvas p-4">
      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-app-ink-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Developer diagnostics</summary>
      <div className="mt-4 space-y-3 text-xs text-app-ink-2"><pre className="overflow-auto rounded-md bg-app-surface p-3 leading-5">{JSON.stringify({ versions: report.diagnostics.versions, extractionWarnings: report.diagnostics.extractionWarnings, fingerprints: report.diagnostics.fingerprints }, null, 2)}</pre><details><summary className="cursor-pointer font-medium text-app-primary">Raw scanner result</summary><pre className="mt-2 max-h-96 overflow-auto rounded-md bg-app-surface p-3 leading-5">{JSON.stringify(report.diagnostics.raw, null, 2)}</pre></details></div>
    </details>
  );
}

export default function ScannerAnalysisDrawer({ open, application, onClose, onScan, onTailor, scanning = false, scanError = null, initialTab = "overview" }: ScannerAnalysisDrawerProps) {
  const [tab, setTab] = useState<ScannerReportTab>(initialTab);
  const [localScanError, setLocalScanError] = useState<string | null>(null);
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const report = application.scanner_result ? buildScannerReportViewModel(application.scanner_result, application) : null;
  const handleScan = async () => {
    setLocalScanError(null);
    try {
      await onScan();
    } catch {
      setLocalScanError("We couldn’t complete the analysis. Please try again.");
    }
  };

  useEffect(() => {
    if (!open) return;
    // Each opening starts at the overview so the report has a predictable entry point.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset the transient tab when the modal opens
    setTab(initialTab);
  }, [initialTab, open]);

  useEffect(() => {
    if (!open) return undefined;
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>("button:not([disabled]), [href], summary, [tabindex]:not([tabindex='-1'])"));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocus.current?.focus();
    };
  }, [onClose, open]);

  const tabIndex = TABS.findIndex((item) => item.id === tab);
  const handleTabKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const next = event.key === "ArrowRight" ? (tabIndex + 1) % TABS.length : (tabIndex - 1 + TABS.length) % TABS.length;
    setTab(TABS[next].id);
    document.getElementById(`scanner-tab-${TABS[next].id}`)?.focus();
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button type="button" aria-label="Close resume analysis" className="absolute inset-0 h-full w-full cursor-default bg-black/30" onClick={onClose} />
      <aside ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={titleId} className="absolute right-0 top-0 flex h-full w-full max-w-2xl flex-col overflow-hidden bg-app-canvas shadow-2xl">
        <header className="shrink-0 border-b border-app-rule bg-app-surface px-4 py-4 sm:px-6">
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-app-primary">Resume Analysis</p><h2 id={titleId} className="mt-1 text-xl font-semibold text-app-ink">{application.company} <span className="font-normal text-app-ink-2">— {application.role}</span></h2><p className="mt-2 text-xs text-app-ink-3">Status: {scannerStatusLabel(application.scanner_status ?? (application.scanner_result ? "current" : "not_scanned"))}</p></div>
            <button ref={closeRef} type="button" aria-label="Close resume analysis" onClick={onClose} className="rounded-md p-2 text-app-ink-3 hover:bg-app-surface-muted hover:text-app-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary"><X className="h-5 w-5" aria-hidden="true" /></button>
          </div>
          <div className="mt-4 -mx-1 flex gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Resume analysis sections">
            {TABS.map((item) => <button key={item.id} id={`scanner-tab-${item.id}`} type="button" role="tab" aria-selected={tab === item.id} aria-controls={`scanner-panel-${item.id}`} tabIndex={tab === item.id ? 0 : -1} onClick={() => setTab(item.id)} onKeyDown={handleTabKeyDown} className={`shrink-0 rounded-md px-3 py-2 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary ${tab === item.id ? "bg-app-primary text-white" : "text-app-ink-2 hover:bg-app-surface-muted"}`}>{item.label}</button>)}
          </div>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
          {((application.scanner_status === "stale" || application.scanner_status === "needs_rescan") && report) && <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-app-warning/30 bg-app-warning-soft px-3 py-3 text-sm text-app-warning" role="alert"><span className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> This analysis is out of date because the CV or job changed.</span><button type="button" onClick={handleScan} disabled={scanning} className="inline-flex items-center gap-1 rounded-md border border-app-warning/40 px-2.5 py-1.5 text-xs font-semibold hover:bg-app-warning/20 disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${scanning ? "animate-spin" : ""}`} aria-hidden="true" />{scanning ? "Analyzing…" : "Analyze again"}</button></div>}
          {(scanError || localScanError) && report && <p className="mb-4 rounded-lg border border-app-danger/30 bg-app-danger-soft px-3 py-3 text-sm text-app-danger" role="alert">{scanError ?? localScanError}</p>}
          {!report ? <EmptyAnalysis application={application} onScan={handleScan} scanning={scanning} scanError={scanError ?? localScanError} /> : <>
            {tab === "overview" && <div id="scanner-panel-overview" role="tabpanel" aria-labelledby="scanner-tab-overview"><Overview report={report} onTab={setTab} /></div>}
            {tab === "job-fit" && <div id="scanner-panel-job-fit" role="tabpanel" aria-labelledby="scanner-tab-job-fit"><JobFit report={report} /></div>}
            {tab === "keywords" && <div id="scanner-panel-keywords" role="tabpanel" aria-labelledby="scanner-tab-keywords"><Keywords report={report} /></div>}
            {tab === "ats" && <div id="scanner-panel-ats" role="tabpanel" aria-labelledby="scanner-tab-ats"><AtsReadiness report={report} /></div>}
            {tab === "quality" && <div id="scanner-panel-quality" role="tabpanel" aria-labelledby="scanner-tab-quality"><Quality report={report} /></div>}
            {tab === "pdf" && <div id="scanner-panel-pdf" role="tabpanel" aria-labelledby="scanner-tab-pdf"><PdfCompatibility report={report} /></div>}
            {onTailor && <button type="button" onClick={onTailor} className="mt-5 inline-flex items-center gap-2 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary"><Sparkles className="h-4 w-4" aria-hidden="true" /> Improve with tailoring</button>}
            {import.meta.env.DEV && <Diagnostics report={report} />}
          </>}
        </div>
      </aside>
    </div>
  );
}
