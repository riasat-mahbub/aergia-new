import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-tailoring-providers-"));
const bundlePath = join(temporaryDirectory, "tailoring-providers-browser.js");

const entry = `
  import React, { StrictMode } from "react";
  import { createRoot } from "react-dom/client";
  import TailoringProviderSettings from ${JSON.stringify(join(webRoot, "src/features/tailoring/components/TailoringProviderSettings.tsx"))};

  window.mountTailoringProviderSettings = () => {
    window.tailoringProviderRoot = createRoot(document.getElementById("root"));
    window.tailoringProviderRoot.render(React.createElement(StrictMode, null, React.createElement(TailoringProviderSettings)));
  };
`;

await build({
  stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
  bundle: true,
  format: "iife",
  platform: "browser",
  outfile: bundlePath,
  define: { "process.env.NODE_ENV": '"development"' },
  plugins: [{
    name: "tailoring-provider-api-mock",
    setup(buildApi) {
      buildApi.onResolve({ filter: /^\.\.\/api\/providers$/ }, () => ({ path: "provider-api-mock", namespace: "provider-test" }));
      buildApi.onLoad({ filter: /^provider-api-mock$/, namespace: "provider-test" }, () => ({
        loader: "js",
        contents: `
          export const getTailoringProviders = () => window.__tailoringProviderMock.getProviders();
          export const connectTailoringProvider = (...args) => window.__tailoringProviderMock.connect(...args);
          export const disconnectTailoringProvider = (...args) => window.__tailoringProviderMock.disconnect(...args);
          export const checkGeminiTailoringSetup = (...args) => window.__tailoringProviderMock.checkGemini(...args);
          export const completeTailoringProviderOAuthCallback = (...args) => window.__tailoringProviderMock.completeCallback(...args);
        `,
      }));
    },
  }],
});

const browserDriver = String.raw`
import asyncio
import sys
from playwright.async_api import async_playwright

BUNDLE_PATH = sys.argv[1]
MOCK_BOOTSTRAP = r"""
(() => {
  window.__tailoringProviderMock = {
    calls: { status: 0, callback: 0 },
    statusOutcomes: [],
    defaultStatus: { kind: "reject", status: 503 },
    callbackFails: true,
    enqueueStatus(outcome) { this.statusOutcomes.push(outcome); },
    getProviders() {
      this.calls.status += 1;
      const outcome = this.statusOutcomes.shift() || this.defaultStatus;
      if (outcome.kind === "reject") return Promise.reject({ response: { status: outcome.status } });
      return Promise.resolve(outcome.value);
    },
    completeCallback() {
      this.calls.callback += 1;
      return this.callbackFails ? Promise.reject(new Error("Synthetic sign-in failure")) : Promise.resolve({ detail: "Sign-in completed." });
    },
    connect() { return Promise.resolve({ authorization_url: "https://accounts.google.com/" }); },
    disconnect() { return Promise.resolve({ status: "disconnected" }); },
    checkGemini() { return Promise.resolve({ status: "ready" }); },
  };
})();
"""

def providers(chatgpt="ready", gemini="unavailable"):
    return {
        "chatgpt": {"status": chatgpt},
        "gemini": {"status": gemini, "detail": "Gemini is not enabled here"},
    }

async def open_settings(browser, url, default_status):
    page = await browser.new_page()
    page.set_default_timeout(10000)
    async def fulfill_settings(route):
        await route.fulfill(status=200, content_type="text/html", body='<div id="root"></div>')
    await page.route("http://settings.test/**", fulfill_settings)
    await page.goto(url)
    await page.evaluate(MOCK_BOOTSTRAP)
    await page.evaluate("(value) => { window.__tailoringProviderMock.defaultStatus = value; }", default_status)
    await page.add_script_tag(path=BUNDLE_PATH)
    await page.evaluate("window.mountTailoringProviderSettings()")
    return page

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            unsupported = await open_settings(
                browser,
                "http://settings.test/settings?code=fictional-code&state=fictional-state&keep=1",
                {"kind": "reject", "status": 404},
            )
            await unsupported.get_by_text("Optional provider connections are not available on this deployment.").wait_for()
            unsupported_url = await unsupported.evaluate("window.location.href")
            assert "keep=1" in unsupported_url and "code=" not in unsupported_url and "state=" not in unsupported_url, unsupported_url
            assert await unsupported.get_by_role("button", name="Connect ChatGPT").count() == 0
            assert await unsupported.get_by_role("link", name="Download the Aergia skill").count() == 0
            assert await unsupported.evaluate("window.__tailoringProviderMock.calls.callback") == 0
            assert await unsupported.get_by_text("You can keep tailoring with your coding agent.").is_visible()
            print("PASS unsupported provider deployment: callback query is cleaned, no callback or provider action is sent, and coding-agent flow remains available", flush=True)

            retry = await open_settings(
                browser,
                "http://settings.test/settings?code=fictional-code&state=fictional-state",
                {"kind": "reject", "status": 503},
            )
            await retry.get_by_role("button", name="Retry").wait_for()
            assert await retry.evaluate("window.__tailoringProviderMock.calls.status") == 2, "StrictMode should replay the initial status effect"
            await retry.evaluate("() => { window.__tailoringProviderMock.enqueueStatus({ kind: 'resolve', value: { chatgpt: { status: 'ready' }, gemini: { status: 'unavailable', detail: 'Not enabled' } } }); window.__tailoringProviderMock.enqueueStatus({ kind: 'reject', status: 503 }); }")
            await retry.get_by_role("button", name="Retry").click()
            await retry.get_by_text("Synthetic sign-in failure").wait_for()
            await retry.wait_for_function("window.__tailoringProviderMock.calls.callback === 1 && [...document.querySelectorAll('[role=alert]')].some((node) => node.textContent.includes('Provider status could not be loaded'))")
            assert await retry.evaluate("window.__tailoringProviderMock.calls.callback") == 1
            assert await retry.get_by_role("link", name="Download the Aergia skill").count() == 0
            await retry.evaluate("() => { window.__tailoringProviderMock.enqueueStatus({ kind: 'resolve', value: { chatgpt: { status: 'ready' }, gemini: { status: 'unavailable', detail: 'Not enabled' } } }); }")
            await retry.get_by_role("button", name="Retry").click()
            await retry.get_by_role("button", name="Disconnect").wait_for()
            assert await retry.evaluate("window.__tailoringProviderMock.calls.callback") == 1
            cleaned_url = await retry.evaluate("window.location.href")
            assert "code=" not in cleaned_url and "state=" not in cleaned_url, cleaned_url
            print("PASS callback retry and StrictMode replay: pending callback resumes after status retry, a submitted callback is not repeated by a later status retry, and ChatGPT status alone does not expose Gemini setup", flush=True)

            setup = await open_settings(
                browser,
                "http://settings.test/settings",
                {"kind": "resolve", "value": providers(chatgpt="ready", gemini="setup_required")},
            )
            await setup.get_by_role("link", name="Download the Aergia skill").wait_for()
            await setup.get_by_role("button", name="Check Gemini setup").wait_for()
            print("PASS supported Gemini setup path: Gemini setup instructions and check action appear only for setup_required", flush=True)
        finally:
            await browser.close()

asyncio.run(main())
`;

try {
  const windowsPython = join(repositoryRoot, "api/.venv/Scripts/python.exe");
  const posixPython = join(repositoryRoot, "api/.venv/bin/python");
  const python = process.platform === "win32" ? windowsPython : posixPython;
  const result = spawnSync(python, ["-c", browserDriver, bundlePath], {
    cwd: repositoryRoot,
    encoding: "utf8",
    stdio: "inherit",
    timeout: 120000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`Provider browser regression harness exited with status ${result.status ?? "unknown"}`);
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
