import type { Zone } from "./types";

export const MIN_ROW_PCT = 10;

export function getWidthPercent(zone: Zone): number {
  const w = zone.styles?.width || "";
  const num = parseInt(w.replace("%", ""));
  return isNaN(num) ? 0 : num;
}

export function normalizeWidths(zones: Zone[]): Zone[] {
  if (zones.length === 0) return zones;

  const rawWidths = zones.map((z) => {
    const w = z.styles?.width || "";
    const num = parseInt(w.replace("%", ""));
    if (isNaN(num) || num <= 0) return -1;
    return num;
  });

  const total = rawWidths.reduce((sum, w) => sum + Math.max(0, w), 0);
  if (total === 0) {
    const equal = Math.floor(100 / zones.length);
    return zones.map((z, i) => ({
      ...z,
      styles: { ...z.styles, width: `${equal + (i === 0 ? 100 - equal * zones.length : 0)}%` },
    }));
  }

  const autoCount = rawWidths.filter((w) => w < 0).length;
  const remaining = autoCount > 0 ? Math.max(0, 100 - total) : 0;
  const autoWidth = autoCount > 0 ? remaining / autoCount : 0;
  const finalWidths = rawWidths.map((w) => (w < 0 ? autoWidth : w));

  const totalFinal = finalWidths.reduce((s, v) => s + v, 0);
  const exact = finalWidths.map((w) => (w / totalFinal) * 100);
  const intParts = exact.map((w) => Math.floor(w));
  const remainderParts = exact.map((w, i) => ({ index: i, remainder: w - Math.floor(w) }));
  remainderParts.sort((a, b) => b.remainder - a.remainder);
  let rem = 100 - intParts.reduce((s, w) => s + w, 0);
  for (let i = 0; i < rem; i++) {
    intParts[remainderParts[i].index]++;
  }

  return zones.map((z, i) => ({
    ...z,
    styles: { ...z.styles, width: `${intParts[i]}%` },
  }));
}

export function getRowNumbers(zones: Zone[]): number[] {
  const rows = new Set<number>();
  for (const z of zones) rows.add(z.row ?? 0);
  return [...rows].sort((a, b) => a - b);
}

export function groupByRow(zones: Zone[]): Map<number, Zone[]> {
  const rows = new Map<number, Zone[]>();
  for (const z of zones) {
    const r = z.row ?? 0;
    if (!rows.has(r)) rows.set(r, []);
    rows.get(r)!.push(z);
  }
  return rows;
}

export function getRowHeightPercent(rowNum: number, rowNumbers: number[], rowHeights?: Record<number, string>): number {
  if (rowHeights && rowHeights[rowNum] !== undefined) {
    const num = parseInt(rowHeights[rowNum].replace("%", ""));
    if (!isNaN(num) && num > 0) return num;
  }
  return Math.floor(100 / rowNumbers.length);
}

export function normalizeRowHeights(rowNumbers: number[], rowHeights?: Record<number, string>): Record<number, string> {
  if (rowNumbers.length === 0) return {};
  if (rowNumbers.length === 1) return { [rowNumbers[0]]: "100%" };

  const raw = rowNumbers.map((r) => {
    const h = rowHeights?.[r] || "";
    const num = parseInt(h.replace("%", ""));
    if (isNaN(num) || num < MIN_ROW_PCT) return -1;
    return num;
  });

  const total = raw.reduce((s, w) => s + Math.max(0, w), 0);
  if (total === 0) {
    const equal = Math.floor(100 / rowNumbers.length);
    const result: Record<number, string> = {};
    rowNumbers.forEach((r, i) => {
      result[r] = `${equal + (i === 0 ? 100 - equal * rowNumbers.length : 0)}%`;
    });
    return result;
  }

  const autoCount = raw.filter((w) => w < 0).length;
  const remaining = autoCount > 0 ? Math.max(0, 100 - total) : 0;
  const autoH = autoCount > 0 ? remaining / autoCount : 0;
  const final = raw.map((w) => (w < 0 ? autoH : w));

  const totalFinal = final.reduce((s, v) => s + v, 0);
  const exact = final.map((w) => (w / totalFinal) * 100);
  const intParts = exact.map((w) => Math.floor(w));
  const remainderParts = exact.map((w, i) => ({ index: i, remainder: w - Math.floor(w) }));
  remainderParts.sort((a, b) => b.remainder - a.remainder);
  let rem = 100 - intParts.reduce((s, w) => s + w, 0);
  for (let i = 0; i < rem; i++) {
    intParts[remainderParts[i].index]++;
  }

  const result: Record<number, string> = {};
  rowNumbers.forEach((r, i) => {
    result[r] = `${intParts[i]}%`;
  });
  return result;
}

export function normalizeAllZones(zones: Zone[]): Zone[] {
  const grouped = groupByRow(zones);
  const normalized: Zone[] = [];
  for (const [, rowZones] of grouped) {
    normalized.push(...normalizeWidths(rowZones));
  }
  return normalized;
}
