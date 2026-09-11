/** Helpers for canonical manifest/CV layout placement. */

import type { Zone } from "./schema";

export function getFirstZoneId(
  layout: { zones?: Zone[] } | null | undefined,
): string | undefined {
  return layout?.zones?.[0]?.id;
}
