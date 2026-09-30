import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-tailoring-session-"));
const bundlePath = join(temporaryDirectory, "tailoring-session-browser.js");

const entry = `
  import React, { useCallback, useState } from "react";
  import { createRoot } from "react-dom/client";
  import { useTailoringSession } from ${JSON.stringify(join(webRoot, "src/features/tailoring/hooks/useTailoringSession.ts"))};
  import { useApplicationStore } from ${JSON.stringify(join(webRoot, "src/features/applications/state/applicationStore.ts"))};

  let root = null;
  function Harness() {
    const [applicationId, setApplicationId] = useState("application-A");
    const addToast = useCallback((message, type) => {
      window.__tailoringMock.toasts.push({ message, type });
    }, []);
    const fetchApplication = useCallback(async (id) => {
      window.__tailoringMock.fetchApplicationCalls.push(id);
    }, []);
    const tailoring = useTailoringSession({ applicationId, addToast, fetchApplication });
    const snapshot = () => ({
      applicationId,
      sessionId: tailoring.tailoringSession?.session_id ?? null,
      sessionApplicationId: tailoring.tailoringSession?.application_id ?? null,
      code: tailoring.tailoringSession?.code ?? null,
      prompt: tailoring.tailoringSession?.prompt ?? null,
      status: tailoring.tailoringStatus?.status ?? null,
      starting: tailoring.tailoringStarting,
    });
    window.tailoringHarness = {
      changeApplication: setApplicationId,
      snapshot,
      start: tailoring.startTailoring,
      copyPrompt: tailoring.copyPrompt,
      acceptDraft: tailoring.acceptDraft,
      rejectDraft: tailoring.rejectDraft,
      cancelTailoring: tailoring.cancelTailoring,
    };
    return React.createElement("pre", { id: "hook-state" }, JSON.stringify(snapshot()));
  }

  window.mountTailoringHarness = () => {
    root = createRoot(document.getElementById("root"));
    root.render(React.createElement(Harness));
  };
  window.unmountTailoringHarness = () => {
    if (root) root.unmount();
    root = null;
  };
  window.runStoreFetchRace = async () => {
    const first = window.__applicationMock.defer("application-A");
    const second = window.__applicationMock.defer("application-B");
    const fetchA = useApplicationStore.getState().fetch("application-A");
    const fetchB = useApplicationStore.getState().fetch("application-B");
    window.__applicationMock.resolve(second, { id: "application-B" });
    await fetchB;
    window.__applicationMock.resolve(first, { id: "application-A" });
    await fetchA;
    return useApplicationStore.getState().currentApplication?.id ?? null;
  };
  window.mountTailoringHarness();
`;

await build({
  stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
  bundle: true,
  format: "iife",
  platform: "browser",
  outfile: bundlePath,
  plugins: [{
    name: "tailoring-test-api-mocks",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^\.\.\/api\/tailoring$/ }, () => ({
        path: "tailoring-api-mock",
        namespace: "tailoring-test",
      }));
      buildApi.onLoad({ filter: /.*/, namespace: "tailoring-test" }, () => ({
        loader: "js",
        contents: `
          export const acceptTailoringDraft = (id) => window.__tailoringMock.call("accept", id);
          export const cancelTailoringSession = (id) => window.__tailoringMock.call("cancel", id);
          export const createTailoringSession = (id) => window.__tailoringMock.call("create", id);
          export const getLatestTailoringSession = (id) => window.__tailoringMock.call("latest", id);
          export const getTailoringSessionStatus = (id) => window.__tailoringMock.call("status", id);
          export const rejectTailoringDraft = (id) => window.__tailoringMock.call("reject", id);
        `,
      }));
      buildApi.onResolve({ filter: /^@\/features\/applications\/api\/applications$/ }, () => ({
        path: "application-api-mock",
        namespace: "application-test",
      }));
      buildApi.onLoad({ filter: /.*/, namespace: "application-test" }, () => ({
        loader: "js",
        contents: `
          export const getApplication = (id) => window.__applicationMock.get(id);
          export const listApplications = async () => [];
          export const createApplication = async (input) => input;
          export const updateApplication = async (_id, input) => input;
          export const deleteApplication = async () => {};
          export const recomputeApplicationRelevance = async (id) => ({ id });
          export const scanApplication = async (id) => ({ id });
        `,
      }));
    },
  }],
});

const browserDriver = String.raw`
import asyncio
import json
import sys
from playwright.async_api import async_playwright

BUNDLE_PATH = sys.argv[1]
MOCK_BOOTSTRAP = r"""
(() => {
  let serial = 0;
  const pending = new Map();
  const queues = { latest: new Map(), create: new Map(), status: new Map(), accept: new Map(), reject: new Map(), cancel: new Map(), application: new Map() };
  const calls = { latest: [], create: [], status: [], accept: [], reject: [], cancel: [], application: [] };
  function deferred() {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    return { promise, resolve, reject };
  }
  function keyQueue(kind, key) {
    const map = queues[kind];
    if (!map.has(key)) map.set(key, []);
    return map.get(key);
  }
  function defer(kind, key) {
    const token = kind + ":" + key + ":" + (++serial);
    const request = deferred();
    pending.set(token, request);
    keyQueue(kind, key).push(token);
    return token;
  }
  function consume(kind, key, fallback) {
    const token = keyQueue(kind, key).shift();
    if (!token) return fallback();
    return pending.get(token).promise;
  }
  function status(applicationId, sessionId, statusName) {
    return {
      protocol_version: 10,
      session_id: sessionId,
      application_id: applicationId,
      source_cv_id: null,
      draft_cv_id: "draft-" + sessionId,
      cv_id: null,
      status: statusName,
      expires_at: "2030-01-01T00:00:00Z",
      created_at: "2029-01-01T00:00:00Z",
      exchanged_at: null,
      submitted_at: null,
      reviewed_at: null,
      updated_at: "2029-01-01T00:00:00Z",
      attempts: 0,
      result: null,
      draft_review: null,
    };
  }
  window.testTailoringStatus = status;
window.__tailoringMock = {
    calls,
    toasts: [],
    fetchApplicationCalls: [],
    defer,
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
      request.reject(error || new Error("mock rejection"));
    },
    call(kind, key) {
      calls[kind].push(key);
      if (kind === "latest") return consume(kind, key, () => Promise.reject(new Error("404 no session")));
      if (kind === "create") return consume(kind, key, () => Promise.reject(new Error("missing create fixture")));
      if (kind === "status") return consume(kind, key, () => Promise.reject(new Error("missing status fixture")));
      return consume(kind, key, () => Promise.resolve({}));
    },
  };
window.__applicationMock = {
    calls: calls.application,
    defer(key) { return defer("application", key); },
    resolve(token, value) {
      const request = pending.get(token);
      if (!request) throw new Error("Unknown deferred request: " + token);
      pending.delete(token);
      request.resolve(value);
    },
    get(key) {
      calls.application.push(key);
      return consume("application", key, () => Promise.reject(new Error("missing application fixture")));
    },
};
const timers = new Map();
const realSetTimeout = window.setTimeout.bind(window);
const realClearTimeout = window.clearTimeout.bind(window);
window.setTimeout = (callback, delay, ...args) => {
  const record = { delay, fired: false, cleared: false };
  const id = realSetTimeout(() => {
    record.fired = true;
    callback(...args);
  }, delay);
  if (delay === 250 || delay === 3000) timers.set(id, record);
  return id;
};
window.clearTimeout = (id) => {
  const timer = timers.get(id);
  if (timer) timer.cleared = true;
  realClearTimeout(id);
};
window.__testTimers = {
  hasPending(delay) { return Array.from(timers.values()).some((timer) => timer.delay === delay && !timer.fired && !timer.cleared); },
  pendingCount(delay) { return Array.from(timers.values()).filter((timer) => timer.delay === delay && !timer.fired && !timer.cleared).length; },
  clearedCount(delay) { return Array.from(timers.values()).filter((timer) => timer.delay === delay && timer.cleared).length; },
};
})();
"""

async def flush_browser(page):
    await page.evaluate("() => new Promise((resolve) => requestAnimationFrame(() => resolve()))")

def session(application_id, session_id, code, prompt):
    return {
        "protocol_version": 10,
        "session_id": session_id,
        "application_id": application_id,
        "source_cv_id": None,
        "cv_id": None,
        "code": code,
        "session_url": "http://localhost/agent/tailor/" + session_id,
        "skill_url": "https://example.test/skill",
        "prompt": prompt,
        "status": "created",
        "expires_at": "2030-01-01T00:00:00Z",
    }

def status(application_id, session_id, status_name):
    return {
        "protocol_version": 10,
        "session_id": session_id,
        "application_id": application_id,
        "source_cv_id": None,
        "draft_cv_id": "draft-" + session_id,
        "cv_id": None,
        "status": status_name,
        "expires_at": "2030-01-01T00:00:00Z",
        "created_at": "2029-01-01T00:00:00Z",
        "exchanged_at": None,
        "submitted_at": None,
        "reviewed_at": None,
        "updated_at": "2029-01-01T00:00:00Z",
        "attempts": 0,
        "result": None,
        "draft_review": None,
    }

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            page.set_default_timeout(10000)
            await page.set_content('<div id="root"></div>')
            await page.evaluate(MOCK_BOOTSTRAP)
            await page.evaluate("Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: (text) => { window.clipboardWrites.push(text); return Promise.resolve(); } } }); window.clipboardWrites = [];")

            first_a_request = await page.evaluate("window.__tailoringMock.defer('latest', 'application-A')")
            await page.add_script_tag(path=BUNDLE_PATH)
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-A').length === 1")

            await page.evaluate("window.tailoringHarness.changeApplication('application-B')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.includes('application-B')")
            await page.wait_for_function("window.tailoringHarness.snapshot().applicationId === 'application-B' && window.tailoringHarness.snapshot().sessionId === null")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                first_a_request,
                status("application-A", "session-A", "draft_ready"),
            ])
            await flush_browser(page)
            current = await page.evaluate("window.tailoringHarness.snapshot()")
            assert current["applicationId"] == "application-B" and current["sessionId"] is None, current
            await page.evaluate("async () => { await window.tailoringHarness.acceptDraft(); await window.tailoringHarness.copyPrompt(); }")
            assert await page.evaluate("window.__tailoringMock.calls.accept") == [], "B must not accept A's hydrated session"
            assert await page.evaluate("window.clipboardWrites") == [], "a missing B session must not expose A's prompt"
            print("PASS A → B/404: late latest-session response cannot restore A or act/copy on B", flush=True)

            second_a_request = await page.evaluate("window.__tailoringMock.defer('latest', 'application-A')")
            create_a_request = await page.evaluate("window.__tailoringMock.defer('create', 'application-A')")
            await page.evaluate("window.tailoringHarness.changeApplication('application-A')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-A').length === 2")
            await page.evaluate("window.tailoringHarness.start(); window.tailoringHarness.start()")
            await page.wait_for_function("window.__tailoringMock.calls.create.length === 1")
            await flush_browser(page)
            assert await page.evaluate("window.__tailoringMock.calls.create.length") == 1, "duplicate start must share one create request"
            fresh_a = session("application-A", "session-fresh-A", "one-time-code-A", "Fresh one-time prompt A")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [create_a_request, fresh_a])
            await page.wait_for_function("window.tailoringHarness.snapshot().sessionId === 'session-fresh-A'")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                second_a_request,
                status("application-A", "session-old-A", "draft_ready"),
            ])
            await flush_browser(page)
            current = await page.evaluate("window.tailoringHarness.snapshot()")
            assert current["sessionId"] == "session-fresh-A" and current["prompt"] == "Fresh one-time prompt A", current
            await page.evaluate("window.tailoringHarness.copyPrompt()")
            await page.wait_for_function("window.clipboardWrites.length === 1")
            assert await page.evaluate("window.clipboardWrites[0]") == "Fresh one-time prompt A"
            print("PASS hydration race: late latest response cannot replace a fresh one-time prompt", flush=True)

            accept_request = await page.evaluate("window.__tailoringMock.defer('accept', 'session-fresh-A')")
            await page.evaluate("window.__tailoringMock.toasts.length = 0; window.__tailoringMock.fetchApplicationCalls.length = 0; window.__tailoringMock.calls.status.length = 0")
            await page.evaluate("window.firstAccept = window.tailoringHarness.acceptDraft(); window.duplicateAccept = window.tailoringHarness.acceptDraft()")
            await page.evaluate("() => window.duplicateAccept")
            await page.wait_for_function("window.__tailoringMock.calls.accept.filter((id) => id === 'session-fresh-A').length === 1")
            await page.evaluate("window.tailoringHarness.changeApplication('application-B')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-B').length === 2")
            await page.evaluate("(token) => window.__tailoringMock.resolve(token, {})", accept_request)
            await page.evaluate("() => window.firstAccept")
            assert await page.evaluate("window.__tailoringMock.calls.accept") == ["session-fresh-A"]
            assert await page.evaluate("window.__tailoringMock.calls.status") == [], "late accept must not trigger status hydration"
            assert await page.evaluate("window.__tailoringMock.fetchApplicationCalls") == [], "late accept must not refresh A after navigation"
            assert await page.evaluate("window.__tailoringMock.toasts") == [], "late accept must not toast on B"
            print("PASS action fencing: duplicate accept is suppressed and late A completion has no B side effects", flush=True)

            third_c_request = await page.evaluate("window.__tailoringMock.defer('latest', 'application-C')")
            await page.evaluate("window.tailoringHarness.changeApplication('application-C')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.includes('application-C')")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                third_c_request,
                status("application-C", "session-hydrated-C", "draft_ready"),
            ])
            await page.wait_for_function("window.tailoringHarness.snapshot().sessionId === 'session-hydrated-C'")
            await page.evaluate("() => window.tailoringHarness.copyPrompt()")
            assert await page.evaluate("window.tailoringHarness.snapshot().code") == ""
            assert await page.evaluate("window.clipboardWrites") == ["Fresh one-time prompt A"], "hydrated sessions do not contain a copyable one-time code"
            print("PASS hydrated prompt: an unavailable one-time code cannot be copied", flush=True)

            create_c_request = await page.evaluate("window.__tailoringMock.defer('create', 'application-C')")
            await page.evaluate("window.__tailoringMock.toasts.length = 0")
            await page.evaluate("() => { void window.tailoringHarness.start(); }")
            await page.wait_for_function("window.__tailoringMock.calls.create.filter((id) => id === 'application-C').length === 1")
            fresh_c = session("application-C", "session-poll-C", "one-time-code-C", "Fresh one-time prompt C")
            first_poll = await page.evaluate("window.__tailoringMock.defer('status', 'session-poll-C')")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [create_c_request, fresh_c])
            await page.wait_for_function("window.__tailoringMock.calls.status.includes('session-poll-C')")
            await page.evaluate("window.__tailoringMock.toasts.length = 0")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                first_poll,
                status("application-C", "session-poll-C", "exchanged"),
            ])
            await page.wait_for_function("window.tailoringHarness.snapshot().status === 'exchanged'")
            await page.wait_for_function("window.__testTimers.hasPending(3000)")
            await page.evaluate("window.unmountTailoringHarness()")
            assert await page.evaluate("window.__testTimers.pendingCount(3000)") == 0, "unmount must clear the pending poll timer"
            assert await page.evaluate("window.__testTimers.clearedCount(3000)") >= 1, "unmount must cancel the poll timer"

            page_latest_request = await page.evaluate("window.__tailoringMock.defer('latest', 'application-C')")
            await page.evaluate("window.mountTailoringHarness()")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-A').length === 3")
            await page.evaluate("window.tailoringHarness.changeApplication('application-C')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-C').length === 2")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                page_latest_request,
                status("application-C", "session-hydrated-poll-C", "exchanged"),
            ])
            late_poll = await page.evaluate("window.__tailoringMock.defer('status', 'session-hydrated-poll-C')")
            await page.wait_for_function("window.__tailoringMock.calls.status.includes('session-hydrated-poll-C')")
            await page.evaluate("window.unmountTailoringHarness()")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                late_poll,
                status("application-C", "session-hydrated-poll-C", "draft_ready"),
            ])
            await flush_browser(page)
            poll_count = await page.evaluate("window.__tailoringMock.calls.status.filter((id) => id === 'session-hydrated-poll-C').length")
            assert poll_count == 1, f"unmounted poll continued: {poll_count} requests"
            assert await page.evaluate("window.__tailoringMock.toasts") == [], "unmounted poll completion must not toast"
            print("PASS polling cleanup: unmount clears a scheduled poll and suppresses an in-flight response", flush=True)

            unmounted_latest = await page.evaluate("window.__tailoringMock.defer('latest', 'application-C')")
            await page.evaluate("window.mountTailoringHarness()")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-A').length === 4")
            await page.evaluate("window.tailoringHarness.changeApplication('application-C')")
            await page.wait_for_function("window.__tailoringMock.calls.latest.filter((id) => id === 'application-C').length === 3")
            await page.evaluate("([token, value]) => window.__tailoringMock.resolve(token, value)", [
                unmounted_latest,
                status("application-C", "session-unmount-action-C", "draft_ready"),
            ])
            await page.wait_for_function("window.tailoringHarness.snapshot().sessionId === 'session-unmount-action-C'")
            unmounted_accept = await page.evaluate("window.__tailoringMock.defer('accept', 'session-unmount-action-C')")
            await page.evaluate("() => { window.__tailoringMock.calls.status.length = 0; window.__tailoringMock.fetchApplicationCalls.length = 0; window.__tailoringMock.toasts.length = 0; window.unmountedAccept = window.tailoringHarness.acceptDraft(); }")
            await page.wait_for_function("window.__tailoringMock.calls.accept.includes('session-unmount-action-C')")
            await page.evaluate("window.unmountTailoringHarness()")
            await page.evaluate("(token) => window.__tailoringMock.resolve(token, {})", unmounted_accept)
            await page.evaluate("() => window.unmountedAccept")
            assert await page.evaluate("window.__tailoringMock.calls.status") == [], "unmounted accept must not fetch session status"
            assert await page.evaluate("window.__tailoringMock.fetchApplicationCalls") == [], "unmounted accept must not refresh application state"
            assert await page.evaluate("window.__tailoringMock.toasts") == [], "unmounted accept must not toast"
            print("PASS action cleanup: pending accept has no side effects after unmount", flush=True)

            final_store_id = await page.evaluate("window.runStoreFetchRace()")
            assert final_store_id == "application-B", f"late A store fetch replaced B: {final_store_id}"
            print("PASS application store: late A fetch cannot overwrite the newer B fetch", flush=True)
        finally:
            await browser.close()

asyncio.run(main())
`;

try {
  const python = join(repositoryRoot, "api/.venv/bin/python");
  const result = spawnSync(python, ["-c", browserDriver, bundlePath], {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: "inherit",
    timeout: 120000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Browser regression harness exited with status ${result.status ?? "unknown"}`);
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
