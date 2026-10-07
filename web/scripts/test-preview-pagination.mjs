import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(webRoot, "src");
const repositoryRoot = resolve(webRoot, "..");
const apiRoot = join(repositoryRoot, "api");
const apiPython = join(apiRoot, ".venv/bin/python");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "aergia-preview-pagination-"));
const fixtureDirectory = resolve(process.env.MINIMAL_PREVIEW_FIXTURE_DIRECTORY ?? join(temporaryDirectory, "fixtures"));
const bundlePath = join(temporaryDirectory, "preview.js");
const cssPath = join(temporaryDirectory, "preview.css");
const screenshotPaths = ["/tmp/minimal-preview-short.png", "/tmp/minimal-preview-long.png"];

if (!process.env.MINIMAL_PREVIEW_FIXTURE_DIRECTORY) {
  const fixturePath = join(repositoryRoot, "docs/fixtures/minimal-readability/preview-sections.json");
  const generator = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from app.db.seed import SEED_TEMPLATES
from app.services.renderer import prepare_render_source, render_source_html, render_source_pdf
from app.services.renderer._pdf_runtime import close_browser

fixture_path, output_path = map(Path, sys.argv[1:3])
fixtures = json.loads(fixture_path.read_text())
minimal = next(seed["manifest"] for seed in SEED_TEMPLATES if seed["id"] == "generic-minimal")
output_path.mkdir(parents=True, exist_ok=True)

async def generate():
    try:
        for length in ("short", "long"):
            source = prepare_render_source(fixtures[length], minimal)
            (output_path / f"generic-minimal-{length}.html").write_text(render_source_html(source))
            if length == "long":
                pdf = await render_source_pdf(source)
                (output_path / "generic-minimal-long.pdf").write_bytes(pdf)
    finally:
        await close_browser()

asyncio.run(generate())
`;
  const generation = spawnSync(join(apiRoot, ".venv/bin/python"), ["-c", generator, fixturePath, fixtureDirectory], {
    cwd: apiRoot,
    encoding: "utf8",
    maxBuffer: 1024 * 1024,
  });
  assert.equal(generation.status, 0, `Production HTML/PDF fixture generation failed: ${generation.stderr}`);
}

const cases = ["short", "long"].map((length) => {
  const filename = join(fixtureDirectory, `generic-minimal-${length}.html`);
  const html = readFileSync(filename, "utf8").replace(/(<a\b[^>]*?\bhref=)(["'])[^"']*\2/gi, "$1\"#\"");
  return { length, filename, html };
});
const exportPdf = join(fixtureDirectory, "generic-minimal-long.pdf");
const pdfiumTextReader = String.raw`
import sys
from pypdfium2 import PdfDocument

document = PdfDocument(sys.argv[1])
print(document[1].get_textpage().get_text_range())
`;
const exportText = spawnSync(apiPython, ["-c", pdfiumTextReader, exportPdf], {
  cwd: apiRoot,
  encoding: "utf8",
  maxBuffer: 1024 * 1024,
});
assert.equal(exportText.status, 0, `Unable to read page 2 from ${exportPdf} with PDFium: ${exportText.stderr}`);
const exportFirstLine = exportText.stdout.split(/\r?\n/).map((line) => line.trim()).find(Boolean);
assert.ok(exportFirstLine, `No text recovered from page 2 of ${exportPdf}`);
const screenshotMode = process.env.MINIMAL_PREVIEW_CAPTURE ?? "all";

const tailwind = spawnSync(join(webRoot, "node_modules/.bin/tailwindcss"), [
  "--config", join(webRoot, "tailwind.config.ts"),
  "--input", join(sourceRoot, "index.css"),
  "--output", cssPath,
  "--minify",
], { cwd: webRoot, encoding: "utf8" });
assert.equal(tailwind.status, 0, `Tailwind CSS compilation failed: ${tailwind.stderr}`);

const entry = `
  import React from "react";
  import { createRoot } from "react-dom/client";
  import UserTemplateRenderer from ${JSON.stringify(join(sourceRoot, "features/builder/components/preview/UserTemplateRenderer.tsx"))};
  const instances = [
    { id: "profile", title: "Alexandra Bennett", type: "profile", enabled: true, data: {} },
    { id: "experience", title: "Experience", type: "experience", enabled: true, data: [] },
  ];
  createRoot(document.getElementById("root")).render(React.createElement(UserTemplateRenderer, {
    instances,
    customizations: {},
    manifest: { name: "Minimal", global_styles: {}, layout_defaults: {} },
  }));
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
    plugins: [{
      name: "fixture-render-html",
      setup(buildContext) {
        buildContext.onResolve({ filter: /^\.\.\/\.\.\/api\/render$/ }, () => ({ path: "fixture-render-html", namespace: "preview-fixture" }));
        buildContext.onLoad({ filter: /.*/, namespace: "preview-fixture" }, () => ({
          contents: "export async function renderHtml() { return { html: window.__previewFixtureHTML }; }",
          loader: "js",
        }));
      },
    }],
  });

  const casesLiteral = JSON.stringify(cases);
  const browserDriver = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

CASES = json.loads(sys.argv[1])
BUNDLE_PATH, CSS_PATH = sys.argv[2:4]
EXPORT_FIRST_LINE = sys.argv[4]
SCREENSHOT_MODE = sys.argv[5]

async def run():
    bundle = Path(BUNDLE_PATH).read_text()
    css = Path(CSS_PATH).read_text()
    page_html = f'<style>{css}</style><div id="root"></div><script>{bundle}</script>'
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        for case in CASES:
            page = await browser.new_page(viewport={"width": 1280, "height": 1400}, device_scale_factor=1)
            fixture_script = '<script>window.__previewFixtureHTML = ' + json.dumps(case["html"]) + '</script>'
            await page.set_content(fixture_script + page_html)
            iframe = page.locator('iframe[title="User Template Preview"]')
            await iframe.wait_for()
            await page.wait_for_function("""() => {
              const frame = document.querySelector('iframe[title="User Template Preview"]');
              const doc = frame?.contentDocument;
              return !!doc?.querySelector('#experience .section-entries .entry')
                && doc.body?.style.paddingTop === '24px';
            }""", timeout=15000)
            await page.wait_for_timeout(500)
            measurement = await page.evaluate("""() => {
              const frame = document.querySelector('iframe[title="User Template Preview"]');
              const doc = frame.contentDocument;
              const bodyTop = doc.body.getBoundingClientRect().top;
              const entries = [...doc.querySelectorAll('[data-preview-entry="true"]')].map((entry) => {
                const rect = entry.getBoundingClientRect();
                const top = rect.top - bodyTop;
                const bottom = rect.bottom - bodyTop;
                const name = entry.querySelector('.f-position, .f-degree, .f-project, .f-name, .f-category')?.textContent?.trim() || '';
                return { id: entry.dataset.previewEntryId, name, top, bottom };
              });
              const style = (selector) => getComputedStyle(doc.querySelector(selector));
              const labels = [...document.querySelectorAll('#root .bg-rose-50')].map((element) => element.textContent?.trim());
              const pageHeight = 297 / 25.4 * 96;
              const entriesOnSecondPage = entries.filter((entry) => Math.floor(entry.top / pageHeight) === 1);
              const crossingEntries = entries.filter((entry) => Math.floor(entry.top / pageHeight) !== Math.floor((entry.bottom - 0.5) / pageHeight));
              return {
                previewPageCount: labels.length + 1,
                previewPageLabels: labels,
                iframeHeightPx: Number.parseFloat(frame.style.height),
                documentScrollHeightPx: doc.body.scrollHeight,
                bodySizePx: Number.parseFloat(style('#experience .f-description').fontSize),
                nameSizePx: Number.parseFloat(style('.f-name').fontSize),
                headingSizePx: Number.parseFloat(style('#experience h2').fontSize),
                bodyLineHeight: getComputedStyle(doc.body).lineHeight,
                sectionGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience')).marginBottom),
                entryGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience .section-entries')).rowGap),
                fieldGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience .entry')).rowGap),
                previewSpacerCount: doc.querySelectorAll('[data-aergia-preview-spacer]').length,
                crossingEntries,
                secondPageFirstEntry: entriesOnSecondPage[0]?.name ?? null,
                secondPageFirstEntryTopPx: entriesOnSecondPage[0]?.top ?? null,
              };
            }""")
            measurement["fixture"] = case["length"]
            measurement["sourceHtml"] = case["filename"]
            assert measurement["previewPageCount"] == (1 if case["length"] == "short" else 2), measurement
            assert measurement["bodySizePx"] == 14, measurement
            assert measurement["nameSizePx"] == 24, measurement
            assert measurement["headingSizePx"] == 16, measurement
            assert measurement["sectionGapPx"] == 16, measurement
            assert measurement["entryGapPx"] == 8, measurement
            assert measurement["fieldGapPx"] == 4, measurement
            if case["length"] == "long":
                assert measurement["previewSpacerCount"] > 0, measurement
                assert not measurement["crossingEntries"], measurement
                assert EXPORT_FIRST_LINE.startswith(measurement["secondPageFirstEntry"]), (measurement, EXPORT_FIRST_LINE)
            if SCREENSHOT_MODE == "all" or SCREENSHOT_MODE == case["length"]:
                screenshot = f'/tmp/minimal-preview-{case["length"]}.png'
                await page.screenshot(path=screenshot, full_page=True)
                measurement["screenshot"] = screenshot
            results.append(measurement)
            print(json.dumps(measurement))
            await page.close()
        await browser.close()
    Path('/tmp/minimal-preview-measurements.json').write_text(json.dumps(results, indent=2))

asyncio.run(run())
`;
  const result = spawnSync(apiPython, ["-c", browserDriver, casesLiteral, bundlePath, cssPath, exportFirstLine, screenshotMode], {
    cwd: apiRoot,
    encoding: "utf8",
    stdio: "inherit",
  });
  assert.equal(result.status, 0, `Playwright fixture exited with status ${result.status}.`);
  console.log(JSON.stringify({ exportFirstLine, screenshots: screenshotPaths }));
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
