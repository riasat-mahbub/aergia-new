import type { Zone } from "./types";

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
