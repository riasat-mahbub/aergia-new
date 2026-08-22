import { describe, expect, it, vi } from "vitest";
import {
  applyPreviewPagination,
  calculatePagination,
  type MeasuredSection,
  type MeasuredZone,
} from "../pagePagination";
import { PAGE_WIDTH_PX, scaleForAvailableWidth, type PageGeometry } from "../pageGeometry";

const GEOMETRY: PageGeometry = {
  pageWidthPx: 80,
  pageHeightPx: 100,
  topMarginPx: 10,
  printableHeightPx: 90,
};

function zone(sections: MeasuredSection[]): MeasuredZone {
  return { id: "main", top: 0, height: 100, sections };
}

describe("page geometry", () => {
  it("scales only the visual canvas and never enlarges it", () => {
    expect(scaleForAvailableWidth(PAGE_WIDTH_PX / 2)).toBeCloseTo(0.5);
    expect(scaleForAvailableWidth(PAGE_WIDTH_PX)).toBe(1);
    expect(scaleForAvailableWidth(PAGE_WIDTH_PX * 1.5)).toBe(1);
  });
});

describe("calculatePagination", () => {
  it("keeps an entry on the current page when it fits", () => {
    const result = calculatePagination([
      zone([{ id: "section", top: 10, height: 50, breakBefore: false, headingKeepsWithFirst: false, entries: [
        { id: "entry", top: 20, height: 40, keepTogether: true },
      ] }]),
    ], GEOMETRY);

    expect(result.pageCount).toBe(1);
    expect(result.spacers).toEqual([]);
  });

  it("moves a keep-together entry to the next page when it crosses a boundary", () => {
    const result = calculatePagination([
      zone([{ id: "section", top: 10, height: 100, breakBefore: false, headingKeepsWithFirst: false, entries: [
        { id: "entry", top: 70, height: 40, keepTogether: true },
      ] }]),
    ], GEOMETRY);

    expect(result.pageCount).toBe(2);
    expect(result.spacers).toEqual([{ beforeId: "entry", height: 40, page: 2 }]);
  });

  it("honors an explicit section page break", () => {
    const result = calculatePagination([
      zone([
        { id: "first", top: 10, height: 20, breakBefore: false, headingKeepsWithFirst: false, entries: [] },
        { id: "second", top: 30, height: 20, breakBefore: true, headingKeepsWithFirst: false, entries: [] },
      ]),
    ], GEOMETRY);

    expect(result.pageCount).toBe(2);
    expect(result.spacers).toEqual([{ beforeId: "second", height: 80, page: 2 }]);
  });

  it("allows an entry taller than a printable page to split naturally", () => {
    const result = calculatePagination([
      zone([{ id: "section", top: 10, height: 180, breakBefore: false, headingKeepsWithFirst: false, entries: [
        { id: "entry", top: 20, height: 140, keepTogether: true },
      ] }]),
    ], GEOMETRY);

    expect(result.spacers).toEqual([]);
    expect(result.pageCount).toBe(2);
  });

  it("takes the longest zone when columns flow independently", () => {
    const result = calculatePagination([
      zone([{ id: "sidebar", top: 0, height: 80, breakBefore: false, headingKeepsWithFirst: false, entries: [] }]),
      { id: "main", top: 0, height: 220, sections: [] },
    ], GEOMETRY);

    expect(result.pageCount).toBe(3);
  });
});

describe("applyPreviewPagination", () => {
  it("inserts idempotent preview-only spacers into the measured iframe DOM", () => {
    const previewDocument = document.implementation.createHTMLDocument();
    previewDocument.body.innerHTML = `
      <div data-preview-zone="true" data-preview-zone-id="main">
        <section data-preview-section="true" data-preview-section-id="work">
          <div
            class="entry"
            data-preview-entry="true"
            data-preview-entry-id="entry-1"
            data-preview-keep-together="true"
          ></div>
        </section>
      </div>
    `;
    const zone = previewDocument.querySelector('[data-preview-zone="true"]');
    const section = previewDocument.querySelector('[data-preview-section="true"]');
    const entry = previewDocument.querySelector('[data-preview-entry="true"]');
    if (!(zone instanceof HTMLElement) || !(section instanceof HTMLElement) || !(entry instanceof HTMLElement)) {
      throw new Error("preview fixture did not render");
    }

    const boxes = new Map<Element, { top: number; height: number }>([
      [previewDocument.body, { top: 0, height: 100 }],
      [zone, { top: 0, height: 100 }],
      [section, { top: 10, height: 100 }],
      [entry, { top: 70, height: 40 }],
    ]);
    for (const [element, box] of boxes) {
      vi.spyOn(element, "getBoundingClientRect").mockReturnValue({
        x: 0,
        y: box.top,
        width: 80,
        height: box.height,
        top: box.top,
        right: 80,
        bottom: box.top + box.height,
        left: 0,
        toJSON: () => ({}),
      });
    }
    Object.defineProperty(previewDocument.body, "scrollHeight", {
      configurable: true,
      value: 100,
    });

    const first = applyPreviewPagination(previewDocument, GEOMETRY);
    expect(first.spacers).toHaveLength(1);
    expect(previewDocument.querySelectorAll("[data-aergia-preview-spacer]")).toHaveLength(1);
    expect(previewDocument.body.style.paddingTop).toBe("10px");

    const second = applyPreviewPagination(previewDocument, GEOMETRY);
    expect(second.spacers).toEqual(first.spacers);
    expect(previewDocument.querySelectorAll("[data-aergia-preview-spacer]")).toHaveLength(1);
  });
});
