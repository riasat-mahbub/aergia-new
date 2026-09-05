/** Placement shape and migration helpers for manifest-backed layouts. */

import type { LayoutDefaults, PolicyOverrides, TemplateManifest, Zone } from "./schema";

export interface LayoutConfig {
  zones: Zone[];
  placement: Record<string, string>;
  manifest_version?: 2;
  name?: string;
  description?: string | null;
  layout_defaults?: LayoutDefaults;
  policy_overrides?: PolicyOverrides;
  global_styles?: Record<string, string>;
}

export function getFirstZoneId(
  manifest: TemplateManifest | LayoutConfig | null | undefined,
): string | undefined {
  return manifest?.zones?.[0]?.id;
}

function isTypeBasedPlacement(placement: Record<string, string>): boolean {
  const keys = Object.keys(placement);
  if (keys.length === 0) return false;
  return keys.some((key) => !key.startsWith("sec_"));
}

export function migratePlacement(
  manifest: TemplateManifest | LayoutConfig | null | undefined,
  instances: Array<{ id: string; type: string }>,
): TemplateManifest | LayoutConfig | null | undefined {
  if (!manifest) return manifest;
  const placement = manifest.placement || {};
  if (!isTypeBasedPlacement(placement)) return manifest;

  const newPlacement: Record<string, string> = {};
  for (const instance of instances) {
    const zoneId = placement[instance.type];
    if (zoneId) newPlacement[instance.id] = zoneId;
  }
  return { ...manifest, placement: newPlacement };
}
