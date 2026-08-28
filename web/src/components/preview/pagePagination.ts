import { A4_PAGE_GEOMETRY, type PageGeometry } from "./pageGeometry";

const EPSILON = 0.01;
const SPACER_ATTRIBUTE = "data-aergia-preview-spacer";

export interface MeasuredEntry {
  id: string;
  top: number;
  height: number;
  keepTogether: boolean;
}

export interface MeasuredSection {
  id: string;
  top: number;
  height: number;
  breakBefore: boolean;
  headingKeepsWithFirst: boolean;
  entries: MeasuredEntry[];
}

export interface MeasuredZone {
  id: string;
  top: number;
  height: number;
  sections: MeasuredSection[];
}

export interface PreviewSpacer {
  beforeId: string;
  height: number;
  page: number;
}

export interface PaginationResult {
  pageCount: number;
  height: number;
  spacers: PreviewSpacer[];
}

function pageBottom(top: number, geometry: PageGeometry): number {
  return (Math.floor(Math.max(0, top) / geometry.pageHeightPx) + 1) * geometry.pageHeightPx;
}

function nextPageContentTop(top: number, geometry: PageGeometry): number {
  return (Math.floor(Math.max(0, top) / geometry.pageHeightPx) + 1) * geometry.pageHeightPx
    + geometry.topMarginPx;
}

function pageForTop(top: number, geometry: PageGeometry): number {
  return Math.floor(Math.max(0, top) / geometry.pageHeightPx) + 1;
}

function addSpacer(spacers: PreviewSpacer[], beforeId: string, height: number, page: number): void {
  if (height <= EPSILON) return;
  spacers.push({ beforeId, height, page });
}

/**
 * Calculate preview-only vertical spacers from already measured flow units.
 *
 * This intentionally models the renderer's coarse page-flow rules rather
 * than trying to reproduce Chromium's line-level fragmentation. The input
 * positions are natural screen-flow positions; `shift` tracks the whitespace
 * inserted when a unit is moved to the next physical page.
 */
export function calculatePagination(
  zones: readonly MeasuredZone[],
  geometry: PageGeometry = A4_PAGE_GEOMETRY,
): PaginationResult {
  const spacers: PreviewSpacer[] = [];
  let maxBottom = geometry.pageHeightPx;

  for (const zone of zones) {
    let shift = 0;
    let hasFlow = false;

    for (const section of zone.sections) {
      let sectionTop = section.top + shift;

      if (section.breakBefore && (hasFlow || sectionTop > geometry.topMarginPx + EPSILON)) {
        const target = nextPageContentTop(sectionTop, geometry);
        const spacerHeight = Math.max(0, target - sectionTop);
        addSpacer(spacers, section.id, spacerHeight, pageForTop(target, geometry));
        shift += spacerHeight;
        sectionTop += spacerHeight;
      }

      const firstEntry = section.entries[0];
      if (
        firstEntry
        && section.headingKeepsWithFirst
        && firstEntry.height <= geometry.printableHeightPx + EPSILON
      ) {
        const firstTop = firstEntry.top + shift;
        const sectionEnd = pageBottom(sectionTop, geometry);
        if (sectionTop < sectionEnd - EPSILON && firstTop + firstEntry.height > sectionEnd + EPSILON) {
          const target = nextPageContentTop(sectionTop, geometry);
          const spacerHeight = Math.max(0, target - sectionTop);
          addSpacer(spacers, section.id, spacerHeight, pageForTop(target, geometry));
          shift += spacerHeight;
          sectionTop += spacerHeight;
        }
      }

      for (const entry of section.entries) {
        const entryTop = entry.top + shift;
        if (entry.keepTogether && entry.height <= geometry.printableHeightPx + EPSILON) {
          const boundary = pageBottom(entryTop, geometry);
          if (entryTop < boundary - EPSILON && entryTop + entry.height > boundary + EPSILON) {
            const target = nextPageContentTop(entryTop, geometry);
            const spacerHeight = Math.max(0, target - entryTop);
            addSpacer(spacers, entry.id, spacerHeight, pageForTop(target, geometry));
            shift += spacerHeight;
          }
        }
      }

      maxBottom = Math.max(maxBottom, section.top + section.height + shift);
      hasFlow = true;
    }

    maxBottom = Math.max(maxBottom, zone.top + zone.height + shift);
  }

  const pageCount = Math.max(1, Math.ceil(maxBottom / geometry.pageHeightPx));
  return {
    pageCount,
    height: Math.max(geometry.pageHeightPx, pageCount * geometry.pageHeightPx, maxBottom),
    spacers,
  };
}

function asBoolean(value: string | undefined): boolean {
  return value === "true";
}

function directChildrenMatching(parent: Element, selector: string): HTMLElement[] {
  return Array.from(parent.children).filter(
    (child): child is HTMLElement => child.nodeType === 1 && (child as Element).matches(selector),
  );
}

function elementTop(element: Element, bodyTop: number): number {
  return element.getBoundingClientRect().top - bodyTop;
}

function elementHeight(element: Element): number {
  return element.getBoundingClientRect().height;
}

function measureDocument(document: Document): {
  zones: MeasuredZone[];
  targets: Map<string, HTMLElement>;
} {
  const body = document.body;
  const bodyTop = body.getBoundingClientRect().top;
  const targets = new Map<string, HTMLElement>();
  const zones: MeasuredZone[] = [];

  for (const zone of Array.from(document.querySelectorAll<HTMLElement>('[data-preview-zone="true"]'))) {
    const zoneId = zone.dataset.previewZoneId || `zone-${zones.length}`;
    const sections: MeasuredSection[] = [];

    for (const sectionElement of directChildrenMatching(zone, '[data-preview-section="true"]')) {
      const sectionRawId = sectionElement.dataset.previewSectionId || `section-${sections.length}`;
      const sectionId = `${zoneId}/section/${sectionRawId}`;
      targets.set(sectionId, sectionElement);

      const entries: MeasuredEntry[] = [];
      for (const [index, entryElement] of directChildrenMatching(sectionElement, '[data-preview-entry="true"]').entries()) {
        const entryRawId = entryElement.dataset.previewEntryId || `entry-${index}`;
        const entryId = `${sectionId}/entry/${entryRawId}`;
        targets.set(entryId, entryElement);
        entries.push({
          id: entryId,
          top: elementTop(entryElement, bodyTop),
          height: elementHeight(entryElement),
          keepTogether: asBoolean(entryElement.dataset.previewKeepTogether),
        });
      }

      sections.push({
        id: sectionId,
        top: elementTop(sectionElement, bodyTop),
        height: elementHeight(sectionElement),
        breakBefore: asBoolean(sectionElement.dataset.previewBreakBefore),
        headingKeepsWithFirst: asBoolean(sectionElement.dataset.previewHeadingKeepsWithFirst),
        entries,
      });
    }

    zones.push({
      id: zoneId,
      top: elementTop(zone, bodyTop),
      height: elementHeight(zone),
      sections,
    });
  }

  return { zones, targets };
}

function removeSpacers(document: Document): void {
  for (const spacer of Array.from(document.querySelectorAll(`[${SPACER_ATTRIBUTE}]`))) {
    spacer.remove();
  }
}

function createSpacer(document: Document, height: number, page: number): HTMLDivElement {
  const spacer = document.createElement("div");
  spacer.setAttribute(SPACER_ATTRIBUTE, "true");
  spacer.setAttribute("aria-hidden", "true");
  spacer.dataset.previewPage = String(page);
  spacer.style.display = "block";
  spacer.style.flex = "none";
  spacer.style.height = `${height}px`;
  spacer.style.margin = "0";
  spacer.style.padding = "0";
  spacer.style.pointerEvents = "none";
  return spacer;
}

/**
 * Apply the approximation to a rendered preview document. This mutates only
 * the same-origin iframe DOM and never the HTML sent to PDF export.
 */
export function applyPreviewPagination(
  document: Document,
  geometry: PageGeometry = A4_PAGE_GEOMETRY,
): PaginationResult {
  const body = document.body;
  if (!body) {
    return { pageCount: 1, height: geometry.pageHeightPx, spacers: [] };
  }

  removeSpacers(document);
  body.style.paddingTop = `${geometry.topMarginPx}px`;

  const measured = measureDocument(document);
  const result = calculatePagination(measured.zones, geometry);
  for (const spacer of result.spacers) {
    const target = measured.targets.get(spacer.beforeId);
    if (!target?.parentElement) continue;
    target.parentElement.insertBefore(createSpacer(document, spacer.height, spacer.page), target);
  }

  const measuredHeight = body.scrollHeight;
  const pageCount = Math.max(result.pageCount, Math.ceil(measuredHeight / geometry.pageHeightPx));
  return {
    pageCount,
    height: Math.max(result.height, measuredHeight, pageCount * geometry.pageHeightPx),
    spacers: result.spacers,
  };
}
