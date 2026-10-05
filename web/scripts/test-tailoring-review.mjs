import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-tailoring-review-"));
const bundlePath = join(temporaryDirectory, "tailoring-review-browser.js");
const captureDirectory = process.env.TAILORING_REVIEW_CAPTURE_DIR ?? "";
const assetsDirectory = join(webRoot, ".output/public/assets");
const builtCss = process.env.TAILORING_REVIEW_CSS
  ?? (existsSync(assetsDirectory)
    ? readdirSync(assetsDirectory).filter((file) => /^index-.*\.css$/.test(file)).sort().at(-1)
      ? join(assetsDirectory, readdirSync(assetsDirectory).filter((file) => /^index-.*\.css$/.test(file)).sort().at(-1))
      : ""
    : "");

const entry = `
  import React, { useCallback, useState } from "react";
  import { createRoot } from "react-dom/client";
  import ApplicationCvPanel from ${JSON.stringify(join(webRoot, "src/features/applications/components/detail/ApplicationCvPanel.tsx"))};
  import { useTailoringSession } from ${JSON.stringify(join(webRoot, "src/features/tailoring/hooks/useTailoringSession.ts"))};

  let root = null;
  function Harness() {
    const [applicationId, setApplicationId] = useState("application-A");
    const addToast = useCallback((message, type) => {
      window.__tailoringReviewMock.toasts.push({ message, type });
    }, []);
    const fetchApplication = useCallback(async (id) => {
      window.__tailoringReviewMock.applicationRefreshes.push(id);
    }, []);
    const tailoring = useTailoringSession({ applicationId, addToast, fetchApplication });
    window.tailoringReviewHarness = {
      changeApplication: setApplicationId,
      reevaluateDraft: tailoring.reevaluateDraft,
      acceptDraft: tailoring.acceptDraft,
      discardDraft: tailoring.rejectDraft,
      snapshot: () => ({
        applicationId,
        sessionId: tailoring.tailoringSession?.session_id ?? null,
        status: tailoring.tailoringStatus?.status ?? null,
        reviewState: tailoring.tailoringStatus?.draft_review?.state ?? null,
        action: tailoring.tailoringAction,
      }),
    };
    const application = {
      id: applicationId,
      user_id: "synthetic-user",
      cv_id: null,
      company: "Example Company",
      role: "Example Engineer",
      job_url: null,
      job_description: "Synthetic job description for review interface tests.",
      notes: null,
      status: "draft",
      relevance: null,
      relevance_updated_at: null,
      created_at: "2029-01-01T00:00:00Z",
      updated_at: "2029-01-01T00:00:00Z",
      history: [],
    };
    return React.createElement(ApplicationCvPanel, {
      application,
      linkedCV: null,
      sections: [],
      sourceCount: null,
      tailoringSession: tailoring.tailoringSession,
      tailoringStarting: tailoring.tailoringStarting,
      tailoringStatus: tailoring.tailoringStatus,
      tailoringResult: tailoring.tailoringResult,
      promptCopied: tailoring.promptCopied,
      tailoringAction: tailoring.tailoringAction,
      tailoringActionError: tailoring.tailoringActionError,
      onExport: () => {},
      onStartTailoring: tailoring.startTailoring,
      onCopyPrompt: tailoring.copyPrompt,
      onCancelTailoring: tailoring.cancelTailoring,
      onReevaluateDraft: tailoring.reevaluateDraft,
      onAcceptDraft: tailoring.acceptDraft,
      onDiscardDraft: tailoring.rejectDraft,
    });
  }

  window.mountTailoringReviewHarness = () => {
    root = createRoot(document.getElementById("root"));
    root.render(React.createElement(Harness));
  };
  window.mountTailoringReviewHarness();
`;

await build({
  stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
  bundle: true,
  format: "iife",
  platform: "browser",
  outfile: bundlePath,
  alias: { "@": join(webRoot, "src") },
  plugins: [{
    name: "tailoring-review-browser-mocks",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^\.\.\/api\/tailoring$/ }, () => ({
        path: "tailoring-api-mock",
        namespace: "tailoring-review-test",
      }));
      buildApi.onLoad({ filter: /^tailoring-api-mock$/, namespace: "tailoring-review-test" }, () => ({
        loader: "js",
        contents: `
          export const acceptTailoringDraft = (id, request) => window.__tailoringReviewMock.call("accept", id, request);
          export const cancelTailoringSession = (id) => window.__tailoringReviewMock.call("cancel", id);
          export const createTailoringSession = (id) => window.__tailoringReviewMock.call("create", id);
          export const getLatestTailoringSession = (id) => window.__tailoringReviewMock.call("latest", id);
          export const getTailoringSessionStatus = (id) => window.__tailoringReviewMock.call("status", id);
          export const reevaluateTailoringDraft = (id, request) => window.__tailoringReviewMock.call("reevaluate", id, request);
          export const rejectTailoringDraft = (id) => window.__tailoringReviewMock.call("discard", id);
        `,
      }));
      buildApi.onResolve({ filter: /^@tanstack\/react-router$/ }, () => ({
        path: "router-link-mock",
        namespace: "tailoring-review-test",
      }));
      buildApi.onLoad({ filter: /^router-link-mock$/, namespace: "tailoring-review-test" }, () => ({
        loader: "jsx",
        resolveDir: webRoot,
        contents: `
          import React from "react";
          export function Link({ to, params = {}, children, ...props }) {
            const href = String(to).replace(/\\$([A-Za-z][A-Za-z0-9_]*)/g, (_match, key) => params[key] ?? "");
            return React.createElement("a", { href, ...props }, children);
          }
        `,
      }));
    },
  }],
});

const browserDriver = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BUNDLE_PATH = sys.argv[1]
CAPTURE_DIRECTORY = sys.argv[2]
CSS_PATH = sys.argv[3]

MOCK_BOOTSTRAP = r"""
(() => {
  const pending = new Map();
  const deferredQueues = new Map();
  const latest = new Map();
  const statuses = new Map();
  const reevaluations = new Map();
  const accepts = new Map();
  const discards = new Map();
  const creates = new Map();
  const acceptErrors = new Map();
  const reevaluateErrors = new Map();
  let serial = 0;
  function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
  }
  function key(kind, id) { return kind + ":" + id; }
  function queueKey(kind, id) {
    const entry = key(kind, id);
    if (!deferredQueues.has(entry)) deferredQueues.set(entry, []);
    return deferredQueues.get(entry);
  }
  function takeDeferred(kind, id) {
    const token = queueKey(kind, id).shift();
    return token ? pending.get(token).promise : null;
  }
  function outcome(map, id, fallback) {
    const token = takeDeferred("unused", id);
    if (token) return token;
    const value = map.get(id);
    if (value && value.__error) {
      map.delete(id);
      return Promise.reject(value.__error);
    }
    return Promise.resolve(value ?? fallback());
  }
  const calls = { latest: [], status: [], reevaluate: [], accept: [], discard: [], create: [], cancel: [] };
  const requests = { reevaluate: [], accept: [] };
  window.__tailoringReviewMock = {
    calls,
    requests,
    toasts: [],
    applicationRefreshes: [],
    setLatest(appId, value) { latest.set(appId, value); },
    setStatus(sessionId, value) { statuses.set(sessionId, value); },
    setReevaluation(sessionId, value) { reevaluations.set(sessionId, value); },
    setAccept(sessionId, value) { accepts.set(sessionId, value); },
    setAcceptError(sessionId, value) { acceptErrors.set(sessionId, { __error: value }); },
    setReevaluationError(sessionId, value) { reevaluateErrors.set(sessionId, { __error: value }); },
    setDiscard(sessionId, value) { discards.set(sessionId, value); },
    setCreate(appId, value) { creates.set(appId, value); },
    defer(kind, id) {
      const token = kind + ":" + id + ":" + (++serial);
      pending.set(token, deferred());
      queueKey(kind, id).push(token);
      return token;
    },
    resolve(token, value) {
      const request = pending.get(token);
      if (!request) throw new Error("Unknown deferred request: " + token);
      pending.delete(token);
      request.resolve(value);
    },
    reject(token, error) {
      const request = pending.get(token);
      if (!request) throw new Error("Unknown deferred request: " + token);
      pending.delete(token);
      request.reject(error);
    },
    call(kind, id, request) {
      calls[kind].push(id);
      if (kind === "reevaluate" || kind === "accept") requests[kind].push({ sessionId: id, request: request ?? null });
      const waiting = takeDeferred(kind, id);
      if (waiting) return waiting;
      if (kind === "latest") return outcome(latest, id, () => Promise.reject(new Error("404 no session")));
      if (kind === "status") return outcome(statuses, id, () => Promise.reject(new Error("404 no session")));
      if (kind === "reevaluate") {
        if (reevaluateErrors.has(id)) return outcome(reevaluateErrors, id, () => Promise.reject(new Error("missing reevaluation fixture")));
        return outcome(reevaluations, id, () => Promise.reject(new Error("missing reevaluation fixture")));
      }
      if (kind === "accept") return outcome(acceptErrors, id, () => accepts.get(id) ?? { session_id: id, application_id: "application-A", status: "accepted", protocol_version: 10, source_cv_id: null, draft_cv_id: null, cv_id: null, scanner_result: null });
      if (kind === "discard") return outcome(discards, id, () => ({ session_id: id, application_id: "application-A", status: "rejected", protocol_version: 10, source_cv_id: null, draft_cv_id: null, cv_id: null, scanner_result: null }));
      if (kind === "create") return outcome(creates, id, () => Promise.reject(new Error("missing create fixture")));
      return Promise.resolve({});
    },
  };
})();
"""

def issue(identifier, message, *, kind="review", category="requirements", detail=None):
    return {
        "id": identifier,
        "kind": kind,
        "category": category,
        "message": message,
        "detail": detail,
        "priority": "high" if kind in ("risk", "blocker", "review") else "normal",
        "requirement_id": "req-synthetic" if category == "requirements" else None,
        "term_id": None,
        "code": "ATS_SYNTHETIC" if category == "ats" else None,
        "importance": "required" if kind in ("risk", "blocker", "review") else None,
    }

def fit_review(verdict="generic", status_name="completed"):
    base = {
        "version": "fit-review-v1",
        "evaluation_id": "evaluation-fit-synthetic",
        "candidate_hash": "a" * 64,
        "pdf_sha256": "b" * 64,
        "status": status_name,
    }
    if status_name == "completed":
        return {
            **base,
            "mode": "fresh_agent",
            "verdict": verdict,
            "rationale": "The layout is readable, but several statements could fit many roles.",
            "strong_connections": [f"Strong connection {i}" for i in range(5)],
            "weak_or_missing_connections": [f"Weak connection {i}" for i in range(5)],
            "recommended_changes": [f"Recommended change {i}" for i in range(3)],
        }
    return {**base, "reason": "A fresh reviewer could not inspect this PDF in the fixture."}

def evaluation(tag="current"):
    return {
        "version": "tailoring-evaluation-v2",
        "candidate_hash": "a" * 64,
        "source_comparison": {"available": False, "requirement_transitions": [], "keyword_transitions": []},
        "previous_evaluation_comparison": {"available": False, "candidate_hash": "a" * 64, "changes": []},
        "dimensions": {
            "job_fit": {"source": None, "candidate": 0.89},
            "keywords": {"source": None, "candidate": 0.8},
            "ats": {"source_count": None, "candidate_count": 8, "candidate_error_count": 0, "candidate_warning_count": 1, "candidate_info_count": 0},
            "resume_quality": {"source_count": None, "candidate_count": 1, "candidate_error_count": 0, "candidate_warning_count": 1, "candidate_info_count": 0},
            "pdf_recovery": {"source": None, "candidate": 0.95},
        },
        "improvements": [issue(f"improvement-{tag}-{i}", f"Improvement item {tag} {i}", kind="recommendation") for i in range(9)],
        "regressions": [issue(f"regression-{tag}-{i}", f"Regression item {tag} {i}", kind="risk") for i in range(9)],
        "risk_findings": [issue(f"risk-{tag}-{i}", f"Risk finding {tag} {i}", kind="risk") for i in range(9)],
        "review_items": [
            issue(f"review-{tag}-{i}", f"Review item {tag} {i}", kind="review", category="ats" if i == 9 else "requirements", detail="Full scanner detail for this review item.")
            for i in range(10)
        ],
        "recommendations": [issue(f"recommendation-{tag}-{i}", f"Recommendation item {tag} {i}", kind="recommendation") for i in range(7)],
        "non_actionable_gaps": [issue(f"gap-{tag}-{i}", f"Not demonstrated item {tag} {i}", kind="non_actionable_gap") for i in range(7)],
        "render_warnings": [f"Render warning {tag} {i}" for i in range(7)],
    }

def scan_result(tag="current"):
    return {
        "schema_version": "scanner-v1",
        "created_at": "2029-01-01T00:00:00Z",
        "input_fingerprints": {"job_description_sha256": "c" * 64, "cv_content_sha256": "d" * 64, "pdf_sha256": "b" * 64},
        "versions": {"extractor_version": "test", "matcher_version": "test", "lexical_version": "test", "quality_version": "test", "pdf_analysis_version": "test"},
        "requirement_extraction": {"status": "partial", "requirements": [], "warnings": [f"Parser warning {tag}"]},
        "semantic": {"status": "evaluated", "requirements": [], "evidence": [], "summary": {"job_fit": 0.89}},
        "lexical": {"status": "evaluated", "terms": []},
        "presentation_quality": {"status": "evaluated", "findings": [{"code": "layout_wrap", "severity": "warning", "location": None, "evidence": None, "explanation": f"Quality warning {tag}"}], "bullet_assessments": []},
        "pdf_recovery": {"status": "warning", "page_count": 1, "checks": [{"code": "text_order", "status": "warning", "expected_count": 1, "recovered_count": 0, "evidence": [], "missing_items": [f"PDF text warning {tag}"], "explanation": "Check reading order in the exported PDF."}]},
        "ats_guidance": {
            "schema_version": "ats-guidance-v1",
            "version": "test",
            "common_findings": [{"id": "ats-synthetic", "rule_id": "synthetic-rule", "title": f"ATS warning {tag}", "category": "heading", "scope": "common", "severity": "warning", "explanation": "Use a recognizable heading.", "action": "Review the heading.", "affected_items": [], "recovered_items": [], "missing_items": [], "applies_to": [], "source_ids": []}],
            "platform_sensitive_findings": [],
            "platforms": {},
            "heading_conventions": [],
            "date_compatibility": [],
            "acronym_coverage": [],
            "entry_completeness": [],
            "summary": {"platforms_checked": 0, "common_pass_count": 0, "common_warning_count": 1, "recommendation_count": 0, "informational_count": 0},
        },
    }

def draft_review(state="current", *, revision=12, fit=None, applicability="current", tag="current"):
    return {
        "state": state,
        "cv_revision": revision,
        "candidate_hash": "a" * 64 if state != "unavailable" else None,
        "render_basis_hash": "e" * 64 if state == "current" else None,
        "evaluation_id": f"evaluation-owner-{tag}" if state == "current" else None,
        "evaluation": evaluation(tag) if state == "current" else None,
        "scanner_result": scan_result(tag) if state == "current" else None,
        "warnings": [f"Owner render warning {tag} 0", f"Owner render warning {tag} 1"] if state == "current" else [],
        "pdf_sha256": "f" * 64 if state == "current" else None,
        "fit_review": fit,
        "fit_review_applicability": applicability,
    }

def result(protocol=10, *, draft_id="draft-A", fit=None, tag="submitted"):
    data = {
        "protocol_version": protocol,
        "session_id": f"session-{draft_id.removeprefix('draft-')}",
        "application_id": "application-A",
        "status": "draft_ready",
        "source_cv_id": None,
        "draft_cv_id": draft_id,
        "scanner_result": scan_result(tag),
        "evaluation": evaluation(tag),
        "render_warnings": [f"Submitted render warning {tag}"],
        "review_notes": ["Author note: verify the role scope.", "Author note: confirm the project dates."],
    }
    if protocol == 10:
        data.update({"evaluation_id": f"evaluation-agent-{draft_id}", "candidate_hash": "a" * 64, "candidate": {"title": "Example CV", "template_id": "classic", "sections": [], "customizations": {}}, "fit_review": fit})
    elif protocol == 9:
        data.update({"evaluation_id": f"evaluation-agent-{draft_id}", "candidate_hash": "a" * 64, "candidate": {"title": "Example CV", "template_id": "classic", "sections": [], "customizations": {}}})
    return data

def status(app_id, session_id, *, status_name="draft_ready", review=None, result_value=None, protocol=10, draft_id="draft-A"):
    return {
        "protocol_version": protocol,
        "session_id": session_id,
        "application_id": app_id,
        "source_cv_id": None,
        "draft_cv_id": draft_id,
        "cv_id": None,
        "status": status_name,
        "expires_at": "2099-01-01T00:00:00Z",
        "created_at": "2029-01-01T00:00:00Z",
        "exchanged_at": None,
        "submitted_at": "2029-01-01T00:00:00Z" if status_name in ("draft_ready", "stale") else None,
        "reviewed_at": None,
        "updated_at": "2029-01-01T00:00:00Z",
        "attempts": 1,
        "result": result_value,
        "draft_review": review,
    }

def accepted_status(app_id, session_id, protocol=10):
    return status(app_id, session_id, status_name="accepted", review=None, result_value=None, protocol=protocol, draft_id=None)

def session_response(app_id, session_id):
    return {
        "protocol_version": 10,
        "session_id": session_id,
        "application_id": app_id,
        "source_cv_id": None,
        "cv_id": None,
        "code": "fresh-code-synthetic",
        "session_url": f"http://localhost/agent/tailor/{session_id}",
        "skill_url": "https://example.test/tailoring-skill.zip",
        "prompt": "Synthetic one-time prompt for the restarted session.",
        "status": "created",
        "expires_at": "2099-01-01T00:00:00Z",
    }

async def flush_browser(page):
    await page.evaluate("() => new Promise((resolve) => requestAnimationFrame(() => resolve()))")

async def load_status(page, app_id, value):
    await page.evaluate("([appId, value]) => window.__tailoringReviewMock.setLatest(appId, value)", [app_id, value])
    await page.evaluate("(appId) => window.tailoringReviewHarness.changeApplication(appId)", app_id)
    await page.wait_for_function("(appId) => window.tailoringReviewHarness.snapshot().applicationId === appId && window.__tailoringReviewMock.calls.latest.includes(appId)", arg=app_id)
    await page.wait_for_function("(appId) => window.tailoringReviewHarness.snapshot().applicationId === appId && window.tailoringReviewHarness.snapshot().sessionId !== null", arg=app_id)

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(10000)
            await page.set_content('<div id="root"></div>')
            await page.evaluate(MOCK_BOOTSTRAP)
            if CSS_PATH:
                await page.add_style_tag(path=CSS_PATH)
            initial = status("application-A", "session-A", review=draft_review("current", revision=12, fit=fit_review("generic"), tag="current"), result_value=result(fit=fit_review("generic")))
            await page.evaluate("value => window.__tailoringReviewMock.setLatest('application-A', value)", initial)
            await page.add_script_tag(path=BUNDLE_PATH)
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().sessionId === 'session-A'")

            await page.get_by_role("heading", name="Scanner feedback").wait_for()
            assert await page.get_by_text("Current owner review").count() == 1
            assert await page.get_by_text("ATS warning current").count() == 1
            assert await page.get_by_text("Parser warning current").count() == 1
            assert await page.get_by_text("This report is advisory. A generic verdict or warning does not prevent acceptance.").count() == 1
            assert await page.get_by_text("Applies to the current draft · Completed").count() == 1
            assert await page.get_by_text("Author note: verify the role scope.").count() == 1
            await page.get_by_role("button", name="Accept draft").wait_for()
            for label, last_item in [
                ("Risk findings (9)", "Risk finding current 8"),
                ("Required conflicts and review items (10)", "Review item current 9"),
                ("Improvements (9)", "Improvement item current 8"),
                ("Regressions and trade-offs (9)", "Regression item current 8"),
                ("Not demonstrated in this CV (7)", "Not demonstrated item current 6"),
                ("Recommendations (7)", "Recommendation item current 6"),
                ("Render warnings (2)", "Owner render warning current 1"),
            ]:
                summary = page.get_by_text(label, exact=True)
                await summary.focus()
                await page.keyboard.press("Enter")
                assert await page.get_by_text(last_item, exact=True).is_visible(), f"{last_item} was not reachable from {label}"
            for label, last_item in [
                ("Strong connections (5)", "Strong connection 4"),
                ("Weak or missing connections (5)", "Weak connection 4"),
                ("Recommended changes (3)", "Recommended change 2"),
            ]:
                summary = page.get_by_text(label, exact=True)
                await summary.focus()
                await page.keyboard.press("Space")
                assert await page.get_by_text(last_item, exact=True).is_visible(), f"{last_item} was not reachable from {label}"
            assert await page.get_by_text("a" * 64, exact=True).count() == 0, "opaque review bindings leaked into owner UI"
            if CAPTURE_DIRECTORY:
                Path(CAPTURE_DIRECTORY).mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(Path(CAPTURE_DIRECTORY) / "tailoring-review-desktop.png"), full_page=True)
            await page.set_viewport_size({"width": 390, "height": 844})
            if CAPTURE_DIRECTORY:
                await page.screenshot(path=str(Path(CAPTURE_DIRECTORY) / "tailoring-review-mobile.png"), full_page=True)
            assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "review panel overflows the mobile viewport"
            await page.set_viewport_size({"width": 1280, "height": 900})
            print("PASS mounted owner panel: current scanner, full expandable findings, generic fit review, and author notes are reachable", flush=True)

            await page.evaluate("(id) => window.__tailoringReviewMock.setStatus('session-A', id)", accepted_status("application-A", "session-A"))
            acceptToken = await page.evaluate("window.__tailoringReviewMock.defer('accept', 'session-A')")
            await page.get_by_role("button", name="Accept draft").click()
            await page.wait_for_function("window.__tailoringReviewMock.calls.accept.length === 1")
            assert await page.get_by_role("button", name="Discard draft").is_disabled(), "conflicting owner action remained enabled during accept"
            await page.evaluate("() => window.tailoringReviewHarness.acceptDraft()")
            await page.evaluate("([token, result]) => window.__tailoringReviewMock.resolve(token, result)", [acceptToken, {"session_id": "session-A", "application_id": "application-A", "status": "accepted", "protocol_version": 10, "source_cv_id": None, "draft_cv_id": "draft-A", "cv_id": "draft-A", "scanner_result": None}])
            await page.wait_for_function("window.tailoringReviewMock === undefined || window.__tailoringReviewMock.calls.status.includes('session-A')")
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().status === 'accepted'")
            accept_request = await page.evaluate("window.__tailoringReviewMock.requests.accept[0]")
            assert accept_request["request"] == {"expected_cv_revision": 12, "candidate_hash": "a" * 64}, accept_request
            assert await page.evaluate("window.__tailoringReviewMock.calls.accept.length") == 1, "duplicate accept was sent"
            assert await page.evaluate("window.__tailoringReviewMock.applicationRefreshes.includes('application-A')"), "accept did not refresh the current application"
            print("PASS revision-bound accept: sends current revision and candidate hash, suppresses duplicates, and refreshes the application", flush=True)

            edited_result = result(draft_id="draft-B", fit=fit_review("partially_tailored"), tag="submitted-B")
            edited = status("application-B", "session-B", review=draft_review("needs_reevaluation", revision=42, fit=fit_review("partially_tailored"), applicability="earlier_version", tag="submitted-B"), result_value=edited_result, draft_id="draft-B")
            await load_status(page, "application-B", edited)
            assert await page.get_by_text("The saved draft changed after its last review.").count() == 1
            await page.get_by_text("Earlier version · Completed", exact=True).wait_for()
            await page.get_by_role("button", name="Reevaluate saved draft").wait_for()
            await page.evaluate("(value) => window.__tailoringReviewMock.setReevaluationError('session-B', value)", {"response": {"data": {"code": "edited_draft", "detail": "The draft changed while the review was running. Save and retry."}}})
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.get_by_role("alert").filter(has_text="The draft changed while the review was running.").wait_for()
            assert await page.get_by_role("button", name="Reevaluate saved draft").is_enabled(), "reevaluate did not recover after an API conflict"
            current_review = draft_review("current", revision=42, fit=fit_review("partially_tailored"), applicability="earlier_version", tag="owner-B")
            reevaluation_response = {"protocol_version": 10, "session_id": "session-B", "application_id": "application-B", "draft_cv_id": "draft-B", "draft_review": current_review, "format": "pdf", "pdf_base64": "", "page_count": 1}
            await page.evaluate("(value) => window.__tailoringReviewMock.setReevaluation('session-B', value)", reevaluation_response)
            await page.get_by_role("button", name="Reevaluate saved draft").click()
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().reviewState === 'current'")
            reevaluate_request = await page.evaluate("window.__tailoringReviewMock.requests.reevaluate.at(-1)")
            assert reevaluate_request["request"] == {"expected_cv_revision": 42}, reevaluate_request
            assert await page.evaluate("window.__tailoringReviewMock.applicationRefreshes.includes('application-B')"), "reevaluation did not refresh the current application"
            await page.get_by_role("button", name="Accept draft").wait_for()
            await page.evaluate("(value) => window.__tailoringReviewMock.setStatus('session-B', value)", accepted_status("application-B", "session-B"))
            await page.evaluate("(value) => window.__tailoringReviewMock.setAccept('session-B', value)", {"session_id": "session-B", "application_id": "application-B", "status": "accepted", "protocol_version": 10, "source_cv_id": None, "draft_cv_id": "draft-B", "cv_id": "draft-B", "scanner_result": None})
            await page.get_by_role("button", name="Accept draft").click()
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().status === 'accepted'")
            accept_b = await page.evaluate("window.__tailoringReviewMock.requests.accept.at(-1)")
            assert accept_b["request"] == {"expected_cv_revision": 42, "candidate_hash": "a" * 64}, accept_b
            print("PASS edited-draft recovery: saved revision is reevaluated, conflict is accessible, then current review accepts with both exact tokens", flush=True)

            stale_result = result(draft_id="draft-deleted-C", fit=fit_review("generic"), tag="stale-C")
            unavailable = draft_review("unavailable", revision=None, fit=None, applicability="not_run", tag="stale-C")
            stale = status("application-C", "session-C", status_name="stale", review=unavailable, result_value=stale_result, draft_id="draft-deleted-C")
            await load_status(page, "application-C", stale)
            assert await page.get_by_text("This draft is no longer available.").count() == 1
            assert await page.get_by_role("link", name="Open/Edit draft").count() == 0
            assert await page.get_by_role("button", name="Accept draft").count() == 0
            assert await page.get_by_role("button", name="Discard draft").is_visible()
            assert await page.get_by_role("button", name="Finish current tailoring first").is_disabled()
            rejected = status("application-C", "session-C", status_name="rejected", review=None, result_value=stale_result, draft_id=None)
            await page.evaluate("(value) => window.__tailoringReviewMock.setStatus('session-C', value)", rejected)
            await page.evaluate("(value) => window.__tailoringReviewMock.setDiscard('session-C', value)", {"session_id": "session-C", "application_id": "application-C", "status": "rejected", "protocol_version": 10, "source_cv_id": None, "draft_cv_id": None, "cv_id": None, "scanner_result": None})
            await page.evaluate("(value) => window.__tailoringReviewMock.setCreate('application-C', value)", session_response("application-C", "session-C-new"))
            await page.get_by_role("button", name="Discard draft").click()
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().status === 'rejected'")
            await page.get_by_role("button", name="Start new tailoring").click()
            await page.get_by_role("textbox", name="Aergia tailoring prompt").wait_for()
            assert await page.get_by_role("textbox", name="Aergia tailoring prompt").input_value() == "Synthetic one-time prompt for the restarted session."
            assert await page.evaluate("window.__tailoringReviewMock.applicationRefreshes.includes('application-C')"), "discard did not refresh the current application"
            print("PASS stale/deleted recovery: unusable edit/accept are hidden, discard clears the pending session, and restart returns a fresh one-time prompt", flush=True)

            stale_owned_review = draft_review("current", revision=16, fit=fit_review("generic"), tag="stale-owned")
            stale_owned = status("application-owned-stale", "session-owned-stale", status_name="stale", review=stale_owned_review, result_value=result(draft_id="draft-owned-stale", tag="stale-owned"), draft_id="draft-owned-stale")
            await load_status(page, "application-owned-stale", stale_owned)
            assert await page.get_by_role("link", name="Open/Edit draft").is_visible(), "an existing stale draft should remain inspectable"
            assert await page.get_by_role("button", name="Accept draft").count() == 0, "stale target must not be accepted"
            assert await page.get_by_text("This saved draft has a review for the previous application target.").count() == 1
            assert await page.get_by_text("Current review applies to saved draft revision 16.").count() == 0
            print("PASS stale owned draft: owner can inspect it while review and acceptance are labeled for the previous target", flush=True)

            historical_result = result(protocol=9, draft_id="draft-D", tag="historical-D")
            historical = status("application-D", "session-D", result_value=historical_result, protocol=9, draft_id="draft-D")
            await load_status(page, "application-D", historical)
            assert await page.get_by_text("Submitted review · historical protocol").count() == 1
            assert await page.get_by_text("Not run · Not run", exact=True).count() == 1
            await page.get_by_role("button", name="Accept draft").wait_for()
            await page.evaluate("(value) => window.__tailoringReviewMock.setAccept('session-D', value)", {"session_id": "session-D", "application_id": "application-D", "status": "accepted", "protocol_version": 9, "source_cv_id": None, "draft_cv_id": "draft-D", "cv_id": "draft-D", "scanner_result": None})
            await page.evaluate("(value) => window.__tailoringReviewMock.setStatus('session-D', value)", accepted_status("application-D", "session-D", 9))
            await page.get_by_role("button", name="Accept draft").click()
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().status === 'accepted'")
            historical_accept = await page.evaluate("window.__tailoringReviewMock.requests.accept.at(-1)")
            assert historical_accept["request"] is None, historical_accept
            print("PASS historical/null compatibility: protocol 9 keeps its submitted feedback and bodyless owner accept", flush=True)

            route_review = draft_review("needs_reevaluation", revision=27, fit=None, applicability="not_run", tag="route-E")
            route_status = status("application-E", "session-E", review=route_review, result_value=result(draft_id="draft-E", tag="route-E"), draft_id="draft-E")
            await load_status(page, "application-E", route_status)
            deferred = await page.evaluate("window.__tailoringReviewMock.defer('reevaluate', 'session-E')")
            await page.evaluate("() => { void window.tailoringReviewHarness.reevaluateDraft(); void window.tailoringReviewHarness.reevaluateDraft(); }")
            await page.wait_for_function("window.__tailoringReviewMock.calls.reevaluate.filter((id) => id === 'session-E').length === 1")
            await page.get_by_role("button", name="Reevaluating…").wait_for()
            await page.evaluate("(value) => window.__tailoringReviewMock.setLatest('application-F', value)", status("application-F", "session-F", status_name="rejected", review=None, result_value=None, draft_id=None))
            await page.evaluate("window.tailoringReviewHarness.changeApplication('application-F')")
            await page.wait_for_function("window.tailoringReviewHarness.snapshot().applicationId === 'application-F' && window.tailoringReviewHarness.snapshot().sessionId === 'session-F'")
            route_response = {"protocol_version": 10, "session_id": "session-E", "application_id": "application-E", "draft_cv_id": "draft-E", "draft_review": draft_review("current", revision=27, fit=None, applicability="not_run", tag="late-E"), "format": "pdf", "pdf_base64": "", "page_count": 1}
            await page.evaluate("([token, value]) => window.__tailoringReviewMock.resolve(token, value)", [deferred, route_response])
            await flush_browser(page)
            current_snapshot = await page.evaluate("window.tailoringReviewHarness.snapshot()")
            assert current_snapshot["applicationId"] == "application-F" and current_snapshot["sessionId"] == "session-F", current_snapshot
            assert await page.evaluate("window.__tailoringReviewMock.applicationRefreshes.includes('application-E')") is False, "late reevaluation refreshed the previous application"
            assert await page.evaluate("window.__tailoringReviewMock.calls.reevaluate.filter((id) => id === 'session-E').length") == 1, "duplicate reevaluation was sent"
            print("PASS reevaluation race: duplicate action is suppressed and late response cannot alter or refresh the new application", flush=True)

            expired_result = result(draft_id="draft-G", tag="expired-G")
            expired = status("application-G", "session-G", status_name="expired", review=draft_review("needs_reevaluation", revision=5, applicability="earlier_version", tag="expired-G"), result_value=expired_result, draft_id="draft-G")
            await load_status(page, "application-G", expired)
            assert await page.get_by_role("link", name="Open/Edit draft").is_visible(), "an expired draft awaiting recovery should remain inspectable"
            assert await page.get_by_role("button", name="Discard draft").is_visible()
            assert await page.get_by_role("button", name="Finish current tailoring first").is_disabled()
            print("PASS expired pending draft: owner can discard it before starting a replacement", flush=True)

            print("PASS narrow layout: full review can be captured at 390px without horizontal page overflow", flush=True)
        finally:
            await browser.close()

asyncio.run(main())
`;

try {
  const python = join(repositoryRoot, "api/.venv/bin/python");
  const result = spawnSync(python, ["-c", browserDriver, bundlePath, captureDirectory, builtCss], {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: "inherit",
    timeout: 120000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Browser review harness exited with status ${result.status ?? "unknown"}`);
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
