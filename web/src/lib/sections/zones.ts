import type { Zone } from "./types";

// The editor's interactive width handling: when the user drags a
// divider, the system computes percentages and the resolver maps
// them to width tokens at the wire boundary. The manifest only ever
// carries the tokens; the percentages are an editor concern.

type WidthToken = "narrow" | "half" | "full" | "auto";

export function getWidthPercent(zone: Zone): number {
  const w = zone.styles?.width || "";
  if (w === "auto") return 0;
  if (w === "narrow") return 30;
  if (w === "half") return 50;
  if (w === "full") return 100;
  // Legacy raw CSS — best-effort.
  const num = parseInt(w.replace("%", ""));
  return isNaN(num) ? 0 : num;
}

export function percentToToken(percent: number): WidthToken {
  if (percent <= 35) return "narrow";
  if (percent <= 65) return "half";
  if (percent >= 95) return "full";
  return "auto";
}

// Editor preview needs CSS values for the zone wrapper. The manifest's
// token values are renderer-independent; the editor maps them to the
// values its CSS engine understands. The backend resolver does the
// same mapping for the actual PDF/HTML output.
export function widthTokenToCss(token: string | null | undefined): string {
  if (!token) return "100%";
  if (token === "narrow") return "30%";
  if (token === "half") return "50%";
  if (token === "full") return "100%";
  if (token === "auto") return "auto";
  return token;
}

export function spacingTokenToCss(token: string | null | undefined): string {
  if (!token) return "0";
  if (token === "none") return "0";
  if (token === "tight") return "12px";
  if (token === "comfortable") return "24px";
  if (token === "loose") return "32px";
  return token;
}

export function normalizeWidths(zones: Zone[]): Zone[] {
  if (zones.length === 0) return zones;

  // Step 1: parse each zone's width into a percentage. "auto" zones
  // carry 0 and get a share of the remaining space.
  const rawWidths = zones.map((z) => getWidthPercent(z));
  const total = rawWidths.reduce((sum, w) => sum + Math.max(0, w), 0);
  if (total === 0) {
    return zones.map((z) => ({ ...z, styles: { ...z.styles, width: "full" } }));
  }

  const autoCount = rawWidths.filter((w) => w === 0).length;
  const fixedTotal = rawWidths.reduce((sum, w) => sum + (w > 0 ? w : 0), 0);
  const remaining = autoCount > 0 ? Math.max(0, 100 - fixedTotal) : 0;
  const autoWidth = autoCount > 0 ? remaining / autoCount : 0;
  const finalWidths = rawWidths.map((w) => (w === 0 ? autoWidth : w));

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
    styles: { ...z.styles, width: percentToToken(intParts[i]) },
  }));
}
