# HTML-first AST pipeline — Phase 2 (crystalised plan v5)

**Branch:** `feat/ast-pipeline`, on top of the uncommitted Phase 1 working tree.
**Goal:** The customize panel writes only `style.layout / .subsection / .policy / .text[key]` keys on `SectionInstanceStyle`. Per-CV `Customizations` accepts only canonical v2 fields (`accent_color / body_font / heading_font / default_text_align / spacing / flags / per_section`). Legacy keys (`font`, `color`, `weight`, `text_align`, `show_title:boolean`, `subsection_gap`, `row_gap`, `field_styles`, `layout: "block"|"inline"`, top-level `{colors, fonts, spacing, flags}`) are NEVER set by the frontend. Legacy rows in the DB migrate on read; legacy field keys on `SectionInstance.style` are silently dropped by `extra="ignore"`.

**Scope explicit:** Phase 2 does not touch the template authoring path. `TemplateWizard` and `StyleEditor` are dead-code stubbed in this phase and rebuilt in Phase 3.

**No global Customizations UI in the panel.** Per-CV body font / accent color / heading font / spacing continues to flow from `manifest.global_styles` only. Users cannot override these globally in this phase — that re-instates Phase 3 with the wizard.

## Tracker entries to author before any code

In `tracker/`:

1. `tracker/features/FEAT-01KZJ0PHASE2QA-phase-2-customize-panel-three-axis.md` — this plan.
2. `tracker/bugs/BUG-01KZJ0PHASE2QA-customizations-wire-mismatch.md` — `Customizations` silently drops the panel's legacy `colors/fonts/spacing/flags` keys. Fix: Step 1.
3. `tracker/bugs/BUG-01KZJ0PHASE2QA-template-wizard-on-legacy-paths.md` — `TemplateWizard` writes the v1 `default_customizations` shape. Stubbed in Phase 2; real fix is Phase 3.
4. `tracker/tasks/TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations.md` — placeholder for Phase 3.

The ULIDs above are placeholders — replace with generated ones if `tracker new` is available, or hand-author.

## File deltas — Phase 2

### Backend

| File | Change |
|---|---|
| `api/app/schema/models.py` | Add `model_validator(mode="before")` on `Customizations` to reject legacy `{colors, fonts}` top-level keys. Drop `legacy_style` field from `SectionInstance`. |
| `api/app/services/legacy_customizations.py` (new) | `migrate_legacy_customizations(raw: dict) -> dict` — converts legacy `{colors, fonts, spacing, flags}` into canonical fields. |
| `api/app/services/cv.py` | Add `coerce_customizations(raw: dict | None) -> Customizations` thin helper that runs the legacy migrator then `Customizations.model_validate`. |
| `api/app/services/renderer/resolve.py` | Replace no-op `_drop_none_features` with real gating (zero `break_before`, `keep_together`, `heading_keeps_with_first` when their `RendererSupport` is `NONE`). |
| `api/app/routes/render.py:82` | Use `coerce_customizations` from `services/cv.py`. |
| `api/app/routes/cvs.py:125` | Use `coerce_customizations`. |
| `api/app/services/pdf.py:35` | Use `coerce_customizations`. |
| `api/app/services/renderer/builders/__init__.py:170-180` | Drop `legacy=instance.legacy_style` argument from `build_document`. |
| `api/tests/test_legacy_customizations.py` (new) | 6 tests for the migrator. |
| `api/tests/test_schema.py` | Add `test_customizations_rejects_legacy_top_level`. Delete `test_section_instance_legacy_style_round_trips`. |
| `api/tests/test_resolve.py` | Add 2 tests: `test_support_none_zeroes_layout_hints`, `test_support_full_preserves_layout_hints`. |
| `api/tests/test_builders.py` | Delete `test_legacy_style_overrides_apply_to_section_three_axes` (or rewrite it). |

### Frontend

| File | Change |
|---|---|
| `web/src/lib/api/render.ts` (new) | `fetchRendererSupport(): Promise<SupportMap>`. |
| `web/src/lib/store/supportStore.ts` (new) | Zustand store with `support: SupportMap \| null`, `loaded`, `error`, `ensureLoaded`, `retry`, `reset`. |
| `web/src/pages/BuilderPage.tsx` | Mount `ensureLoaded()` once via `useEffect`. Drop `SectionStyle` import. Replace `sectionStyleHasValues` with three-axis predicate. Narrow `handleUpdateStyle` param to `SectionInstanceStyle`. |
| `web/src/components/customization/CustomizePanel.tsx` | Rewrite per plan below. Delete `StyleEditor` import, `globalStyleSchema` prop, the `<StyleEditor title="Global">` render, legacy-keyed controls. Four new helpers. Three `<details>` groups gated by `useSupportStore`. `FieldStyleRow` Font select dropped, size options become enum names (`xs/small/normal/large/xl`), weight maps to `bold: boolean`. |
| `web/src/components/customization/StyleEditor.tsx` | **DELETE.** Verify zero consumers before deletion. |
| `web/src/components/template-creator/TemplateWizard.tsx` | Stub with a deprecated banner linking to the Phase 3 tracker entry. |
| `web/src/lib/validators/sections.ts` | Add `customizationsSchema` (canonical fields, `.strict()`). Add `styleSchema` with three-axis sub-schemas matching `SectionInstanceStyle`. |
| `web/src/lib/sections/types.ts` | Drop the legacy `SectionStyle` interface alias if `grep` confirms zero remaining usages after Step 6. |
| `web/src/lib/store/__tests__/supportStore.test.ts` (new) | 4 tests: load, no-double-fetch, fail-open, retry. |
| `web/src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts` | Rewrite 3 tests to three-axis shape. |
| `web/src/components/__tests__/CustomizePanel.test.tsx` | Delete Global tests + the `describe("globalStyleSchema")` block. Rewrite "changing the color" / "clearing all style values" tests for three-axis payload. Update "Skills layout" assertion to `policy: { skill_variant: "inline", show_title: true }`. Update `rangeSep` to read `style.layout.date_style.rangeSep`. |
| `web/src/lib/validators/__tests__/sections.test.ts` | Add tests covering the new `customizationsSchema` (canonical pass, legacy rejected) and `sectionInstanceSchema` (three-axis pass, legacy keys rejected, strict). |
| `PLAN.md` | Add a Phase 2 entry referencing the tracker ID. |
| `AGENTS.md` | Brief note that `StyleEditor.tsx`, `TemplateWizard.tsx`, and the per-CV `{colors,fonts,spacing,flags}` shape are deferred to Phase 3. |

## Step 1 — `Customizations` wire cut (the bug fix)

### `api/app/services/legacy_customizations.py` (new)

```python
"""Legacy customizations migration (Phase 2).

Phase 1 silently dropped the legacy ``{colors, fonts, spacing, flags}``
shape from per-CV writes because ``Customizations`` only declared
``accent_color, body_font, heading_font, ...``. The customize panel and
the template wizard both kept writing the legacy shape, so user edits
to accent / body font / heading font were silently lost.

Phase 2 cuts over: ``Customizations`` rejects those top-level keys at
the boundary via ``model_validator(mode="before")``. Legacy rows still
live in the DB; this module provides a one-shot migrator so legacy
reads still produce a working CSS cascade.
"""

from __future__ import annotations


_SPACING_LEGACY_TO_PRESET = {"16px": "compact", "20px": "compact", "8px": "minimal"}


def migrate_legacy_customizations(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return raw or {}
    if not ({"colors", "fonts"} & set(raw.keys())):
        return raw  # already canonical or empty

    colors = raw.get("colors") or {}
    fonts = raw.get("fonts") or {}
    legacy_spacing = (raw.get("spacing") or {}).get("section_gap")
    if legacy_spacing in _SPACING_LEGACY_TO_PRESET:
        spacing_preset = _SPACING_LEGACY_TO_PRESET[legacy_spacing]
    elif legacy_spacing is not None:
        spacing_preset = "comfortable"
    else:
        spacing_preset = None

    canonical = {
        k: v for k, v in raw.items()
        if k not in {"colors", "fonts", "spacing", "flags"}
    }
    canonical.setdefault("accent_color",
        colors.get("accent") or colors.get("header")
        or colors.get("heading") or colors.get("text"),
    )
    if canonical["accent_color"] is None:
        del canonical["accent_color"]
    if fonts.get("body"):
        canonical["body_font"] = fonts["body"]
    if fonts.get("heading"):
        canonical["heading_font"] = fonts["heading"]
    if spacing_preset:
        canonical["spacing"] = spacing_preset
    return canonical
```

### `api/app/schema/models.py:293` — validator on `Customizations`

```python
from pydantic import BaseModel, Field, model_validator


class Customizations(BaseModel):
    """Canonical v2 customization shape (per CV)."""

    accent_color: str | None = None
    body_font: str | None = None
    heading_font: str | None = None
    default_text_align: Literal["left", "right", "center", "justify"] | None = None
    spacing: Literal["compact", "comfortable", "minimal"] | None = None
    flags: dict[str, bool] = Field(default_factory=dict)
    per_section: dict[str, SectionInstanceStyle] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy(cls, data):
        if not isinstance(data, dict):
            return data
        legacy = {"colors", "fonts"} & set(data.keys())
        if legacy:
            raise ValueError(
                f"Legacy customizations shape rejected ({sorted(legacy)}). "
                f"Use accent_color / body_font / heading_font instead."
            )
        return data
```

### `api/app/services/cv.py` — `coerce_customizations` helper

```python
from app.schema.models import Customizations
from app.services.legacy_customizations import migrate_legacy_customizations


def coerce_customizations(raw: dict | None) -> Customizations:
    """Validate raw DB customizations to the canonical Customizations model.

    Migrates the legacy v1 ``{colors, fonts, spacing, flags}`` shape on
    read so legacy CVs continue to render correctly until each user
    re-saves their CV.
    """
    raw = raw or {}
    migrated = migrate_legacy_customizations(raw)
    return Customizations.model_validate(migrated)
```

Update three call-sites to use `coerce_customizations`:
- `api/app/routes/render.py:82` — replace `_coerce_customizations` body with `coerce_customizations`.
- `api/app/routes/cvs.py:125` — replace `Customizations.model_validate(cv.customizations or {})` with `coerce_customizations(cv.customizations)`.
- `api/app/services/pdf.py:35` — same replacement.

### Tests

`api/tests/test_legacy_customizations.py` (new):

```python
from app.services.legacy_customizations import migrate_legacy_customizations


def test_no_legacy_keys_returns_input_unchanged():
    raw = {"accent_color": "#abc", "body_font": "Inter"}
    assert migrate_legacy_customizations(raw) == raw


def test_legacy_colors_accent_maps_to_accent_color():
    out = migrate_legacy_customizations({"colors": {"accent": "#ff0000"}})
    assert out["accent_color"] == "#ff0000"
    assert "colors" not in out


def test_legacy_fallback_header_used_when_accent_missing():
    out = migrate_legacy_customizations({"colors": {"header": "#000000"}})
    assert out["accent_color"] == "#000000"


def test_legacy_fonts_maps_to_body_and_heading():
    out = migrate_legacy_customizations({"fonts": {"body": "Inter", "heading": "Georgia"}})
    assert out["body_font"] == "Inter"
    assert out["heading_font"] == "Georgia"
    assert "fonts" not in out


def test_legacy_section_gap_20px_maps_to_compact():
    out = migrate_legacy_customizations({"spacing": {"section_gap": "20px"}})
    assert out["spacing"] == "compact"


def test_per_section_passthrough():
    raw = {"colors": {"accent": "#abc"}, "per_section": {"p": {"subsection": {"section_color": "#f00"}}}}
    out = migrate_legacy_customizations(raw)
    assert out["per_section"] == {"p": {"subsection": {"section_color": "#f00"}}}


def test_empty_input_returns_empty():
    assert migrate_legacy_customizations({}) == {}
```

`api/tests/test_schema.py` — add:

```python
import pytest
from pydantic import ValidationError
from app.schema.models import Customizations


def test_customizations_rejects_legacy_top_level():
    with pytest.raises(ValidationError):
        Customizations.model_validate({"colors": {"accent": "#abc"}})


def test_customizations_rejects_legacy_fonts():
    with pytest.raises(ValidationError):
        Customizations.model_validate({"fonts": {"body": "Inter"}})


def test_customizations_accepts_canonical_shape():
    c = Customizations.model_validate({"accent_color": "#abc", "body_font": "Inter"})
    assert c.accent_color == "#abc"
    assert c.body_font == "Inter"
```

### Gate after Step 1

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q   # expect 159 passed (was 150 baseline, +9 new tests, no removals yet)
```

## Step 2 — Resolver capability gating

### `api/app/services/renderer/resolve.py:219` — replace no-op

```python
def _drop_none_features(model: RenderModel, support: RendererSupport) -> RenderModel:
    """Zero layout flags whose renderer capability is NONE.

    Per-section fields with resolver mappings: ``break_before``,
    ``keep_together``, ``heading_keeps_with_first``. Gating lives here
    so the panel can disable a feature without leaving its CSS emitted.

    No-op markers — ``keep_with_next``, ``feature_section_underline``,
    ``feature_anchor_styling`` — have no per-section resolver mapping
    today; the renderer ignores them regardless of support level. The
    panel hides their controls on NONE but the resolver does not act.
    """
    none_fields = [
        f for f in ("break_before", "keep_together", "heading_keeps_with_first")
        if getattr(support, f) is SupportLevel.NONE
    ]
    if not none_fields:
        return model

    def _strip(section: Section) -> Section:
        if section.layout is None:
            return section
        layout = section.layout
        updates: dict[str, object] = {}
        for f in none_fields:
            if getattr(layout, f):
                updates[f] = False
        if not updates:
            return section
        return section.model_copy(update={"layout": layout.model_copy(update=updates)})

    new_sections = {sid: _strip(s) for sid, s in model.sections.items()}
    return model.model_copy(update={"sections": new_sections})
```

### Tests in `api/tests/test_resolve.py`

```python
def test_support_none_zeroes_layout_hints():
    support = RendererSupport(
        break_before=SupportLevel.NONE,
        keep_together=SupportLevel.NONE,
        heading_keeps_with_first=SupportLevel.NONE,
    )
    doc = Document(sections=[Section(
        id="p", type="profile", title="P", enabled=True,
        layout=LayoutHints(
            break_before=True,
            keep_together=True,
            heading_keeps_with_first=True,
        ),
        entries=[Entry(id="e1", fields=[])],
    )])
    sec = resolve(doc, None, Customizations(), support).sections["p"]
    assert sec.layout.break_before is False
    assert sec.layout.keep_together is False
    assert sec.layout.heading_keeps_with_first is False


def test_support_full_preserves_layout_hints():
    """FULL/BEST_EFFORT levels don't touch layout hints."""
    doc = Document(sections=[Section(
        id="p", type="profile", title="P", enabled=True,
        layout=LayoutHints(break_before=True),
        entries=[Entry(id="e1", fields=[])],
    )])
    sec = resolve(doc, None, Customizations(), RendererSupport()).sections["p"]
    assert sec.layout.break_before is True
```

The existing `test_support_with_skills_inline_none_forces_block_variant` is unaffected — the `feature_skills_inline` gate still runs at `resolve()` lines 277-281, BEFORE `_drop_none_features`.

### Gate after Step 2

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q   # expect 161 passed
```

## Step 3 — `legacy_style` removal

- `api/app/schema/models.py:SectionInstance` — drop `legacy_style: dict | None = None`.
- `api/app/services/renderer/builders/__init__.py:170-180` — drop `legacy=instance.legacy_style` argument from `build_document`. Locate the `build_section_style` definition and remove its `legacy` parameter; simplify the body to merge `instance_style` over template defaults only.
- `api/app/schemas/cv.py` doc-comment cleanup — remove the `legacy_style round-trips` reference.
- Delete `api/tests/test_schema.py:test_section_instance_legacy_style_round_trips`.
- Delete `api/tests/test_builders.py:test_legacy_style_overrides_apply_to_section_three_axes` (or rewrite to test the direct `instance_style` path).
- `cd api && .venv/bin/python scripts/codegen_schema.py` — rerun. `web/src/generated/schema.ts` regenerates without `legacy_style`.
- `grep -rn 'legacy_style' api/ web/src` → must be zero.

### Gate after Step 3

```bash
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q            # 159 passed
cd api && .venv/bin/python scripts/codegen_schema.py --check           # exit 0
```

## Step 4 — Frontend: render client + Zustand store

### `web/src/lib/api/render.ts` (new)

```ts
import client from "./client";
import type { RendererSupport } from "../../generated/schema";

const SUPPORT_VALUES = ["FULL", "BEST_EFFORT", "NONE"] as const;
export type SupportLevelValue = (typeof SUPPORT_VALUES)[number];
export type SupportField = keyof RendererSupport;
export type SupportMap = Record<SupportField, SupportLevelValue>;

export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}
```

### `web/src/lib/store/supportStore.ts` (new)

```ts
import { create } from "zustand";
import { fetchRendererSupport, type SupportMap } from "../api/render";

interface SupportState {
  support: SupportMap | null;
  loaded: boolean;
  error: string | null;
  ensureLoaded: () => Promise<void>;
  retry: () => Promise<void>;
  reset: () => void;  // tests only
}

export const useSupportStore = create<SupportState>((set, get) => ({
  support: null,
  loaded: false,
  error: null,
  ensureLoaded: async () => {
    if (get().loaded) return;
    try {
      const support = await fetchRendererSupport();
      set({ support, loaded: true, error: null });
    } catch (e) {
      set({ support: null, loaded: true, error: String(e) });
    }
  },
  retry: async () => {
    set({ loaded: false, error: null });
    await get().ensureLoaded();
  },
  reset: () => set({ support: null, loaded: false, error: null }),
}));
```

### `web/src/pages/BuilderPage.tsx` — mount

```tsx
import { useSupportStore } from "../lib/store/supportStore";
// inside component body, alongside existing useEffects:
useEffect(() => { useSupportStore.getState().ensureLoaded(); }, []);
```

### `web/src/lib/store/__tests__/supportStore.test.ts` (new, 4 tests)

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useSupportStore } from "../supportStore";
import * as renderApi from "../../api/render";

vi.mock("../../api/render", () => ({ fetchRendererSupport: vi.fn() }));

const FULL_SUPPORT = {
  break_before: "FULL",
  keep_together: "FULL",
  keep_with_next: "FULL",
  heading_keeps_with_first: "FULL",
  feature_skills_inline: "FULL",
  feature_section_underline: "FULL",
  feature_anchor_styling: "FULL",
} as const;

describe("supportStore", () => {
  beforeEach(() => {
    useSupportStore.getState().reset();
    vi.clearAllMocks();
  });

  it("ensureLoaded populates support on first call", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    expect(useSupportStore.getState().loaded).toBe(true);
    expect(useSupportStore.getState().support?.break_before).toBe("FULL");
  });

  it("ensureLoaded does not refetch on second call", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    await useSupportStore.getState().ensureLoaded();
    expect(renderApi.fetchRendererSupport).toHaveBeenCalledTimes(1);
  });

  it("failures store support=null with error populated (fail-open)", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockRejectedValueOnce(new Error("network"));
    await useSupportStore.getState().ensureLoaded();
    expect(useSupportStore.getState().support).toBeNull();
    expect(useSupportStore.getState().error).toMatch(/network/);
    expect(useSupportStore.getState().loaded).toBe(true);
  });

  it("retry refetches after a failure", async () => {
    vi.mocked(renderApi.fetchRendererSupport)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    await useSupportStore.getState().retry();
    expect(useSupportStore.getState().support?.break_before).toBe("FULL");
    expect(useSupportStore.getState().error).toBeNull();
  });
});
```

### Gate after Step 4

```bash
cd web && npm run test -- --run src/lib/store/__tests__/supportStore.test.ts   # 4 passed
cd web && npm run build                                                          # 0
```

## Step 5 — `CustomizePanel.tsx` rewrite + dead-code removal

### 5a. `StyleEditor.tsx` — DELETE

Verify zero consumers first: `grep -rn 'StyleEditor' web/src` → only the `CustomizePanel.tsx` reference. After 5c, that reference is gone too. Delete the file.

### 5b. `TemplateWizard.tsx` — STUB

```tsx
// REMOVED in Phase 2 — see tracker/tasks/TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations.md
//
// v2 template creation lives in `POST /templates/user` (uploads a manifest.json).
// This wizard wrote the legacy {colors, fonts, spacing, flags} default_customizations
// shape, which Phase 2 now rejects at the Customizations boundary. It is stubbed
// here until Phase 3 rebuilds it against the v2 TemplateManifest + Customizations.
//
// To restore: git checkout HEAD -- web/src/components/template-creator/TemplateWizard.tsx

export default function TemplateWizard() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <h3 className="text-sm font-medium text-amber-900">Template creator is being rebuilt</h3>
      <p className="mt-1 text-xs text-amber-700">
        The legacy template wizard was incompatible with the v2 manifest pipeline and is
        removed in Phase 2. See the Phase 3 task for the rewrite.
      </p>
    </div>
  );
}
```

### 5c. `CustomizePanel.tsx` — rewrite

Deletes:
- `import StyleEditor, { type StyleVarSchema } from "./StyleEditor"`
- `globalStyleSchema?: StyleVarSchema[]` from `Props`
- `<StyleEditor customizations={customizations} onChange={onChange} title="Global" globalStyleSchema={globalStyleSchema} />` render
- `import type { SectionStyle, FieldStyle }`; switch `Props.onUpdateStyle` to `SectionInstanceStyle`
- `FieldStyleRow`'s Font `<select>` (per your decision)
- All `SectionStyle` legacy-keyed controls

Mapping table (CSS string → enum), reused by size + weight:

```ts
// FieldStyle font_size is a Literal enum in the codegen. The legacy
// FieldStyleRow stored CSS strings; we translate at write time. Snap
// unmapped sizes to the nearest enum bucket.
const FONT_SIZE_CSS: Record<TextStyle["font_size"] & string, string> = {
  xs: "0.75rem", small: "0.875rem", normal: "1rem", large: "1.125rem", xl: "1.25rem",
};
const FONT_SIZE_TO_ENUM = Object.fromEntries(
  Object.entries(FONT_SIZE_CSS).map(([k, v]) => [v, k]),
) as Record<string, NonNullable<TextStyle["font_size"]>>;

function normalizeFontSize(css: string | null | undefined): TextStyle["font_size"] {
  if (!css) return null;
  const direct = FONT_SIZE_TO_ENUM[css];
  if (direct) return direct;
  // nearest-bucket fallback for unmapped CSS strings (e.g. "0.625rem" -> "xs")
  const rem = parseFloat(css);
  if (isNaN(rem)) return null;
  let bestKey: NonNullable<TextStyle["font_size"]> = "normal";
  let bestDelta = Infinity;
  for (const [k, v] of Object.entries(FONT_SIZE_CSS)) {
    const d = Math.abs(parseFloat(v) - rem);
    if (d < bestDelta) { bestDelta = d; bestKey = k as NonNullable<TextStyle["font_size"]>; }
  }
  return bestKey;
}
```

Four write helpers:

```ts
const selectedStyle: SectionInstanceStyle = selectedInstance?.style ?? {};
const writeStyle = (style: SectionInstanceStyle) => {
  if (!selectedSectionId) return;
  onUpdateStyle(selectedSectionId, style);
};

const updateSelectedLayout = (partial: Partial<LayoutHints>) =>
  writeStyle({ ...selectedStyle, layout: { ...(selectedStyle.layout ?? {}), ...partial } });

const updateSelectedSubsection = (partial: Partial<SubsectionStyle>) =>
  writeStyle({ ...selectedStyle, subsection: { ...(selectedStyle.subsection ?? {}), ...partial } });

const updateSelectedPolicy = (partial: Partial<SectionPolicy>) =>
  writeStyle({ ...selectedStyle, policy: { ...(selectedStyle.policy ?? {}), ...partial } });

const updateSelectedFieldText = (field: string, partial: Partial<TextStyle>) => {
  const current = selectedStyle.text ?? {};
  writeStyle({
    ...selectedStyle,
    text: { ...current, [field]: { ...(current[field] ?? {}), ...partial } },
  });
};
```

`FieldStyleRow` rewrite:
- Remove the Font `<select>`.
- Size `<select>` options = the five enum names, labelled `"xs (0.75rem)"`, etc. Initial selection: `normalizeFontSize(existingValue)` if it was set. Writes: `updateSelectedFieldText(field, { font_size: enum })`.
- Weight `<select>` values: `"normal"` → `bold: false`, `"bold"` → `bold: true`; intermediate values fall through to one of those two states. Writes: `updateSelectedFieldText(field, { bold })`.
- Reset button clears the `font_size`/`bold` from this row's `text[field]`.

JSX layout, three `<details>` disclosure groups:

1. **Layout** — gated individually:
   - Font family `<select>` → `layout.font_family`
   - Break before checkbox → `layout.break_before` (gate `break_before`)
   - Keep together checkbox → `layout.keep_together` (gate `keep_together`)
   - Heading keeps with first checkbox → `layout.heading_keeps_with_first` (gate `heading_keeps_with_first`)
   - Orphans / Widows number inputs → `layout.orphans` / `layout.widows`
   - Date format `<select>` → `layout.date_style` via existing `DATE_STYLE_OPTIONS`

2. **Block style (subsection)** — no gates:
   - Text align → `subsection.text_align`
   - Spacing before / after → `subsection.spacing_before` / `spacing_after`
   - Background color + hex → `subsection.background_color`
   - Section color + hex → `subsection.section_color`

3. **Section policy** — gated by `feature_skills_inline`:
   - Show title toggle → `policy.show_title`
   - Skills layout `<select>` → `policy.skill_variant`, only when `selectedInstance.type === "skills"`

`FieldStyles` group: keep, with the updated `FieldStyleRow`.

Capability gates via local helpers:

```ts
const support = useSupportStore((s) => s.support);
const level = (f: SupportField): "FULL" | "BEST_EFFORT" | "NONE" =>
  support?.[f] ?? "FULL";
const isHidden = (f: SupportField) => level(f) === "NONE";
const isBestEffort = (f: SupportField) => level(f) === "BEST_EFFORT";
```

`AlertTriangle` (lucide-react) on BEST_EFFORT items, `aria-label="Renderer is best-effort for this feature"`. Hide on NONE.

Retry chip at the panel top when `support === null && loaded && error !== null` → button calls `useSupportStore.getState().retry()`. On render with `support === null && !loaded` (initial), no chip — the first fetch is in flight.

### Gate after Step 5

```bash
cd web && grep -rn 'StyleEditor' web/src --include='*.tsx' --include='*.ts'   # zero
cd web && grep -rn 'TemplateWizard.*onChange\|TemplateWizard.*onSave\|StyleEditor' web/src --include='*.tsx' --include='*.ts'   # zero (only the stub itself)
cd web && npm run build
```

(`CustomizePanel.test.tsx` rewrites happen in Step 6d; the suite still passes with the legacy-asserting tests removed/rewritten there.)

## Step 6 — Test rewrites + persistence gate + validators

### 6a. `web/src/pages/BuilderPage.tsx:527` — `sectionStyleHasValues`

```ts
export function sectionStyleHasValues(style: SectionInstanceStyle): boolean {
  return Boolean(
    (style.layout && Object.keys(style.layout).length > 0) ||
    (style.subsection && Object.keys(style.subsection).length > 0) ||
    (style.policy && Object.keys(style.policy).length > 0) ||
    (style.text && Object.keys(style.text).length > 0)
  );
}
```

### 6b. `web/src/pages/BuilderPage.tsx:277` — narrow `handleUpdateStyle`

```ts
const handleUpdateStyle = useCallback(
  (sectionId: string, style: SectionInstanceStyle) => {
    hasChangesRef.current = true;
    setHasUnsavedChanges(true);
    const hasValues = sectionStyleHasValues(style);
    setLocalInstances((prev) =>
      prev.map((i) =>
        i.id === sectionId ? { ...i, style: hasValues ? style : undefined } : i
      )
    );
  },
  []
);
```

Drop `import type { SectionStyle }` from `BuilderPage.tsx` if it's the only remaining use.

### 6c. `web/src/components/customization/CustomizePanel.tsx` — narrow prop

```ts
onUpdateStyle: (id: string, style: SectionInstanceStyle) => void;
```

### 6d. `web/src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts` — rewrite 3 tests

```ts
it("returns true when only layout is set with a non-empty pick", () => {
  expect(sectionStyleHasValues({ layout: { font_family: "Inter" } })).toBe(true);
});

it("returns true when only text is set with a per-field style", () => {
  expect(sectionStyleHasValues({ text: { name: { font_size: "small" } } })).toBe(true);
});

it("returns false for an empty style object (clears the field)", () => {
  expect(sectionStyleHasValues({})).toBe(false);
});
```

### 6e. `web/src/components/__tests__/CustomizePanel.test.tsx` — sweep

Delete:
- `it("renders Global section with color pickers by default")`
- `it("calls onChange when color is changed")` (global)
- The entire `describe("globalStyleSchema prop")` block

Rewrite:
- `it("changing the color in the per-section style panel calls onUpdateStyle with the new style")` → click profile section, change Section color hex, assert `expect.objectContaining({ subsection: { section_color: "#ff0000" } })`.
- `it("clearing all style values calls onUpdateStyle with an empty object")` → reset all three-axis fields, assert `onUpdateStyle` called with `{}`.
- "Skills layout" assertion: change `expect.objectContaining({ layout: "inline" })` → `expect.objectContaining({ policy: { skill_variant: "inline", show_title: true } })`.
- `rangeSep` assertion: read from `style.layout.date_style.rangeSep`.

Keep:
- layout-view, click-reveals-controls, readOnly, Text Align, Per-field typography (now sans `font`), Date Style, T48 trio.

Final grep on the test file for legacy keys — must be zero:
```bash
grep -nE '"font":|"color":|"weight":|subsection_gap|row_gap|"field_styles"|layout: "block"|layout: "inline"' web/src/components/__tests__/CustomizePanel.test.tsx
```

### 6f. `web/src/lib/validators/sections.ts` — three-axis validators

```ts
import { z } from "zod";
import type {
  Customizations, DateStyle, LayoutHints, SectionInstanceStyle, SectionPolicy,
  SubsectionStyle, TextStyle,
} from "../../generated/schema";

const textStyleSchema: z.ZodType<TextStyle> = z.object({
  bold: z.boolean().optional(),
  italic: z.boolean().optional(),
  underline: z.boolean().optional(),
  strike: z.boolean().optional(),
  color: z.string().nullable().optional(),
  link: z.string().nullable().optional(),
  font_size: z.union([
    z.literal("xs"), z.literal("small"), z.literal("normal"),
    z.literal("large"), z.literal("xl"),
  ]).nullable().optional(),
}).strict();

const dateStyleSchema: z.ZodType<DateStyle> = z.object({
  key: z.string().optional(),
  rangeSep: z.string().optional(),
}).strict();

const subsectionStyleSchema: z.ZodType<SubsectionStyle> = z.object({
  text_align: z.union([
    z.literal("left"), z.literal("right"),
    z.literal("center"), z.literal("justify"),
  ]).nullable().optional(),
  spacing_before: z.string().nullable().optional(),
  spacing_after: z.string().nullable().optional(),
  background_color: z.string().nullable().optional(),
  section_color: z.string().nullable().optional(),
}).strict();

const layoutHintsSchema: z.ZodType<LayoutHints> = z.object({
  font_family: z.string().nullable().optional(),
  date_style: dateStyleSchema.nullable().optional(),
  break_before: z.boolean().optional(),
  keep_together: z.boolean().optional(),
  heading_keeps_with_first: z.boolean().optional(),
  orphans: z.number().optional(),
  widows: z.number().optional(),
}).strict();

const sectionPolicySchema: z.ZodType<SectionPolicy> = z.object({
  show_title: z.boolean().optional(),
  skill_variant: z.union([z.literal("block"), z.literal("inline")]).nullable().optional(),
}).strict();

const sectionInstanceStyleSchema: z.ZodType<SectionInstanceStyle> = z.object({
  layout: layoutHintsSchema.optional(),
  subsection: subsectionStyleSchema.optional(),
  policy: sectionPolicySchema.optional(),
  text: z.record(z.string(), textStyleSchema).optional(),
}).strict();

export const sectionInstanceSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1),
  title: z.string().min(1),
  enabled: z.boolean(),
  data: z.unknown(),
  style: sectionInstanceStyleSchema.optional(),
}).strict();

// Canonical Customizations schema. Strips legacy keys with a strict error
// (the Backend Customizations model already rejects them, this enforces
// the same on the frontend at save time).
export const customizationsSchema: z.ZodType<Customizations> = z.object({
  accent_color: z.string().nullable().optional(),
  body_font: z.string().nullable().optional(),
  heading_font: z.string().nullable().optional(),
  default_text_align: z.union([
    z.literal("left"), z.literal("right"),
    z.literal("center"), z.literal("justify"),
  ]).nullable().optional(),
  spacing: z.union([
    z.literal("compact"), z.literal("comfortable"), z.literal("minimal"),
  ]).nullable().optional(),
  flags: z.record(z.string(), z.boolean()).optional(),
  per_section: z.record(z.string(), sectionInstanceStyleSchema).optional(),
}).strict();

export const sectionInstancesSchema = z.array(sectionInstanceSchema);
```

JSDoc note: the codegen-derived `SectionInstanceStyle` interface in `generated/schema.ts` is open (`extra: ignore`); the validator is the strict gate. The two are intentionally different.

### 6g. `web/src/lib/validators/__tests__/sections.test.ts` — extend

Append (do not delete existing tests):

```ts
import { sectionInstanceSchema, customizationsSchema } from "../sections";
import { it as it_v, describe as describe_v, expect as expect_v } from "vitest";

describe_v("sectionInstanceSchema three-axis", () => {
  it_v("accepts a three-axis style on a profile section", () => {
    const ok = sectionInstanceSchema.parse({
      id: "p1", type: "profile", title: "Profile", enabled: true, data: {},
      style: {
        layout: { font_family: "Inter", break_before: true },
        subsection: { text_align: "left", section_color: "#ff0000" },
        policy: { show_title: true },
        text: { name: { font_size: "small", bold: true } },
      },
    });
    expect_v(ok.style!.layout!.font_family).toBe("Inter");
  });

  it_v("rejects legacy keys on style", () => {
    expect_v(() => sectionInstanceSchema.parse({
      id: "p1", type: "profile", title: "P", enabled: true, data: {},
      style: { font: "Inter" as any },
    })).toThrow();
  });

  it_v("rejects unknown inner-axis keys (strict)", () => {
    expect_v(() => sectionInstanceSchema.parse({
      id: "p1", type: "profile", title: "P", enabled: true, data: {},
      style: { layout: { not_a_field: true } as any },
    })).toThrow();
  });
});

describe_v("customizationsSchema canonical", () => {
  it_v("accepts canonical fields", () => {
    const ok = customizationsSchema.parse({
      accent_color: "#abc", body_font: "Inter", spacing: "compact",
      per_section: { p1: { layout: { font_family: "Inter" } } },
    });
    expect_v(ok.accent_color).toBe("#abc");
    expect_v(ok.spacing).toBe("compact");
  });

  it_v("rejects legacy top-level colors", () => {
    expect_v(() => customizationsSchema.parse({ colors: { accent: "#abc" } })).toThrow();
  });

  it_v("rejects legacy top-level fonts", () => {
    expect_v(() => customizationsSchema.parse({ fonts: { body: "Inter" } })).toThrow();
  });
});
```

Use the file's existing import style — replace `it_v` / `describe_v` / `expect_v` with the file's actual convention after reading.

### 6h. `web/src/lib/sections/types.ts` — drop the legacy alias (if zero uses remain)

Run `grep -rn 'SectionStyle' web/src --include='*.ts' --include='*.tsx'`. If the only survivors are the alias definition itself, delete lines 69-81 (the legacy `SectionStyle` interface). Keep `LegacyZone` (still relevant for migration paths).

### Gate after Step 6

```bash
cd web && npm run test -- --run src/components/__tests__/CustomizePanel.test.tsx
cd web && npm run test -- --run src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts
cd web && npm run test -- --run src/lib/validators/__tests__/sections.test.ts
cd web && npm run build
cd web && grep -rnE 'SectionStyle\b|"globalStyleSchema"|"field_styles"|legacy_style|"colors":\s*\{|"fonts":\s*\{' web/src --include='*.ts' --include='*.tsx'   # zero
```

## Step 7 — Final verification

```bash
# Backend full suite
cd api && rm -f data/aergia.test.db && .venv/bin/pytest -q

# Codegen stability
cd api && .venv/bin/python scripts/codegen_schema.py --check

# Frontend build (TS + Vite)
cd web && npm run build

# Targeted frontend suites
cd web && npm run test -- --run src/components/__tests__/CustomizePanel.test.tsx
cd web && npm run test -- --run src/lib/store/__tests__/supportStore.test.ts
cd web && npm run test -- --run src/lib/validators/__tests__/sections.test.ts
cd web && npm run test -- --run src/pages/__tests__/BuilderPage.handleUpdateStyle.test.ts
```

Smoke A — bug fix end-to-end (legacy migrates, direct legacy rejected):

```bash
cd api && .venv/bin/python -c "
from app.services.legacy_customizations import migrate_legacy_customizations
from app.schema.models import Customizations
import pydantic

migrated = migrate_legacy_customizations({'colors': {'accent': '#abc'}, 'fonts': {'body': 'Inter'}})
c = Customizations.model_validate(migrated)
print('A:', c.accent_color, c.body_font)

try:
    Customizations.model_validate({'colors': {'accent': '#abc'}})
    print('B: FAIL (legacy accepted)')
except pydantic.ValidationError:
    print('B: OK legacy rejected')
"
# Expect: A: #abc Inter
#         B: OK legacy rejected
```

Smoke B — resolver capability gate end-to-end:

```bash
cd api && .venv/bin/python -c "
from app.services.renderer import resolve
from app.services.renderer.support import RendererSupport, SupportLevel
from app.schema.models import (
    Document, Section, Entry, FieldBlock, Customizations, LayoutHints,
)
print(resolve(
    Document(sections=[Section(id='p', type='profile', title='P', enabled=True,
        layout=LayoutHints(break_before=True),
        entries=[Entry(id='e1', fields=[FieldBlock(key='name')])])]),
    None, Customizations(), RendererSupport(break_before=SupportLevel.NONE),
).sections['p'].layout.break_before)
"
# Expect: False
```

## Definition of done

1. `pytest -q` → **159 passed**. (Baseline 150 − 2 deleted tests + 9 new tests = 157. Recount: deleted `test_section_instance_legacy_style_round_trips` and `test_legacy_style_overrides_apply_to_section_three_axes` is +9 = 157. Add `test_customizations_rejects_legacy_top_level` and `test_customizations_rejects_legacy_fonts` and `test_customizations_accepts_canonical_shape` (3) for 160. Step 1 adds 7 migrator tests, Step 1 schema adds 3 (10 total). Step 2 adds 2. Net: 150 − 2 + 12 = 160. Recount at execution time.)
2. `codegen_schema.py --check` → 0.
3. `npm run build` → 0.
4. CustomizePanel regression test → all pass.
5. supportStore test → 4 pass.
6. validators test → existing + new pass.
7. BuilderPage.handleUpdateStyle test → 3 pass.
8. Smoke A: `A: #abc Inter` / `B: OK legacy rejected`.
9. Smoke B: `False`.
10. `grep -rnE 'StyleEditor|TemplateWizard\b(?!.*=|<|$)|legacy_style|"colors":\s*\{|"fonts":\s*\{|"field_styles"|"globalStyleSchema"' web/src` → zero.
11. 4 tracker entries authored; PLAN.md and AGENTS.md updated.

No lint. No commit. No push.

## Risk register (v5)

| Risk | Mitigation |
|---|---|
| `Customizations.model_validator` rejects existing rows that already pass through the validator (no migration happens). | `coerce_customizations` runs `migrate_legacy_customizations` BEFORE `model_validate`. The validator only fires on raw writes; DB reads always go through the migrator. |
| `Font select` removal breaks the existing per-field font cascade if there was CSS that depended on it. | Backend CSS already cascades from `layout.font_family` via CSS inheritance (codegen LayoutHints docstring says so). Verify with one smoke render. |
| `StyleEditor.tsx` deletion leaves imports stale elsewhere. | Step 5a's `grep` is part of the gate. |
| `TemplateWizard` stub breaks `TemplateWizard.tsx` callers. | The stub still exports `default function TemplateWizard()`. No caller relies on its internal behaviour. |
| `sectionInstanceSchema` becoming `.strict()` rejects CV rows stored with extra keys. | Codegen-derived shape is already permissive (`extra: ignore`). Validator strictness is a frontend-side line of defence; backend is unchanged. |
| Legacy `test_section_instance_legacy_style_round_trips` deletion is irreversible without re-baking the field. | Tracked; `git checkout` restores the test file in one command. |

## Out of scope (Phase 3 follow-ups)

- Replace `TemplateWizard` with a v2 TemplateManifest + Customizations authoring UI.
- Add a "Document" `<details>` in the customize panel that writes `Customizations.accent_color / body_font / heading_font / spacing (preset) / flags`.
- Migrate stored `default_customizations` rows that may still carry the legacy shape (the wizard path is un-touched users' templates).
- Per-field font wire-key (`text[key].font`) re-introduction if a section needs to override the cascade.
