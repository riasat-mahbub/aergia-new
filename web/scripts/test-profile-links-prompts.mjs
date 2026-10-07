import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(webRoot, "src");
const apiRoot = resolve(webRoot, "../api");
const apiPython = join(apiRoot, ".venv/bin/python");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-profile-links-prompts-"));
const bundlePath = join(temporaryDirectory, "profile-editors.js");
const cssPath = join(temporaryDirectory, "profile-editors.css");

const tailwind = spawnSync(join(webRoot, "node_modules/.bin/tailwindcss"), [
  "--config", join(webRoot, "tailwind.config.ts"),
  "--input", join(sourceRoot, "index.css"),
  "--output", cssPath,
  "--minify",
], { cwd: webRoot, encoding: "utf8" });
assert.equal(tailwind.status, 0, `Tailwind CSS compilation failed: ${tailwind.stderr}`);

const entry = `
  import React, { useState } from "react";
  import { createRoot } from "react-dom/client";
  import UserProfileEditor from ${JSON.stringify(join(sourceRoot, "features/profile/components/UserProfileEditor.tsx"))};
  import ExperienceEditor from ${JSON.stringify(join(sourceRoot, "shared/cv-editor/section-editors/experience/ExperienceEditor.tsx"))};
  function App() {
    const [profile, setProfile] = useState(() => JSON.parse(window.__profileSaved || JSON.stringify(window.__profileFixture)));
    window.__profile = profile;
    return React.createElement(React.Fragment, null,
      React.createElement(UserProfileEditor, { profile, onChange: setProfile }),
      React.createElement(ExperienceEditor, {
        mode: "library",
        data: [{ id: "experience-1", company: "Example Company", position: "Engineer", description: [] }],
        onChange: () => {},
      }),
      React.createElement("button", {
        id: "save-profile",
        type: "button",
        onClick: () => { window.__profileSaved = JSON.stringify(profile); },
      }, "Save profile"),
    );
  }
  let root = createRoot(document.getElementById("root"));
  root.render(React.createElement(App));
  window.__remountProfile = () => {
    root.unmount();
    root = createRoot(document.getElementById("root"));
    root.render(React.createElement(App));
  };
`;

const browserDriver = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BUNDLE_PATH, CSS_PATH = sys.argv[1:3]
FIXTURE = {
    "name": "Example Candidate",
    "site_text": "Personal Site",
    "site_url": "https://example.com/portfolio",
    "show_urls": False,
    "email_link": True,
    "social_links": [{"label": "LinkedIn", "url": "https://linkedin.com/in/example", "icon": "linkedin"}],
}

async def run():
    bundle = Path(BUNDLE_PATH).read_text()
    css = Path(CSS_PATH).read_text()
    fixture_script = '<script>window.__profileFixture = ' + json.dumps(FIXTURE) + '</script>'
    html = fixture_script + '<style>' + css + '</style><main id="root"></main><script>' + bundle + '</script>'
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        results = []
        for label, viewport in [
            ("desktop", {"width": 1280, "height": 1000}),
            ("mobile", {"width": 390, "height": 844}),
        ]:
            page = await browser.new_page(viewport=viewport)
            console_errors = []
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            await page.set_content(html)
            checkbox = page.get_by_label("Show URLs beside labels")
            await checkbox.wait_for()
            assert await checkbox.is_checked() is False
            description_id = await checkbox.get_attribute("aria-describedby")
            assert description_id
            description = page.locator("#" + description_id)
            assert "Visible addresses can help text extraction" in await description.inner_text()
            assert "parser behavior varies" in await description.inner_text()
            assert await page.get_by_text("A few focused sentences are usually enough; use specific, factual details that reflect your work.").count() == 1
            assert await page.get_by_text("A few concise bullets are often easier to scan. Include a result you can support, and use a metric only when you have evidence for it.").count() == 1
            assert await page.get_by_text("Name your area of work, strengths, and direction in a few focused sentences.").count() == 1
            assert await page.get_by_text("Start with what you did, then add scope and the result…").count() == 1

            await checkbox.focus()
            assert await checkbox.evaluate("element => document.activeElement === element")
            await page.keyboard.press("Space")
            await page.wait_for_function("window.__profile?.show_urls === true")
            await page.get_by_role("button", name="Save profile").click()
            await page.wait_for_function("JSON.parse(window.__profileSaved).show_urls === true")
            await page.evaluate("window.__remountProfile()")
            reloaded_checkbox = page.get_by_label("Show URLs beside labels")
            await page.wait_for_function("document.querySelector('input[aria-describedby]')?.checked === true")
            assert await reloaded_checkbox.is_checked() is True
            await page.screenshot(path=f"/tmp/cv-profile-{label}.png", full_page=True)

            await reloaded_checkbox.focus()
            await page.keyboard.press("Space")
            await page.wait_for_function("window.__profile?.show_urls === false")
            await page.get_by_role("button", name="Save profile").click()
            await page.wait_for_function("JSON.parse(window.__profileSaved).show_urls === false")
            await page.evaluate("window.__remountProfile()")
            assert await page.get_by_label("Show URLs beside labels").is_checked() is False
            width_check = await page.evaluate("({width: window.innerWidth, documentWidth: document.documentElement.scrollWidth})")
            assert width_check["documentWidth"] <= width_check["width"], (label, width_check)
            assert not console_errors, (label, console_errors)
            results.append({"viewport": label, "keyboard_toggle": "passed", "serialization_remount": "passed", "horizontal_overflow": False, "console_errors": console_errors})
            await page.close()
        print(json.dumps({"viewports": results, "summary_and_experience_prompts": "present", "screenshots": ["/tmp/cv-profile-desktop.png", "/tmp/cv-profile-mobile.png"]}))
        await browser.close()

asyncio.run(run())
`;

try {
  await build({
    stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
    bundle: true,
    format: "iife",
    platform: "browser",
    outfile: bundlePath,
    alias: { "@": sourceRoot },
    define: { "import.meta.env.DEV": "false" },
  });

  const result = spawnSync(apiPython, ["-c", browserDriver, bundlePath, cssPath], {
    cwd: apiRoot,
    encoding: "utf8",
    stdio: "inherit",
  });
  assert.equal(result.status, 0, `Playwright fixture exited with status ${result.status}.`);
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
