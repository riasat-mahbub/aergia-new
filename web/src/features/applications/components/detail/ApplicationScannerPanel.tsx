import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { CVListItem } from "@/features/cvs";
import type {
  Application,
  ScanResult,
  ScannerExpressionEvaluation,
  ScannerExpressionNode,
  ScannerRequirement,
} from "@/features/applications/types";

interface ApplicationScannerPanelProps {
  application: Application;
  availableCVs: CVListItem[];
  cvListLoading: boolean;
  onLinkCV: (cvId: string | null) => Promise<unknown>;
  onScan: () => Promise<unknown>;
}

function labelFor(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function percentage(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

function statusTone(value: string): string {
  if (value === "supported" || value === "pass" || value === "evaluated") {
    return "border-app-primary/30 bg-app-primary-soft text-app-primary";
  }
  if (value === "partial" || value === "warning" || value === "unverifiable") {
    return "border-app-warning/30 bg-app-warning-soft text-app-warning";
  }
  if (value === "conflicting" || value === "fail" || value === "failed") {
    return "border-app-danger/30 bg-app-danger-soft text-app-danger";
  }
  return "border-app-rule bg-app-canvas text-app-ink-3";
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusTone(status)}`}>{labelFor(status)}</span>;
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-app-rule-soft bg-app-canvas p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-app-ink-3">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

interface ExpressionRowProps {
  node: ScannerExpressionNode;
  result: ScannerExpressionEvaluation;
  evidenceById: Map<string, ScanResult["semantic"]["evidence"][number]>;
  relationLabel?: string;
}

function ExpressionRow({ node, result, evidenceById, relationLabel }: ExpressionRowProps) {
  const title = node.concept?.name ?? (
    node.kind === "examples"
      ? "Illustrative examples"
      : node.kind === "all" ? "All of the following" : "Any of the following"
  );
  const evidence = node.kind === "leaf"
    ? result.evidence_ids.flatMap((id) => evidenceById.get(id)?.locations ?? [])
    : [];
  const expressionChildren = node.kind === "examples"
    ? [
        ...(node.subject ? [{ node: node.subject, label: "Umbrella" }] : []),
        ...(node.examples ?? []).map((child) => ({ node: child, label: "Example" })),
      ]
    : (node.children ?? []).map((child) => ({ node: child, label: undefined }));

  return (
    <li className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-app-ink">{title}</span>
        {node.expectation && <span className="text-xs text-app-ink-3">Expectation: {labelFor(node.expectation.kind)}</span>}
        {node.modifiers?.optional && <span className="text-xs text-app-ink-3">Optional</span>}
        {relationLabel && <span className="text-xs text-app-ink-3">{relationLabel}</span>}
        {node.kind === "examples" && <span className="text-xs text-app-ink-3">Illustrative list, not separate requirements</span>}
        <StatusBadge status={result.status} />
        {result.mandatory_total > 1 && (
          <span className="text-xs text-app-ink-3">
            {result.mandatory_supported} / {result.mandatory_total} fully supported
          </span>
        )}
      </div>
      {evidence.length > 0 && (
        <ul className="mt-2 space-y-1 border-l-2 border-app-rule pl-3">
          {evidence.map((location, index) => (
            <li key={`${location.field_path}-${index}`} className="text-xs leading-5 text-app-ink-2">
              <span>“{location.excerpt}”</span>
              <span className="ml-1 text-app-ink-3">({location.section_type ?? "CV"})</span>
            </li>
          ))}
        </ul>
      )}
      {expressionChildren.length > 0 && (
        <ul className="mt-2 space-y-2 border-l border-app-rule pl-3">
          {expressionChildren.map(({ node: child, label }, index) => {
            const childResult = result.children[index];
            if (!childResult) return null;
            return <ExpressionRow key={child.id} node={child} result={childResult} evidenceById={evidenceById} relationLabel={label} />;
          })}
        </ul>
      )}
    </li>
  );
}

function JobFit({ result }: { result: ScanResult }) {
  const { requirement_extraction: extraction, semantic } = result;
  const evaluationById = new Map(semantic.requirements.map((item) => [item.requirement_id, item]));
  const evidenceById = new Map(semantic.evidence.map((item) => [item.id, item]));
  const summary = semantic.summary;
  const supportedRequirements = summary?.supported_requirement_count ?? summary?.supported_count ?? 0;
  const partialRequirements = summary?.partial_requirement_count ?? summary?.partial_count ?? 0;
  const notEvidencedRequirements = summary?.not_evidenced_requirement_count ?? summary?.not_evidenced_count ?? 0;
  const conflictingRequirements = summary?.conflicting_requirement_count ?? summary?.conflicting_count ?? 0;
  const unverifiableRequirements = summary?.unverifiable_requirement_count ?? summary?.unverifiable_count ?? 0;
  const evidenceScorableFraction = summary?.evidence_scorable_fraction ?? summary?.scorable_fraction;

  return (
    <SectionCard title="Job fit">
      {extraction.status === "failed" && <p className="text-sm text-app-danger">Requirement extraction failed for this scan.</p>}
      {extraction.warnings.length > 0 && <p className="mb-3 text-xs text-app-warning">{extraction.warnings.join(" · ")}</p>}
      {semantic.status !== "evaluated" && <p className="text-sm text-app-ink-2">Semantic analysis: {labelFor(semantic.status)}.</p>}
      {summary && (
        <div className="mb-4 rounded-md border border-app-rule-soft bg-app-surface p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-lg font-semibold text-app-ink">
              {summary.status === "available" && summary.job_fit !== null
                ? `Job Fit ${percentage(summary.job_fit)}`
                : summary.status === "insufficient_scorable_evidence"
                  ? "Insufficient scorable evidence"
                  : "Job Fit unavailable"}
            </p>
            <span className="text-xs text-app-ink-3">
              {summary.classified_fraction === null || summary.classified_fraction === undefined
                ? "Classification coverage unavailable"
                : `${percentage(summary.classified_fraction)} classified`}
              {" · "}
              {percentage(evidenceScorableFraction)} evaluable from CV
            </span>
          </div>
          <p className="mt-1 text-xs text-app-ink-3">
            {supportedRequirements} supported requirements · {partialRequirements} partial · {notEvidencedRequirements} not evidenced · {conflictingRequirements} conflicting · {unverifiableRequirements} unverifiable requirements
          </p>
          {summary.unverifiable_component_count !== null && summary.unverifiable_component_count !== undefined && (
            <p className="mt-1 text-xs text-app-ink-3">
              {summary.unverifiable_component_count} unverifiable components
            </p>
          )}
          <p className="mt-1 text-xs text-app-ink-3">Category weights: 70% qualifications, 25% responsibilities, 5% preferred. Empty categories are redistributed.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {[
              { title: "Core qualifications", bucket: summary.qualification_fit },
              { title: "Responsibility alignment", bucket: summary.responsibility_alignment },
              { title: "Preferred fit", bucket: summary.preferred_fit },
            ].map(({ title, bucket }) => {
              return (
                <div key={title} className="rounded border border-app-rule-soft px-2.5 py-2">
                  <p className="text-xs text-app-ink-3">{title}</p>
                  <p className="text-sm font-medium text-app-ink">{bucket.total_weight > 0 ? percentage(bucket.score) : "No requirements"}</p>
                  {bucket.total_weight > 0 && <p className="text-xs text-app-ink-3">{percentage(bucket.scorable_fraction)} scorable</p>}
                </div>
              );
            })}
          </div>
          {(summary.unclassified_requirement_count > 0 || summary.required_constraint_conflicts > 0) && (
            <p className="mt-2 text-xs text-app-ink-2">
              {summary.unclassified_requirement_count > 0 && `${summary.unclassified_requirement_count} unclassified requirement${summary.unclassified_requirement_count === 1 ? "" : "s"}`}
              {summary.unclassified_requirement_count > 0 && summary.required_constraint_conflicts > 0 && " · "}
              {summary.required_constraint_conflicts > 0 && `${summary.required_constraint_conflicts} required constraint conflict${summary.required_constraint_conflicts === 1 ? "" : "s"}`}
            </p>
          )}
        </div>
      )}
      {extraction.requirements.length > 0 ? (
        <ul className="space-y-3">
          {extraction.requirements.map((requirement: ScannerRequirement) => {
            const evaluation = evaluationById.get(requirement.id);
            return (
              <li key={requirement.id} className="rounded-md border border-app-rule-soft bg-app-surface p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="max-w-3xl text-sm leading-5 text-app-ink">{requirement.source.original_text}</p>
                  <span className="shrink-0 text-xs text-app-ink-3">
                    {labelFor(requirement.importance)}
                    {requirement.source.section && ` · ${requirement.source.section.title ?? labelFor(requirement.source.section.purpose)}`}
                  </span>
                </div>
                {evaluation ? (
                  <div className="mt-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <StatusBadge status={evaluation.status} />
                      {evaluation.expression.mandatory_total > 1 && (
                        <span className="text-xs text-app-ink-3">
                          {evaluation.expression.mandatory_supported} / {evaluation.expression.mandatory_total} mandatory components fully supported
                        </span>
                      )}
                    </div>
                    <ul className="space-y-2 border-l border-app-rule pl-3">
                      <ExpressionRow node={requirement.expression} result={evaluation.expression} evidenceById={evidenceById} />
                    </ul>
                  </div>
                ) : <p className="mt-2 text-xs text-app-ink-3">No semantic result for this requirement.</p>}
              </li>
            );
          })}
        </ul>
      ) : extraction.status !== "failed" ? <p className="text-sm text-app-ink-2">No candidate-facing requirements were extracted.</p> : null}
    </SectionCard>
  );
}

function LexicalAnalysis({ result }: { result: ScanResult }) {
  const lexical = result.lexical;
  return (
    <SectionCard title="ATS / keywords">
      {lexical.status !== "evaluated" && <p className="mb-3 text-sm text-app-ink-2">Lexical analysis: {labelFor(lexical.status)}.</p>}
      {lexical.summary && (
        <div className="mb-4 rounded-md border border-app-rule-soft bg-app-surface p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-lg font-semibold text-app-ink">
              {lexical.summary.visibility_score === null ? "Term Visibility unavailable" : `Term Visibility ${percentage(lexical.summary.visibility_score)}`}
            </p>
            <span className="text-xs text-app-ink-3">{percentage(lexical.summary.scorable_fraction)} scorable</span>
          </div>
          <p className="mt-1 text-xs text-app-ink-3">
            {lexical.summary.exact_count} exact · {lexical.summary.normalized_count} normalized · {lexical.summary.variant_count} variant · {lexical.summary.absent_count} absent
          </p>
        </div>
      )}
      {lexical.terms.length > 0 ? (
        <ul className="space-y-2">
          {lexical.terms.map((term) => (
            <li key={term.id} className="flex flex-wrap items-start justify-between gap-2 border-b border-app-rule-soft pb-2 last:border-0 last:pb-0">
              <div>
                <p className="text-sm font-medium text-app-ink">{term.term}</p>
                {(term.evidence.length > 0 || term.importance !== "unknown") && (
                  <p className="mt-1 text-xs text-app-ink-3">
                    {term.importance !== "unknown" && `${labelFor(term.importance)} · `}
                    {term.evidence.map((item) => `Found as “${item.matched_text}”`).join(" · ")}
                  </p>
                )}
                {term.visibility === "absent" && term.semantic_support && (
                  <p className="mt-1 text-xs text-app-ink-2">
                    {term.semantic_support === "supported" || term.semantic_support === "partial"
                      ? `Relevant CV evidence is ${term.semantic_support}; the employer’s wording is absent.`
                      : term.semantic_support === "not_evidenced"
                        ? "Wording is absent and this CV does not currently evidence the capability; do not add it without support."
                        : term.semantic_support === "conflicting"
                          ? "Wording is absent and the available evidence conflicts with this requirement."
                          : "Wording is absent and semantic evidence could not be assessed."}
                  </p>
                )}
              </div>
              <StatusBadge status={term.visibility} />
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-app-ink-2">No candidate-facing terms were extracted.</p>}
    </SectionCard>
  );
}

function PresentationQuality({ result }: { result: ScanResult }) {
  const quality = result.presentation_quality;
  const counts = quality.findings.reduce<{ error: number; warning: number; info: number }>(
    (total, finding) => ({ ...total, [finding.severity]: total[finding.severity] + 1 }),
    { error: 0, warning: 0, info: 0 },
  );
  return (
    <SectionCard title="Resume quality">
      {quality.status !== "evaluated" && <p className="mb-3 text-sm text-app-ink-2">Presentation analysis: {labelFor(quality.status)}.</p>}
      <p className="mb-3 text-xs text-app-ink-3">{counts.error} errors · {counts.warning} warnings · {counts.info} informational findings</p>
      {quality.findings.length > 0 ? (
        <ul className="space-y-2">
          {quality.findings.map((finding, index) => (
            <li key={`${finding.code}-${index}`} className="rounded border border-app-rule-soft bg-app-surface p-2.5">
              <div className="flex flex-wrap items-center gap-2"><StatusBadge status={finding.severity} /><span className="text-xs font-medium text-app-ink">{labelFor(finding.code)}</span></div>
              <p className="mt-1 text-sm text-app-ink-2">{finding.explanation}</p>
              {finding.evidence && <p className="mt-1 text-xs text-app-ink-3">“{finding.evidence}”</p>}
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-app-ink-2">No presentation findings.</p>}
      {quality.bullet_assessments.length > 0 && (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-medium text-app-primary">Bullet evidence classifications ({quality.bullet_assessments.length})</summary>
          <ul className="mt-2 space-y-2">
            {quality.bullet_assessments.map((item, index) => (
              <li key={`${item.location.field_path}-${index}`} className="text-xs leading-5 text-app-ink-2">
                <span>{labelFor(item.classification)}</span>
                <span className="block text-app-ink-3">{item.location.excerpt}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </SectionCard>
  );
}

function PDFRecovery({ result }: { result: ScanResult }) {
  const pdf = result.pdf_recovery;
  return (
    <SectionCard title="PDF text recovery">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={pdf.status} />
        {pdf.summary?.recovery_score !== null && pdf.summary?.recovery_score !== undefined && (
          <span className="text-sm font-semibold text-app-ink">{percentage(pdf.summary.recovery_score)} recovery</span>
        )}
        {pdf.page_count !== null && <span className="text-xs text-app-ink-3">{pdf.page_count} page{pdf.page_count === 1 ? "" : "s"}</span>}
      </div>
      {pdf.summary && (
        <p className="mt-1 text-xs text-app-ink-3">
          {pdf.summary.recovery_score === null ? "Numeric recovery score unavailable" : `${pdf.summary.scored_check_count} checks scored · ${percentage(pdf.summary.scorable_fraction)} scorable coverage`}
        </p>
      )}
      <p className="mt-2 text-xs text-app-ink-3">Checks what Aergia recovered from this PDF; it does not guarantee behavior in every ATS.</p>
      {pdf.checks.length > 0 && (
        <ul className="mt-3 space-y-2">
          {pdf.checks.map((check) => (
            <li key={check.code} className="flex flex-wrap items-start justify-between gap-2 border-b border-app-rule-soft pb-2 last:border-0 last:pb-0">
              <div>
                <p className="text-sm font-medium text-app-ink">{labelFor(check.code)}</p>
                {check.explanation && <p className="mt-1 text-xs text-app-ink-3">{check.explanation}</p>}
                {check.evidence.length > 0 && <p className="mt-1 text-xs text-app-ink-3">{check.evidence.join(" · ")}</p>}
              </div>
              <div className="flex items-center gap-2"><StatusBadge status={check.status} />{check.expected_count !== null && check.recovered_count !== null && <span className="text-xs text-app-ink-3">{check.recovered_count}/{check.expected_count}</span>}</div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export default function ApplicationScannerPanel({
  application,
  availableCVs,
  cvListLoading,
  onLinkCV,
  onScan,
}: ApplicationScannerPanelProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [isLinkingCV, setIsLinkingCV] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const result = application.scanner_result ?? null;
  const linkableCVs = availableCVs.filter(
    (cv) => cv.id === application.cv_id || !cv.application || cv.application.id === application.id,
  );

  const handleScan = async () => {
    setIsScanning(true);
    setError(null);
    try {
      await onScan();
    } catch {
      setError("Unable to run the scanner. Please try again.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleCVChange = async (cvId: string) => {
    setIsLinkingCV(true);
    setLinkError(null);
    try {
      await onLinkCV(cvId || null);
    } catch {
      setLinkError("Unable to update the linked CV.");
    } finally {
      setIsLinkingCV(false);
    }
  };

  return (
    <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Scanner analysis</h2>
          <p className="mt-1 text-xs text-app-ink-3">Job fit, term visibility, presentation quality, and PDF recovery are reported separately.</p>
          {result && <p className="mt-1 text-xs text-app-ink-3">Last run: {new Date(result.created_at).toLocaleString()}</p>}
        </div>
        <button
          type="button"
          onClick={handleScan}
          disabled={!application.cv_id || isScanning}
          className="inline-flex items-center gap-2 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isScanning ? "animate-spin" : ""}`} />
          {isScanning ? "Scanning…" : result ? "Run scanner again" : "Run scanner"}
        </button>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label htmlFor="application-scanner-cv" className="text-sm font-medium text-app-ink-2">CV used for this scan</label>
        <select
          id="application-scanner-cv"
          value={application.cv_id ?? ""}
          disabled={cvListLoading || isLinkingCV}
          onChange={(event) => handleCVChange(event.target.value)}
          className="min-w-56 max-w-full rounded-md border border-app-rule-strong bg-app-surface px-3 py-2 text-sm disabled:opacity-50"
        >
          <option value="">No CV linked</option>
          {linkableCVs.map((cv) => <option key={cv.id} value={cv.id}>{cv.title}</option>)}
        </select>
        {isLinkingCV && <span className="text-xs text-app-ink-3" role="status">Updating link…</span>}
        {!cvListLoading && linkableCVs.length === 0 && <span className="text-xs text-app-ink-3">No unassigned CVs are available to link.</span>}
      </div>
      {linkError && <p role="alert" className="mt-2 text-sm text-app-danger">{linkError}</p>}
      {error && <p role="alert" className="mt-3 rounded-md bg-app-danger-soft px-3 py-2 text-sm text-app-danger">{error}</p>}
      {!application.cv_id && <p className="mt-3 text-sm text-app-ink-2">Link a CV to this application before running the scanner.</p>}
      {!result && application.cv_id && <p className="mt-3 text-sm text-app-ink-2">No scanner result yet. Run the scanner to evaluate the linked CV against this job description.</p>}
      {result && (
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          <JobFit result={result} />
          <LexicalAnalysis result={result} />
          <PresentationQuality result={result} />
          <PDFRecovery result={result} />
        </div>
      )}
    </section>
  );
}
