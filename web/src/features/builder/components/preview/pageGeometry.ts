/**
 * Geometry shared by the live preview's A4 canvas and paginator.
 *
 * Chromium resolves CSS physical units at 96dpi. Keeping the source values in
 * millimetres makes the relationship to the PDF's `@page { size: A4 }` rule
 * explicit while the pixel values let the browser position overlay elements.
 */

export const CSS_DPI = 96;
export const MILLIMETRES_PER_INCH = 25.4;
export const A4_WIDTH_MM = 210;
export const A4_HEIGHT_MM = 297;
export const PRINT_TOP_MARGIN_PX = 24;

export const PAGE_WIDTH_PX = (A4_WIDTH_MM / MILLIMETRES_PER_INCH) * CSS_DPI;
export const PAGE_HEIGHT_PX = (A4_HEIGHT_MM / MILLIMETRES_PER_INCH) * CSS_DPI;
export const PRINTABLE_PAGE_HEIGHT_PX = PAGE_HEIGHT_PX - PRINT_TOP_MARGIN_PX;

export interface PageGeometry {
  pageWidthPx: number;
  pageHeightPx: number;
  topMarginPx: number;
  printableHeightPx: number;
}

export const A4_PAGE_GEOMETRY: PageGeometry = {
  pageWidthPx: PAGE_WIDTH_PX,
  pageHeightPx: PAGE_HEIGHT_PX,
  topMarginPx: PRINT_TOP_MARGIN_PX,
  printableHeightPx: PRINTABLE_PAGE_HEIGHT_PX,
};

/** Scale the fixed-width canvas to fit its preview viewport. */
export function scaleForAvailableWidth(availableWidthPx: number): number {
  if (!Number.isFinite(availableWidthPx) || availableWidthPx <= 0) return 1;
  return Math.min(1, availableWidthPx / PAGE_WIDTH_PX);
}

