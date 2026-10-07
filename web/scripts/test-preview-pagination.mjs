import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
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
const fixtureDirectory = join(temporaryDirectory, "fixtures");
const bundlePath = join(temporaryDirectory, "preview.js");
const cssPath = join(temporaryDirectory, "preview.css");
const screenshotPaths = [
  "/tmp/minimal-preview-short.png",
  "/tmp/minimal-preview-long.png",
  "/tmp/minimal-preview-mobile-short.png",
  "/tmp/minimal-preview-mobile-oversized.png",
];

const fixturePath = join(repositoryRoot, "docs/fixtures/minimal-readability/preview-sections.json");
const generator = String.raw`
import asyncio
import copy
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

oversized = copy.deepcopy(fixtures["short"])
experience = next(section for section in oversized if section["type"] == "experience")
experience["data"] = [{
    "id": "oversized-entry",
    "position": "Deliberately Oversized Research Entry",
    "company": "Example Research Group",
    "start_date": "2022-01",
    "end_date": "2025-12",
    "description": [{"type": "bullet_list", "items": [
        {"text": f"Long evidence remains selectable and continues naturally across pages ({index}). "
                 "The preview should explain that this entry may split in PDF export."}
        for index in range(100)
    ]}],
}]

custom_layout = {
    "zones": copy.deepcopy(minimal["zones"]),
    "placement": copy.deepcopy(minimal["placement"]),
}
custom_layout["zones"][0]["styles"]["padding"] = "comfortable"
cases = {
    "short": (fixtures["short"], {}),
    "long": (fixtures["long"], {}),
    "oversized": (oversized, {}),
    "saved-custom": (fixtures["long"], {"layout": custom_layout}),
}

async def generate():
    try:
        metadata = {}
        for name, (sections, customizations) in cases.items():
            source = prepare_render_source(sections, minimal, customizations)
            html = render_source_html(source)
            pdf = await render_source_pdf(source)
            html_path = output_path / f"generic-minimal-{name}.html"
            pdf_path = output_path / f"generic-minimal-{name}.pdf"
            html_path.write_text(html)
            pdf_path.write_bytes(pdf)
            metadata[name] = {
                "html": str(html_path),
                "pdf": str(pdf_path),
                "customizations": customizations,
            }
        (output_path / "cases.json").write_text(json.dumps(metadata))
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

const generatedCases = JSON.parse(readFileSync(join(fixtureDirectory, "cases.json"), "utf8"));
const cases = Object.entries(generatedCases).map(([name, paths]) => ({
  length: name,
  filename: paths.html,
  pdf: paths.pdf,
  customizations: paths.customizations,
  html: readFileSync(paths.html, "utf8").replace(/(<a\b[^>]*?\bhref=)(["'])[^"']*\2/gi, "$1\"#\""),
}));
const casesPath = join(temporaryDirectory, "browser-cases.json");
writeFileSync(casesPath, JSON.stringify(cases));
const exportReader = String.raw`
import json
import sys
from pypdfium2 import PdfDocument

document = PdfDocument(sys.argv[1])
pages = [page.get_textpage().get_text_range() for page in document]
first_lines = [next((line.strip() for line in text.splitlines() if line.strip()), "") for text in pages]
print(json.dumps({"page_count": len(pages), "first_lines": first_lines}))
`;
const exports = {};
for (const item of cases) {
  const result = spawnSync(apiPython, ["-c", exportReader, item.pdf], {
    cwd: apiRoot,
    encoding: "utf8",
    maxBuffer: 1024 * 1024,
  });
  assert.equal(result.status, 0, `Unable to read ${item.length} export with PDFium: ${result.stderr}`);
  exports[item.length] = JSON.parse(result.stdout);
}

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
  import { calculatePagination } from ${JSON.stringify(join(sourceRoot, "features/builder/components/preview/pagePagination.ts"))};
  window.__calculatePagination = calculatePagination;
  const instances = [
    { id: "profile", title: "Alexandra Bennett", type: "profile", enabled: true, data: {} },
    { id: "experience", title: "Experience", type: "experience", enabled: true, data: [] },
  ];
  createRoot(document.getElementById("root")).render(React.createElement(UserTemplateRenderer, {
    instances,
    customizations: window.__previewFixtureCustomizations ?? {},
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

  const browserDriver = String.raw`
import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

CASES = json.loads(Path(sys.argv[1]).read_text())
EXPORTS = json.loads(sys.argv[2])
BUNDLE_PATH, CSS_PATH = sys.argv[3:5]
SCREENSHOT_MODE = sys.argv[5]

async def load_case(browser, case, viewport):
    page = await browser.new_page(viewport=viewport, device_scale_factor=1)
    bundle = Path(BUNDLE_PATH).read_text()
    css = Path(CSS_PATH).read_text()
    page_html = f'''<style>{css}</style><div id="root"></div><script>
window.__previewBodyResizeCount = 0;
const NativeResizeObserver = window.ResizeObserver;
window.ResizeObserver = class extends NativeResizeObserver {{
  constructor(callback) {{
    super((entries, observer) => {{
      if (entries.some((entry) => entry.target.tagName === 'BODY'
        && entry.target.ownerDocument.defaultView?.frameElement?.title === 'User Template Preview')) {{
        window.__previewBodyResizeCount += 1;
      }}
      callback(entries, observer);
    }});
  }}
}};
</script><script>{bundle}</script>'''
    fixture_script = (
        '<script>window.__previewFixtureHTML = ' + json.dumps(case["html"]) + ';'
        + 'window.__previewFixtureCustomizations = ' + json.dumps(case["customizations"]) + '</script>'
    )
    await page.set_content(fixture_script + page_html)
    iframe = page.locator('iframe[title="User Template Preview"]')
    await iframe.wait_for()
    await page.wait_for_function("""() => {
      const frame = document.querySelector('iframe[title="User Template Preview"]');
      const doc = frame?.contentDocument;
      return !!doc?.querySelector('#experience .section-entries .entry')
        && doc.body?.style.paddingTop === '48px'
        && doc.body?.style.paddingLeft === '16px'
        && doc.body?.style.paddingRight === '16px';
    }""", timeout=15000)
    await page.wait_for_timeout(450)
    return page

async def inspect_case(browser, case, export):
    page = await load_case(browser, case, {"width": 1280, "height": 1400})
    measurement = await page.evaluate("""() => {
      const frame = document.querySelector('iframe[title="User Template Preview"]');
      const doc = frame.contentDocument;
      const bodyTop = doc.body.getBoundingClientRect().top;
      const entries = [...doc.querySelectorAll('[data-preview-entry="true"]')].map((entry) => {
        const rect = entry.getBoundingClientRect();
        const top = rect.top - bodyTop;
        const bottom = rect.bottom - bodyTop;
        const name = entry.querySelector('.f-position, .f-degree, .f-project, .f-name, .f-category')?.textContent?.trim() || '';
        return { id: entry.dataset.previewEntryId, name, top, bottom, height: rect.height };
      });
      const style = (selector) => getComputedStyle(doc.querySelector(selector));
      const labels = [...document.querySelectorAll('#root .bg-rose-50')].map((element) => element.textContent?.trim());
      const pageHeight = 297 / 25.4 * 96;
      const entriesOnSecondPage = entries.filter((entry) => Math.floor(entry.top / pageHeight) === 1);
      const crossingEntries = entries.filter((entry) => Math.floor(entry.top / pageHeight) !== Math.floor((entry.bottom - 0.5) / pageHeight));
      const notice = document.querySelector('#root [aria-label="PDF pagination notice"]');
      const zone = doc.querySelector('.zone');
      const firstHeading = doc.querySelector('#experience h2');
      const bodyStyle = getComputedStyle(doc.body);
      const marginArea = {
        leftPx: Number.parseFloat(bodyStyle.paddingLeft),
        rightPx: Number.parseFloat(bodyStyle.paddingRight),
        topPx: Number.parseFloat(bodyStyle.paddingTop),
        zonePadding: getComputedStyle(zone).padding,
        zoneBoxSizing: getComputedStyle(zone).boxSizing,
      };
      return {
        previewPageCount: labels.length + 1,
        previewPageLabels: labels,
        iframeHeightPx: Number.parseFloat(frame.style.height),
        documentScrollHeightPx: doc.body.scrollHeight,
        bodySizePx: Number.parseFloat(style('#experience .f-description').fontSize),
        nameSizePx: Number.parseFloat(style('.f-name').fontSize),
        headingSizePx: Number.parseFloat(style('#experience h2').fontSize),
        bodyLineHeight: bodyStyle.lineHeight,
        sectionGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience')).marginBottom),
        entryGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience .section-entries')).rowGap),
        fieldGapPx: Number.parseFloat(getComputedStyle(doc.querySelector('#experience .entry')).rowGap),
        previewSpacerCount: doc.querySelectorAll('[data-aergia-preview-spacer]').length,
        crossingEntries,
        secondPageFirstEntry: entriesOnSecondPage[0]?.name ?? null,
        secondPageFirstEntryTopPx: entriesOnSecondPage[0]?.top ?? null,
        oversizedEntryHeights: entries.filter((entry) => entry.height > (297 / 25.4 * 96 - 96)).map((entry) => entry.name),
        noticeText: notice?.innerText ?? '',
        marginArea,
        firstHeadingTopPx: firstHeading ? firstHeading.getBoundingClientRect().top - bodyTop : null,
        bodyResizeCallbacks: window.__previewBodyResizeCount,
      };
    }""")
    measurement["fixture"] = case["length"]
    measurement["sourceHtml"] = case["filename"]
    measurement["exportPageCount"] = export["page_count"]
    measurement["exportPageTwoFirstLine"] = export["first_lines"][1] if len(export["first_lines"]) > 1 else None

    assert measurement["bodySizePx"] == 14, measurement
    assert measurement["nameSizePx"] == 24, measurement
    assert measurement["headingSizePx"] == 16, measurement
    assert measurement["sectionGapPx"] == 16, measurement
    assert measurement["entryGapPx"] == 8, measurement
    assert measurement["fieldGapPx"] == 4, measurement
    assert measurement["marginArea"]["leftPx"] == 16, measurement
    assert measurement["marginArea"]["rightPx"] == 16, measurement
    assert measurement["marginArea"]["topPx"] == 48, measurement
    assert measurement["marginArea"]["zoneBoxSizing"] == "border-box", measurement
    assert measurement["bodyResizeCallbacks"] <= 2, measurement
    assert measurement["previewPageCount"] >= (1 if case["length"] == "short" else 2), measurement

    if case["length"] == "short":
        assert measurement["previewPageCount"] == export["page_count"], measurement
        assert measurement["marginArea"]["zonePadding"] == "32px", measurement
    elif case["length"] == "long":
        assert measurement["previewPageCount"] == export["page_count"], measurement
        assert measurement["previewSpacerCount"] > 0, measurement
        assert not measurement["crossingEntries"], measurement
        assert measurement["secondPageFirstEntry"], measurement
        assert export["first_lines"][1].startswith(measurement["secondPageFirstEntry"]), (measurement, export)
    elif case["length"] == "saved-custom":
        assert measurement["previewPageCount"] == export["page_count"], measurement
        assert measurement["marginArea"]["zonePadding"] == "24px", measurement
        assert measurement["secondPageFirstEntry"], measurement
        assert export["first_lines"][1].startswith(measurement["secondPageFirstEntry"]), (measurement, export)
    else:
        assert measurement["oversizedEntryHeights"], measurement
        assert "Deliberately Oversized Research Entry" in measurement["noticeText"], measurement
        assert "may split in PDF export" in measurement["noticeText"], measurement
        assert measurement["exportPageCount"] >= 2, measurement

    if SCREENSHOT_MODE == "all" or SCREENSHOT_MODE == case["length"]:
        screenshot = f'/tmp/minimal-preview-{case["length"]}.png'
        await page.screenshot(path=screenshot, full_page=True)
        measurement["screenshot"] = screenshot
    await page.close()
    return measurement

async def boundary_cases(page):
    return await page.evaluate("""() => {
      const pageHeightPx = 297 / 25.4 * 96;
      const geometry = {
        pageWidthPx: 210 / 25.4 * 96,
        pageHeightPx,
        leftMarginPx: 16,
        rightMarginPx: 16,
        topMarginPx: 48,
        bottomMarginPx: 48,
        printableWidthPx: 210 / 25.4 * 96 - 32,
        printableHeightPx: pageHeightPx - 96,
      };
      const entryInMargin = window.__calculatePagination([{
        id: 'main', top: 0, height: pageHeightPx,
        sections: [{
          id: 'main/section/experience', top: 1000, height: 140,
          breakBefore: false, headingKeepsWithFirst: false, label: 'Experience',
          entries: [{ id: 'entry-in-bottom-margin', top: 1080, height: 24, keepTogether: true, label: 'Boundary Role' }],
        }],
      }], geometry);
      const headingInMargin = window.__calculatePagination([{
        id: 'main', top: 0, height: pageHeightPx,
        sections: [{
          id: 'main/section/projects', top: 1080, height: 40,
          breakBefore: false, headingKeepsWithFirst: true, label: 'Projects',
          entries: [{ id: 'first-project', top: 1104, height: 32, keepTogether: true, label: 'Boundary Project' }],
        }],
      }], geometry);
      return { entryInMargin, headingInMargin };
    }""")

async def mobile_case(browser, case):
    page = await load_case(browser, case, {"width": 390, "height": 844})
    await page.wait_for_timeout(250)
    result = await page.evaluate("""() => ({
      viewportWidth: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      previewWidth: document.querySelector('#root .overflow-x-auto')?.clientWidth,
      previewContentWidth: document.querySelector('#root .overflow-x-auto')?.scrollWidth,
      noticeVisible: !!document.querySelector('#root [aria-label="PDF pagination notice"]'),
      pageLabelCount: document.querySelectorAll('#root .bg-rose-50').length,
    })""")
    assert result["documentWidth"] <= result["viewportWidth"] + 1, result
    assert result["previewContentWidth"] <= result["previewWidth"] + 1, result
    if case["length"] == "oversized":
        assert result["noticeVisible"], result
    screenshot = f'/tmp/minimal-preview-mobile-{case["length"]}.png'
    await page.screenshot(path=screenshot, full_page=True)
    result["screenshot"] = screenshot
    await page.close()
    return result

async def run():
    bundle = Path(BUNDLE_PATH).read_text()
    css = Path(CSS_PATH).read_text()
    page_html = f'<style>{css}</style><div id="root"></div><script>{bundle}</script>'
    results = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        for case in CASES:
            measurement = await inspect_case(browser, case, EXPORTS[case["length"]])
            results.append(measurement)
            print(json.dumps(measurement))

        boundary_page = await browser.new_page(viewport={"width": 1280, "height": 1400}, device_scale_factor=1)
        await boundary_page.set_content(page_html)
        boundary_page_result = await boundary_cases(boundary_page)
        for key, target in (("entryInMargin", "entry-in-bottom-margin"), ("headingInMargin", "main/section/projects")):
            spacers = boundary_page_result[key]["spacers"]
            assert any(spacer["beforeId"] == target and spacer["height"] > 0 for spacer in spacers), boundary_page_result
        print(json.dumps({"bottomMarginBoundaryCases": boundary_page_result}))
        await boundary_page.close()

        mobile_results = []
        for case in (CASES[0], next(item for item in CASES if item["length"] == "oversized")):
            mobile = await mobile_case(browser, case)
            mobile["fixture"] = case["length"]
            mobile_results.append(mobile)
            print(json.dumps({"mobile": mobile}))
        await browser.close()
    Path('/tmp/minimal-preview-measurements.json').write_text(json.dumps(results, indent=2))
    Path('/tmp/minimal-preview-mobile-measurements.json').write_text(json.dumps(mobile_results, indent=2))

asyncio.run(run())
`;
  const result = spawnSync(apiPython, ["-c", browserDriver, casesPath, JSON.stringify(exports), bundlePath, cssPath, screenshotMode], {
    cwd: apiRoot,
    encoding: "utf8",
    stdio: "inherit",
  });
  assert.equal(result.status, 0, `Playwright fixture exited with status ${result.status}.`);
  console.log(JSON.stringify({ exports, screenshots: screenshotPaths }));
} finally {
  rmSync(temporaryDirectory, { recursive: true, force: true });
}
