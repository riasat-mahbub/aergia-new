import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-tailoring-builder-"));
const bundlePath = join(temporaryDirectory, "tailoring-builder-browser.js");
const candidateCssFiles = [join(webRoot, ".output/public/assets"), join(webRoot, "dist/assets")]
  .flatMap((directory) => existsSync(directory)
    ? readdirSync(directory).filter((name) => name.endsWith(".css")).map((name) => join(directory, name))
    : []);
const cssPath = process.env.TAILORING_BUILDER_CSS
  ?? candidateCssFiles.sort((left, right) => statSync(right).mtimeMs - statSync(left).mtimeMs)[0]
  ?? "";
const captureDirectory = process.env.TAILORING_BUILDER_CAPTURE_DIR;
if (captureDirectory) mkdirSync(captureDirectory, { recursive: true });

const entry = `
  import React, { useState } from "react";
  import { createRoot } from "react-dom/client";
  import BuilderPage from ${JSON.stringify(join(webRoot, "src/features/builder/BuilderPage.tsx"))};
  import { useBuilderDocumentStore } from ${JSON.stringify(join(webRoot, "src/features/builder/state/builderDocumentStore.ts"))};

  function Harness() {
    const [route, setRoute] = useState({ cvId: "draft-pending", applicationId: "application-wrong" });
    window.builderHarness = {
      navigate: (cvId, applicationId = null) => setRoute({ cvId, applicationId }),
      snapshot: () => {
        const state = useBuilderDocumentStore.getState();
        return { currentCvId: state.currentCV?.id ?? null, isSaving: state.isSaving, revision: state.currentCV?.revision ?? null };
      },
    };
    return React.createElement(BuilderPage, route);
  }

  window.mountBuilderHarness = () => {
    window.builderRoot = createRoot(document.getElementById("root"));
    window.builderRoot.render(React.createElement(Harness));
  };
  window.unmountBuilderHarness = () => {
    window.builderRoot?.unmount();
    window.builderRoot = null;
  };
  window.mountBuilderHarness();
`;

await build({
  stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
  bundle: true,
  format: "iife",
  platform: "browser",
  outfile: bundlePath,
  alias: { "@": join(webRoot, "src") },
  define: { "import.meta.env.DEV": "false" },
  plugins: [{
    name: "tailoring-builder-browser-mocks",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^@\/features\/cvs$/ }, () => ({ path: "cvs-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^cvs-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        contents: `
          export const fetchCV = (id) => window.__builderMock.fetchCV(id);
          export const updateCV = (id, data) => window.__builderMock.updateCV(id, data);
        `,
      }));

      buildApi.onResolve({ filter: /^@\/features\/applications$/ }, () => ({ path: "applications-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^applications-mock$/, namespace: "builder-test" }, () => ({
        loader: "jsx",
        resolveDir: webRoot,
        contents: `
          import ScannerAnalysisDrawer from ${JSON.stringify(join(webRoot, "src/features/applications/components/ScannerAnalysisDrawer.tsx"))};
          import ScannerJobFitBadge from ${JSON.stringify(join(webRoot, "src/features/applications/components/ScannerJobFitBadge.tsx"))};
          export const createApplication = async () => ({});
          export const deleteApplication = async () => {};
          export const getApplication = (id) => window.__builderMock.getApplication(id);
          export const listApplications = async () => [];
          export const recomputeApplicationRelevance = async () => ({});
          export const scanApplication = (id) => window.__builderMock.scanApplication(id);
          export { ScannerAnalysisDrawer, ScannerJobFitBadge };
          export const updateApplication = async () => ({});
        `,
      }));

      buildApi.onResolve({ filter: /^@\/features\/tailoring$/ }, () => ({ path: "tailoring-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^tailoring-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        contents: `
          export const acceptTailoringDraft = async () => ({});
          export const cancelTailoringSession = async () => ({});
          export const createTailoringSession = async () => ({});
          export const getLatestTailoringSession = async () => ({});
          export const getTailoringSessionStatus = async () => ({});
          export const getTailoringDraftContext = (id) => window.__builderMock.getDraftContext(id);
          export const reevaluateTailoringDraft = (id, request) => window.__builderMock.reevaluate(id, request);
          export const rejectTailoringDraft = async () => ({});
        `,
      }));

      buildApi.onResolve({ filter: /^@tanstack\/react-router$/ }, () => ({ path: "router-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^router-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        contents: `
          export const useNavigate = () => (navigation) => { window.__builderMock.calls.navigations.push(navigation); };
          export const useBlocker = () => ({ status: "idle", proceed() {}, reset() {} });
        `,
      }));

      buildApi.onResolve({ filter: /^motion\/react$/ }, () => ({ path: "motion-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^motion-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        resolveDir: webRoot,
        contents: `import React from "react"; export const motion = { div: React.forwardRef((props, ref) => React.createElement("div", { ...props, ref })) };`,
      }));

      buildApi.onResolve({ filter: /^\.\/components\/BuilderWorkspace$/ }, () => ({ path: "workspace-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^workspace-mock$/, namespace: "builder-test" }, () => ({
        loader: "jsx",
        resolveDir: webRoot,
        contents: `
          import React from "react";
          export default function BuilderWorkspace({ onToggle }) {
            return React.createElement("main", null,
              React.createElement("button", { type: "button", onClick: () => onToggle("section-1") }, "Edit CV"));
          }
        `,
      }));

      buildApi.onResolve({ filter: /^\.\/ExportPDFButton$/ }, () => ({ path: "pdf-button-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^pdf-button-mock$/, namespace: "builder-test" }, () => ({
        loader: "jsx",
        resolveDir: webRoot,
        contents: `import React from "react"; export default function ExportPDFButton() { return React.createElement("button", { type: "button" }, "PDF"); }`,
      }));
      buildApi.onResolve({ filter: /^\.\/PromoteToLibraryButton$/ }, () => ({ path: "promote-button-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^promote-button-mock$/, namespace: "builder-test" }, () => ({
        loader: "jsx",
        resolveDir: webRoot,
        contents: `import React from "react"; export default function PromoteToLibraryButton() { return React.createElement("button", { type: "button" }, "Promote"); }`,
      }));

      buildApi.onResolve({ filter: /^\.\/hooks\/useTemplateManifest$/ }, () => ({ path: "template-hook-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^template-hook-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        contents: `export function useTemplateManifest() { return { templateManifest: null, handleTemplateChange: async () => {} }; }`,
      }));
      buildApi.onResolve({ filter: /^\.\/state\/supportStore$/ }, () => ({ path: "support-store-mock", namespace: "builder-test" }));
      buildApi.onLoad({ filter: /^support-store-mock$/, namespace: "builder-test" }, () => ({
        loader: "js",
        contents: `export const useSupportStore = Object.assign(() => null, { getState: () => ({ ensureLoaded() {} }) });`,
      }));
    },
  }],
});

const browserDriver = String.raw`
import asyncio
from playwright.async_api import async_playwright

BUNDLE_PATH = __import__("sys").argv[1]
CSS_PATH = __import__("sys").argv[2] if len(__import__("sys").argv) > 2 else ""

MOCK_BOOTSTRAP = r"""
(() => {
  const clone = (value) => value == null ? value : JSON.parse(JSON.stringify(value));
  const contexts = new Map();
  const applications = new Map();
  const serverCvs = new Map();
  const contextErrors = new Map();
  const updateErrors = new Map();
  const deferred = new Map();
  const queues = new Map();
  const normalizations = new Map();
  const calls = { contexts: [], applications: [], scans: [], updates: [], reevaluations: [], fetches: [], navigations: [] };
  let serial = 0;

  function deferredRequest() {
    let resolve;
    let reject;
    const promise = new Promise((resolveValue, rejectValue) => { resolve = resolveValue; reject = rejectValue; });
    return { promise, resolve, reject };
  }
  function queueKey(kind, id) { return kind + ":" + id; }
  function queue(kind, id) {
    const key = queueKey(kind, id);
    if (!queues.has(key)) queues.set(key, []);
    return queues.get(key);
  }
  function makeCv(id, revision = 1, sections = null) {
    return {
      id,
      title: "CV " + id,
      description: null,
      template_id: "test-template",
      customizations: {},
      sections: sections ?? [{ id: "section-1", title: "Profile", type: "profile", enabled: true, data: { name: "Synthetic owner" } }],
      extra_metadata: {},
      revision,
      created_at: "2029-01-01T00:00:00Z",
      updated_at: "2029-01-01T00:00:00Z",
    };
  }
  function makeScannerResult(jobFit = 0.94) {
    const zeroBucket = { score: null, scorable_fraction: 0, scorable_weight: 0, total_weight: 0, requirement_count: 0 };
    return {
      schema_version: "scanner-v1",
      created_at: "2029-01-01T00:00:00Z",
      input_fingerprints: { job_description_sha256: "job-hash", cv_content_sha256: "cv-hash", pdf_sha256: null },
      versions: { extractor_version: "test", matcher_version: "test", lexical_version: "test", quality_version: "test", pdf_analysis_version: "test" },
      requirement_extraction: { status: "evaluated", requirements: [], warnings: [] },
      semantic: {
        status: "evaluated", requirements: [], evidence: [],
        summary: {
          status: "available", job_fit: jobFit, scorable_fraction: 1, classified_fraction: 1,
          evidence_scorable_fraction: 1, classification_warning_code: null,
          qualification_fit: { ...zeroBucket }, responsibility_alignment: { ...zeroBucket }, preferred_fit: { ...zeroBucket },
          unclassified_requirement_count: 0, supported_requirement_count: 0, partial_requirement_count: 0,
          not_evidenced_requirement_count: 0, conflicting_requirement_count: 0, unverifiable_requirement_count: 0,
          unverifiable_component_count: 0, supported_count: 0, partial_count: 0, not_evidenced_count: 0,
          conflicting_count: 0, unverifiable_count: 0, required_constraint_conflicts: 0,
        },
      },
      lexical: { status: "evaluated", terms: [], summary: { visibility_score: 1, scorable_fraction: 1, exact_count: 0, normalized_count: 0, variant_count: 0, absent_count: 0, unverifiable_count: 0 } },
      presentation_quality: { status: "evaluated", findings: [], bullet_assessments: [] },
      pdf_recovery: { status: "unavailable", page_count: null, checks: [], summary: null },
    };
  }
  function makeDraftContext(cvId, applicationId, state = "needs_reevaluation", revision = 1, scanner = null) {
    return {
      protocol_version: 10,
      session_id: "session-" + cvId,
      application_id: applicationId,
      draft_cv_id: cvId,
      draft_review: {
        state,
        cv_revision: revision,
        candidate_hash: "a".repeat(64),
        render_basis_hash: "b".repeat(64),
        evaluation_id: state === "current" ? "evaluation-current" : null,
        evaluation: null,
        scanner_result: scanner,
        warnings: [],
        pdf_sha256: scanner ? "c".repeat(64) : null,
        fit_review: null,
        fit_review_applicability: "not_run",
      },
      job: { company: "Owner Company", role: "Senior Engineer", job_url: null, description: "Synthetic job description" },
      scanner_context: { schema_version: "scanner-v1", versions: {}, requirement_extraction: {} },
    };
  }
  function notFound() { return Object.assign(new Error("not found"), { response: { status: 404 } }); }
  function syntheticApplication(id, cvId) {
    return {
      id, user_id: "synthetic-user", cv_id: cvId, company: "Synthetic Company", role: "Engineer",
      job_url: null, job_description: "Synthetic job description", notes: null, status: "draft",
      relevance: null, relevance_updated_at: null, scanner_status: "current",
      scanner_result: makeScannerResult(0.88),
      created_at: "2029-01-01T00:00:00Z", updated_at: "2029-01-01T00:00:00Z", history: [],
    };
  }
  function setupCv(id, revision = 1) { serverCvs.set(id, makeCv(id, revision)); }
  ["draft-pending", "draft-noop-failure", "ordinary-unlinked", "ordinary-linked", "draft-delete", "draft-late-save", "draft-late-target", "draft-late-failure", "draft-fetch-B", "context-late", "fetch-A", "fetch-B"].forEach((id) => setupCv(id));
  contexts.set("draft-pending", makeDraftContext("draft-pending", "application-owner", "current", 1, makeScannerResult()));
  contexts.set("draft-noop-failure", makeDraftContext("draft-noop-failure", "application-noop", "needs_reevaluation", 1, makeScannerResult()));
  contexts.set("draft-delete", makeDraftContext("draft-delete", "application-delete", "needs_reevaluation", 1));
  contexts.set("draft-late-save", makeDraftContext("draft-late-save", "application-late", "needs_reevaluation", 1));
  contexts.set("draft-late-target", makeDraftContext("draft-late-target", "application-target", "needs_reevaluation", 1));
  contexts.set("draft-late-failure", makeDraftContext("draft-late-failure", "application-late-failure", "needs_reevaluation", 1));
  contexts.set("draft-fetch-B", makeDraftContext("draft-fetch-B", "application-fetch-B", "needs_reevaluation", 1));
  contexts.set("fetch-B", makeDraftContext("fetch-B", "application-fetch-B", "needs_reevaluation", 1));
  contexts.set("context-late", makeDraftContext("context-late", "application-context-late", "needs_reevaluation", 1));
  applications.set("application-wrong", syntheticApplication("application-wrong", "draft-pending"));
  applications.set("application-linked", syntheticApplication("application-linked", "ordinary-linked"));
  applications.get("application-linked").scanner_result = null;
  applications.get("application-linked").scanner_status = "not_scanned";

  window.__builderMock = {
    calls,
    makeCv,
    makeDraftContext,
    setDraftContext(id, value) { contextErrors.delete(id); contexts.set(id, clone(value)); },
    setDraftContextError(id, status = 404) { contexts.delete(id); contextErrors.set(id, status); },
    setApplication(id, value) { applications.set(id, clone(value)); },
    setServerRevision(id, revision) {
      const current = serverCvs.get(id) ?? makeCv(id);
      current.revision = revision;
      serverCvs.set(id, current);
    },
    setUpdateFailureOnce(id, status = 500) { updateErrors.set(id, status); },
    setReviewNormalization(sessionId, revisions = 1) { normalizations.set(sessionId, revisions); },
    defer(kind, id) {
      const token = kind + ":" + id + ":" + (++serial);
      deferred.set(token, deferredRequest());
      queue(kind, id).push(token);
      return token;
    },
    resolve(token, value) {
      const request = deferred.get(token);
      if (!request) throw new Error("Unknown deferred request: " + token);
      deferred.delete(token);
      request.resolve(value);
    },
    reject(token, error) {
      const request = deferred.get(token);
      if (!request) throw new Error("Unknown deferred request: " + token);
      deferred.delete(token);
      request.reject(error);
    },
    async fetchCV(id) {
      calls.fetches.push(id);
      const token = queue("fetch", id).shift();
      if (token) return deferred.get(token).promise;
      if (!serverCvs.has(id)) setupCv(id);
      return clone(serverCvs.get(id));
    },
    async updateCV(id, data) {
      calls.updates.push({ id, data: clone(data) });
      const token = queue("update", id).shift();
      if (token) {
        const value = await deferred.get(token).promise;
        if (value?.__error) throw Object.assign(new Error(value.message), { response: { status: value.status } });
        serverCvs.set(id, clone(value));
        return clone(value);
      }
      if (updateErrors.has(id)) {
        const status = updateErrors.get(id);
        updateErrors.delete(id);
        throw Object.assign(new Error("synthetic save failure"), { response: { status } });
      }
      const current = serverCvs.get(id) ?? makeCv(id);
      const saved = makeCv(id, current.revision + 1, data.sections ?? current.sections);
      saved.customizations = clone(data.customizations ?? current.customizations);
      if (data.template_id) saved.template_id = data.template_id;
      serverCvs.set(id, saved);
      const context = contexts.get(id);
      if (context) {
        context.draft_review.state = "needs_reevaluation";
        context.draft_review.cv_revision = saved.revision;
        context.draft_review.scanner_result = null;
        context.draft_review.fit_review_applicability = "earlier_version";
      }
      return clone(saved);
    },
    async getDraftContext(id) {
      calls.contexts.push(id);
      const token = queue("context", id).shift();
      if (token) return deferred.get(token).promise;
      if (contextErrors.has(id)) throw Object.assign(new Error("draft context unavailable"), { response: { status: contextErrors.get(id) } });
      if (!contexts.has(id)) throw notFound();
      return clone(contexts.get(id));
    },
    async getApplication(id) {
      calls.applications.push(id);
      if (!applications.has(id)) throw notFound();
      return clone(applications.get(id));
    },
    async scanApplication(id) {
      calls.scans.push(id);
      const application = { ...clone(applications.get(id)), scanner_result: makeScannerResult(), scanner_status: "current" };
      applications.set(id, clone(application));
      return application;
    },
    async reevaluate(sessionId, request) {
      calls.reevaluations.push({ sessionId, request: clone(request) });
      const token = queue("reevaluate", sessionId).shift();
      if (token) return deferred.get(token).promise;
      const cvId = sessionId.slice("session-".length);
      const current = serverCvs.get(cvId) ?? makeCv(cvId, request.expected_cv_revision);
      const revision = request.expected_cv_revision + (normalizations.get(sessionId) ?? 0);
      if (revision > current.revision) {
        const normalized = makeCv(cvId, revision, current.sections.map((section) => ({ ...section, title: "Normalized " + section.title })));
        normalized.customizations = current.customizations;
        serverCvs.set(cvId, normalized);
      }
      const context = contexts.get(cvId);
      if (context) {
        context.draft_review.state = "current";
        context.draft_review.cv_revision = revision;
        context.draft_review.scanner_result = makeScannerResult();
      }
      return {
        protocol_version: 10,
        session_id: sessionId,
        application_id: context?.application_id ?? "application-unknown",
        draft_cv_id: cvId,
        draft_review: {
          state: "current", cv_revision: revision, candidate_hash: "a".repeat(64),
          render_basis_hash: "b".repeat(64), evaluation_id: "evaluation-current", evaluation: null,
          scanner_result: makeScannerResult(), warnings: [],
          pdf_sha256: "c".repeat(64), fit_review: null, fit_review_applicability: "not_run",
        },
        format: "pdf", pdf_base64: "", page_count: 1,
      };
    },
  };
})();
"""

async def flush(page):
    await page.evaluate("() => new Promise((resolve) => requestAnimationFrame(() => resolve()))")

async def navigate(page, cv_id, application_id=None):
    await page.evaluate("([id, applicationId]) => window.builderHarness.navigate(id, applicationId)", [cv_id, application_id])
    await page.get_by_role("heading", name="CV " + cv_id).wait_for()

async def capture(page, filename):
    directory = __import__("os").environ.get("TAILORING_BUILDER_CAPTURE_DIR")
    if directory:
        from pathlib import Path
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(target / filename), full_page=True)

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        await page.set_content('<div id="root"></div>')
        if CSS_PATH:
            from pathlib import Path
            css = Path(CSS_PATH).read_text()
            await page.add_style_tag(content=css)
        await page.evaluate(MOCK_BOOTSTRAP)
        await page.add_script_tag(path=BUNDLE_PATH)
        try:
            await page.get_by_role("heading", name="CV draft-pending").wait_for()
            await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").wait_for()
            assert await page.evaluate("window.__builderMock.calls.applications") == [], "pending context must own application identity even when route search is wrong"
            assert await page.evaluate("window.__builderMock.calls.scans") == [], "draft editor started a source application scan"
            draft_badge = page.get_by_role("button", name="Job Fit 94%")
            await draft_badge.wait_for()
            await capture(page, "pending-builder-desktop.png")
            await draft_badge.click()
            draft_drawer = page.get_by_role("dialog")
            await draft_drawer.get_by_role("heading", name="Owner Company — Senior Engineer").wait_for()
            await capture(page, "pending-scanner-drawer-desktop.png")
            assert await draft_drawer.get_by_text("94%", exact=True).count() > 0, "pending draft result was not rendered in the scanner drawer"
            await draft_drawer.get_by_role("button", name="Close resume analysis").click()
            await page.set_viewport_size({"width": 390, "height": 900})
            await capture(page, "pending-builder-mobile.png")
            await page.get_by_role("button", name="Job Fit 94%").click()
            draft_drawer = page.get_by_role("dialog")
            await draft_drawer.get_by_role("heading", name="Owner Company — Senior Engineer").wait_for()
            await capture(page, "pending-scanner-drawer-mobile.png")
            await draft_drawer.get_by_role("button", name="Close resume analysis").click()
            await page.set_viewport_size({"width": 1280, "height": 900})
            assert await page.get_by_role("button", name="Source scanner application-wrong").count() == 0, "linked source scanner was shown for an unlinked draft"
            await page.get_by_role("button", name="Back").click()
            navigation = await page.evaluate("window.__builderMock.calls.navigations.at(-1)")
            assert navigation == {"to": "/applications/$id", "params": {"id": "application-owner"}}, navigation
            print("PASS pending draft context overrides the unrelated search ID and never shows the source scanner", flush=True)

            await page.get_by_role("button", name="Edit CV").click()
            await page.get_by_text("Unsaved edits. The current review applies to the previously saved draft.").wait_for()
            stale_draft_badge = page.get_by_role("button", name="Job Fit 94% · Update needed")
            await stale_draft_badge.wait_for()
            await page.evaluate("window.__builderMock.setReviewNormalization('session-draft-pending', 1)")
            await stale_draft_badge.click()
            draft_drawer = page.get_by_role("dialog")
            deferred_save = await page.evaluate("window.__builderMock.defer('update', 'draft-pending')")
            update_count_before_review = await page.evaluate("window.__builderMock.calls.updates.length")
            await page.evaluate("() => { const actions = Array.from(document.querySelectorAll('button')).filter((button) => button.textContent.trim() === 'Save and reevaluate draft'); actions.forEach((button) => button.click()); }")
            await page.wait_for_function("window.__builderMock.calls.updates.length > " + str(update_count_before_review))
            assert await page.evaluate("window.__builderMock.calls.updates.length") == update_count_before_review + 1, "two review controls queued duplicate draft saves"
            deferred_saved_cv = await page.evaluate("window.__builderMock.makeCv('draft-pending', 2)")
            await page.evaluate("([token, value]) => window.__builderMock.resolve(token, value)", [deferred_save, deferred_saved_cv])
            await page.get_by_text("Review current for saved draft.").wait_for()
            requests = await page.evaluate("window.__builderMock.calls.reevaluations")
            assert requests[-1] == {"sessionId": "session-draft-pending", "request": {"expected_cv_revision": 2}}, requests
            assert await page.evaluate("window.__builderMock.calls.scans") == [], "draft reevaluation used the source application scanner"
            saved_doc = await page.evaluate("window.builderHarness.snapshot()")
            assert saved_doc["revision"] == 3, saved_doc
            assert await draft_drawer.get_by_text("94%", exact=True).count() > 0
            await draft_drawer.get_by_role("button", name="Close resume analysis").click()
            print("PASS the actual pending scanner drawer renders the draft result and reevaluates the exact normalized saved revision", flush=True)

            await page.get_by_role("button", name="Edit CV").click()
            await page.evaluate("window.__builderMock.setUpdateFailureOnce('draft-pending', 500)")
            before = await page.evaluate("window.__builderMock.calls.reevaluations.length")
            await page.get_by_role("button", name="Save and reevaluate draft").click()
            await page.get_by_text("synthetic save failure").wait_for()
            assert await page.evaluate("window.__builderMock.calls.reevaluations.length") == before, "reevaluation ran after a failed save"
            assert await page.get_by_role("alert").filter(has_text="could not be saved").count() == 1
            await page.get_by_role("button", name="Job Fit 94% · Update needed").wait_for()
            await page.get_by_role("button", name="Save", exact=True).click()
            await page.get_by_role("button", name="Saved!").wait_for()
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.get_by_text("Review current for saved draft.").wait_for()
            requests = await page.evaluate("window.__builderMock.calls.reevaluations")
            assert requests[-1]["request"] == {"expected_cv_revision": 5}, requests[-1]
            print("PASS failed save blocks reevaluation until explicit Save succeeds; reevaluation then receives its exact saved revision", flush=True)

            await navigate(page, "draft-noop-failure")
            await page.evaluate("window.__builderMock.setUpdateFailureOnce('draft-noop-failure', 500)")
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.get_by_text("synthetic save failure").wait_for()
            assert await page.get_by_text("Unsaved", exact=True).count() == 0
            await navigate(page, "ordinary-unlinked")
            await navigate(page, "draft-noop-failure")
            assert await page.get_by_role("alert").count() == 0, "prior-generation save error reappeared after reopening the CV"
            assert await page.get_by_role("button", name="Saved!").count() == 0, "prior-generation saved feedback reappeared after reopening the CV"
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.get_by_text("Review current for saved draft.").wait_for()
            await page.get_by_role("button", name="Edit CV").click()
            await page.get_by_role("button", name="Save", exact=True).click()
            await page.get_by_role("button", name="Saved!").wait_for()
            await navigate(page, "ordinary-unlinked")
            await navigate(page, "draft-noop-failure")
            assert await page.get_by_role("alert").count() == 0
            assert await page.get_by_role("button", name="Saved!").count() == 0, "saved feedback was not cleared at the next route generation"
            print("PASS no-op save errors and saved feedback clear on A→B→A; the reopened generation can review successfully", flush=True)

            await page.evaluate("window.__builderMock.setServerRevision('draft-pending', 7)")
            await navigate(page, "ordinary-unlinked")
            await navigate(page, "draft-pending", "application-wrong")
            await page.get_by_text("This saved draft needs reevaluation.").wait_for()
            await page.get_by_role("button", name="Job Fit 94% · Update needed").wait_for()
            print("PASS a newer saved CV revision makes the prior review and scanner badge stale after reload", flush=True)

            await navigate(page, "ordinary-unlinked")
            assert await page.get_by_role("region", name="Tailoring draft review").count() == 0, "ordinary unlinked CV was presented as a draft"
            assert await page.evaluate("window.__builderMock.calls.applications") == [], "ordinary unlinked CV unexpectedly resolved an application"
            await navigate(page, "ordinary-linked", "application-linked")
            await page.get_by_role("button", name="Analyze CV").wait_for()
            await page.get_by_role("button", name="Analyze CV").click()
            ordinary_drawer = page.get_by_role("dialog")
            await ordinary_drawer.get_by_role("heading", name="Synthetic Company — Engineer").wait_for()
            await ordinary_drawer.get_by_role("button", name="Analyze CV").click()
            await page.wait_for_function("window.__builderMock.calls.scans.includes('application-linked')")
            await ordinary_drawer.get_by_text("94%", exact=True).wait_for()
            await ordinary_drawer.get_by_role("button", name="Close resume analysis").click()
            print("PASS ordinary linked CV keeps its scanner badge, drawer, and scan action", flush=True)

            late_context = await page.evaluate("window.__builderMock.defer('context', 'context-late')")
            await navigate(page, "context-late")
            await page.wait_for_function("window.__builderMock.calls.contexts.includes('context-late')")
            await navigate(page, "ordinary-unlinked")
            await page.evaluate("([token, value]) => window.__builderMock.resolve(token, value)", [late_context, await page.evaluate("window.__builderMock.makeDraftContext('context-late', 'application-context-late')")])
            await flush(page)
            assert await page.get_by_role("region", name="Tailoring draft review").count() == 0, "late draft context rendered after navigation"
            assert await page.evaluate("window.builderHarness.snapshot().currentCvId") == "ordinary-unlinked"
            print("PASS late context response is fenced after navigation", flush=True)

            await navigate(page, "draft-delete")
            await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").wait_for()
            await page.evaluate("window.__builderMock.setDraftContextError('draft-delete', 404)")
            before = await page.evaluate("window.__builderMock.calls.reevaluations.length")
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.get_by_text("This tailoring draft is no longer available.").wait_for()
            assert await page.evaluate("window.__builderMock.calls.reevaluations.length") == before, "deleted draft was reevaluated"
            print("PASS deleted draft is surfaced as unavailable and is never reevaluated", flush=True)

            late_update = await page.evaluate("window.__builderMock.defer('update', 'draft-late-save')")
            await navigate(page, "draft-late-save")
            await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").wait_for()
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.wait_for_function("window.__builderMock.calls.updates.some((request) => request.id === 'draft-late-save')")
            await navigate(page, "draft-late-target")
            await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").wait_for()
            late_update_cv = await page.evaluate("window.__builderMock.makeCv('draft-late-save', 2)")
            await page.evaluate("([token, value]) => window.__builderMock.resolve(token, value)", [late_update, late_update_cv])
            await flush(page)
            assert await page.get_by_role("heading", name="CV draft-late-target").is_visible()
            assert await page.evaluate("window.__builderMock.calls.reevaluations.some((request) => request.sessionId === 'session-draft-late-save')") is False
            assert await page.evaluate("window.builderHarness.snapshot().currentCvId") == "draft-late-target"
            assert await page.evaluate("window.builderHarness.snapshot().isSaving") is False
            print("PASS save completion after navigation cannot reevaluate or mutate the new builder's save state", flush=True)

            late_failure = await page.evaluate("window.__builderMock.defer('update', 'draft-late-failure')")
            await navigate(page, "draft-late-failure")
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.wait_for_function("window.__builderMock.calls.updates.some((request) => request.id === 'draft-late-failure')")
            await navigate(page, "ordinary-unlinked")
            await navigate(page, "draft-late-failure")
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            before_failure_request = await page.evaluate("window.__builderMock.calls.reevaluations.filter((request) => request.sessionId === 'session-draft-late-failure').length")
            await page.evaluate("([token, value]) => window.__builderMock.resolve(token, value)", [late_failure, {"__error": True, "status": 500, "message": "late old-generation failure"}])
            await page.wait_for_function("window.__builderMock.calls.reevaluations.filter((request) => request.sessionId === 'session-draft-late-failure').length > " + str(before_failure_request))
            await page.get_by_text("Review current for saved draft.").wait_for()
            failure_requests = await page.evaluate("window.__builderMock.calls.reevaluations.filter((request) => request.sessionId === 'session-draft-late-failure')")
            assert len(failure_requests) == 1, failure_requests
            print("PASS a late old-generation save failure does not poison or unlock the reopened CV's serialized review save", flush=True)

            late_fetch = await page.evaluate("window.__builderMock.defer('fetch', 'fetch-A')")
            await page.evaluate("window.builderHarness.navigate('fetch-A', null)")
            await page.wait_for_function("window.__builderMock.calls.fetches.includes('fetch-A')")
            await navigate(page, "fetch-B")
            await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").wait_for()
            late_cv = await page.evaluate("window.__builderMock.makeCv('fetch-A', 9)")
            await page.evaluate("([token, value]) => window.__builderMock.resolve(token, value)", [late_fetch, late_cv])
            await flush(page)
            assert await page.evaluate("window.builderHarness.snapshot().currentCvId") == "fetch-B"
            assert await page.get_by_role("heading", name="CV fetch-B").is_visible()
            assert await page.get_by_role("heading", name="Tailored draft for Senior Engineer at Owner Company").is_visible()
            print("PASS late old CV fetch cannot replace or invalidate the newly loaded pending draft", flush=True)
        finally:
            await browser.close()

asyncio.run(main())
`;

try {
  const python = join(repositoryRoot, "api/.venv/bin/python");
  const result = spawnSync(python, ["-c", browserDriver, bundlePath, cssPath], {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: "inherit",
    timeout: 120000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Browser builder harness exited with status ${result.status ?? "unknown"}`);
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
