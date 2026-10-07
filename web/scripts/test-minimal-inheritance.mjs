import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-minimal-inheritance-"));
const bundlePath = join(temporaryDirectory, "inspector-browser.js");
const generatedCssPath = join(temporaryDirectory, "inspector.css");
const desktopCapture = join(tmpdir(), "minimal-p02-desktop.png");
const mobileCapture = join(tmpdir(), "minimal-p02-mobile.png");
const cssPath = process.env.MINIMAL_INHERITANCE_CSS ?? generatedCssPath;

if (!process.env.MINIMAL_INHERITANCE_CSS) {
  const tailwind = spawnSync(join(webRoot, "node_modules/.bin/tailwindcss"), [
    "--config", join(webRoot, "tailwind.config.ts"),
    "--input", join(webRoot, "src/index.css"),
    "--output", generatedCssPath,
    "--minify",
  ], { cwd: webRoot, encoding: "utf8" });
  assert.equal(tailwind.status, 0, `Tailwind CSS compilation failed: ${tailwind.stderr}`);
}

const entry = `
  import React, { useState } from "react";
  import { createRoot } from "react-dom/client";
  import Inspector from ${JSON.stringify(join(webRoot, "src/features/builder/components/customization/Inspector.tsx"))};

  const minimalManifest = {
    name: "Readable Minimal",
    global_styles: { body_font: "sans-serif", body_font_size: "small", body_line_height: "normal" },
    layout_defaults: { spacing: "minimal", entry_gap: "snug", field_gap: "tight" },
  };
  const alternateManifest = {
    name: "Alternate Template",
    global_styles: { body_font: "serif", body_font_size: "normal", body_line_height: "relaxed" },
    layout_defaults: { spacing: "comfortable", entry_gap: "roomy", field_gap: "balanced" },
  };

  function Harness() {
    const [manifest, setManifest] = useState(minimalManifest);
    const [customizations, setCustomizations] = useState({});
    const [instances, setInstances] = useState([
      { id: "profile", title: "Morgan Lee", type: "profile", enabled: true, data: { name: "Morgan Lee" } },
      { id: "experience", title: "Experience", type: "experience", enabled: true, data: [] },
    ]);
    const [writes, setWrites] = useState([]);

    window.inspectorHarness = {
      snapshot: () => JSON.parse(JSON.stringify({ instances, writes })),
      setDocumentSpacing: (spacing) => setCustomizations((current) => ({ ...current, spacing })),
      changeTemplate: () => setManifest((current) => current === minimalManifest ? alternateManifest : minimalManifest),
    };

    function updateStyle(id, style) {
      setWrites((current) => [...current, { id, style }]);
      setInstances((current) => current.map((instance) => instance.id === id ? { ...instance, style } : instance));
    }

    return React.createElement(
      "main",
      { className: "mx-auto w-full max-w-[560px] bg-app-surface p-4", style: { minHeight: "100vh" } },
      React.createElement(Inspector, {
        templateId: "template-current",
        templateName: manifest.name,
        templateManifest: manifest,
        instances,
        onUpdateStyle: updateStyle,
        onTemplateChange: () => window.inspectorHarness.changeTemplate(),
        onReset: () => {},
        customizations,
      }),
    );
  }

  createRoot(document.getElementById("root")).render(React.createElement(Harness));
`;

await build({
  stdin: { contents: entry, resolveDir: webRoot, loader: "ts" },
  bundle: true,
  format: "iife",
  platform: "browser",
  outfile: bundlePath,
  alias: { "@": join(webRoot, "src") },
  define: { "import.meta.env.DEV": "false" },
});

const browserDriver = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BUNDLE_PATH, CSS_PATH, DESKTOP_CAPTURE, MOBILE_CAPTURE = sys.argv[1:5]

async def run():
    bundle = Path(BUNDLE_PATH).read_text()
    css = Path(CSS_PATH).read_text()
    page_html = f'<style>{css}</style><div id="root"></div><script>{bundle}</script>'

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1280, "height": 980}, device_scale_factor=1)
        await page.set_content(page_html)
        await page.get_by_test_id("inspector").wait_for()

        initial = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert initial["writes"] == [], initial
        assert all("style" not in item for item in initial["instances"]), initial

        await page.get_by_test_id("section-card-experience").locator("button").first.click()
        body_group = page.get_by_role("button", name="Body text")
        await body_group.click()
        body_size = page.locator('select[aria-label="Body size"]')
        line_height = page.locator('select[aria-label="Body line height"]')
        assert await body_size.input_value() == ""
        assert await body_size.locator("option:checked").inner_text() == "Template default (10.5 pt)"
        assert await line_height.input_value() == ""
        assert await line_height.locator("option:checked").inner_text() == "Template default (Normal · 1.4)"

        await page.get_by_role("button", name="Spacing").click()
        assert await page.get_by_test_id("inherited-entry-gap-experience").inner_text() == "Template default (8 px)"
        assert await page.get_by_test_id("inherited-field-gap-experience").inner_text() == "Template default (4 px)"
        opened = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert opened["writes"] == [], opened
        assert all("style" not in item for item in opened["instances"]), opened

        await body_size.select_option("normal")
        edited = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert edited["instances"][1]["style"]["typography"]["body"]["font_size"] == "normal", edited
        assert edited["writes"][-1]["style"]["typography"]["body"]["font_size"] == "normal", edited
        await body_size.select_option("")
        cleared_size = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert cleared_size["instances"][1].get("style", {}) == {}, cleared_size

        fields_picker = page.get_by_test_id("spacing-fields-experience")
        await fields_picker.get_by_role("radio", name="Loose: 32px").click()
        explicit_gap = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert explicit_gap["instances"][1]["style"]["subsection"]["field_gap"] == "loose", explicit_gap
        await fields_picker.get_by_role("radio", name="Default").click()
        cleared_gap = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert cleared_gap["instances"][1].get("style", {}) == {}, cleared_gap
        assert await page.get_by_test_id("inherited-field-gap-experience").inner_text() == "Template default (4 px)"

        await body_size.select_option("large")
        await page.get_by_role("button", name="Reset this section").click()
        reset = await page.evaluate("() => window.inspectorHarness.snapshot()")
        assert reset["instances"][1].get("style", {}) == {}, reset
        assert "Customized" not in await page.get_by_test_id("section-card-experience").inner_text()

        await page.evaluate("() => window.inspectorHarness.setDocumentSpacing('comfortable')")
        await page.get_by_test_id("inherited-entry-gap-experience").get_by_text("Document spacing (16 px)").wait_for()
        assert await page.get_by_test_id("inherited-field-gap-experience").inner_text() == "Document spacing (16 px)"
        await page.evaluate("() => window.inspectorHarness.setDocumentSpacing(null)")
        await page.get_by_test_id("inherited-entry-gap-experience").get_by_text("Template default (8 px)").wait_for()

        await page.get_by_test_id("section-card-profile").locator("button").first.click()
        await page.get_by_role("button", name="Body text").click()
        profile_size = page.locator('select[aria-label="Body size"]')
        assert await profile_size.locator("option:checked").inner_text() == "Template default (10.5 pt)"
        assert await page.get_by_text("The candidate name keeps its separate size.").is_visible()

        await page.get_by_role("button", name="Change", exact=True).click()
        await page.get_by_role("button", name="Change template", exact=True).click()
        await page.get_by_role("dialog").wait_for(state="hidden")
        await page.get_by_test_id("section-card-profile").locator("button").first.click()
        await page.get_by_test_id("section-card-experience").locator("button").first.click()
        await page.get_by_role("button", name="Body text").click()
        alternate_body_size = page.locator('select[aria-label="Body size"]')
        assert await alternate_body_size.locator("option:checked").inner_text() == "Template default (12 pt)"
        await page.get_by_role("button", name="Spacing").click()
        assert await page.get_by_test_id("inherited-entry-gap-experience").inner_text() == "Template default (16 px)"
        assert await page.get_by_test_id("inherited-field-gap-experience").inner_text() == "Template default (12 px)"

        await page.get_by_role("button", name="Change", exact=True).click()
        await page.get_by_role("button", name="Change template", exact=True).click()
        await page.get_by_role("dialog").wait_for(state="hidden")
        await page.get_by_test_id("inherited-entry-gap-experience").get_by_text("Template default (8 px)").wait_for()

        await page.set_viewport_size({"width": 1280, "height": 980})
        await page.screenshot(path=DESKTOP_CAPTURE, full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.screenshot(path=MOBILE_CAPTURE, full_page=True)
        await browser.close()

asyncio.run(run())
`;

try {
  const result = spawnSync("python", ["-c", browserDriver, bundlePath, cssPath, desktopCapture, mobileCapture], {
    cwd: webRoot,
    encoding: "utf8",
    stdio: "inherit",
  });
  assert.equal(result.status, 0, `Playwright fixture exited with status ${result.status}.`);
  console.log(JSON.stringify({ desktopCapture, mobileCapture }));
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
