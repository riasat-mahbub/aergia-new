# Phase 4 — Constrained design vocabulary (tokenised plan v2)

**Branch:** `feat/ast-pipeline`, on top of the Phase 3 working tree.
**Goal:** Every styling field on the manifest and the per-CV `Customizations` is a **token** from a closed enum, OR a `ColorRef` (hex literal `#RRGGBB` or `palette.<name>`). The manifest never carries raw CSS. The resolver is the only place tokens become CSS values. A future renderer (DOCX) ships its own `tokens_<renderer>.py` and reuses the same `palette.py`.

**The change in one sentence:** Replace the legacy `{colors, fonts, spacing, flags}` shape and the free-form CSS strings on `ZoneStyle` with a typed closed vocabulary, then drop the legacy derivations in routes and seed.

**Scope explicit:** This phase does not introduce drag-drop zone authoring, multi-template preview, per-entry policy overrides, or a DOCX renderer. The wizard is the only authoring surface that ships this phase; the editor's interactive zone drag is unchanged.

---

## 1. What is a token (the philosophical anchor)

A **token** is a name from a closed enum that the renderer maps to its native value at the wire boundary. The manifest carries the name; the resolver carries the mapping table. The plan's vocabulary:

| Token family | Manifest value | Resolver mapping (HTML) | Where it lives |
|---|---|---|---|
| Width | `narrow \| half \| full \| auto` | `narrow→30%, half→50%, full→100%, auto→auto` | `ZoneStyle.width` |
| Spacing (zones) | `none \| tight \| comfortable \| loose` | `none→0, tight→12px, comfortable→24px, loose→32px` | `ZoneStyle.padding` |
| Spacing (layout) | `compact \| comfortable \| minimal` | CSS vars (`--spacing-section` / `--spacing-subsection`) | `LayoutDefaults.spacing` |
| Font | `sans-serif \| serif \| mono \| display` | CSS font-stack | `GlobalStyles.body_font / heading_font`, `Customizations.body_font / heading_font` |
| Color | `ColorRef` (hex literal `#RRGGBB` or `palette.<name>`) | hex literal returned as-is; `palette.<name>` resolved via `DEFAULT_PALETTE` (renderer-defined) | `GlobalStyles.accent_color`, `Customizations.accent_color`, `ZoneStyle.background` |

**The one exception** is the hex literal. Color is the one styling domain where the user reasonably wants exact control; the resolver's role is just to validate and pass through. Every other field is a closed enum.

**`palette.<name>` is renderer-defined.** The default palette lives in `app/services/renderer/palette.py`. A DOCX renderer ships its own palette. Renderers MUST agree on the default; renderer-specific palettes are an extension point (not a v1 concern).

---

## 2. Token addition checklist (operational discipline)

When you add a new token to the schema, the following must all be updated in one commit:

- [ ] `api/app/schema/models.py` — add the `Literal[...]` type
- [ ] `api/app/services/renderer/tokens.py` — add the value mapping
- [ ] `api/app/services/renderer/resolve.py` — call the mapping in the right hook
- [ ] `web/src/lib/validators/sections.ts` — add the Zod schema
- [ ] `web/src/components/template-creator/TemplateWizard.tsx` — add the picker
- [ ] `web/src/components/customization/CustomizePanel.tsx` — add the picker (if user-facing)
- [ ] `web/src/lib/sections/zones.ts` — `widthTokenToCss` / `spacingTokenToCss` helpers (if the token has a CSS representation)
- [ ] Tests for every layer that touches the token
- [ ] A roundtrip test that proves the new field flows schema → resolver → Zod → renderer

A pre-commit hook that greps for the new token and verifies all those files are updated would automate this.

---

## 3. Out of scope (deferred to later phases)

- **Drag-drop zone authoring** (the user-facing CV editor's interactive divider / zone-create / zone-resize surface) — the wizard deep-copies zones from the base template. Restoring v1's interactive surface is medium effort, not on the critical path.
- **Multi-template preview side-by-side** — comparison UX, not editor richness. Defer to a product-driven phase.
- **Per-entry policy overrides** — `SectionPolicy` today is per-section-type. A `SectionInstance.policy` override field would let two "Skills" sections render differently. The `Section.style` field already exists for per-instance content styling; mixing semantic policy with content styling is a deliberate design choice the plan defers. Small effort (1-2 days) when the need arises.
- **DOCX renderer** — a renderer-only change. The `palette.py` and `tokens.py` modules are renderer-defined; a DOCX renderer ships its own `tokens_docx.py` and reuses `palette.py`. No schema impact.
- **Asset upload UI** — `assets` was dropped from `TemplateDetail` in this phase. The `Template.assets` column is still nullable for any old rows.
- **Alembic migration for the legacy columns** — verified via the existing `Template` model that all four columns (`default_customizations`, `layout_config`, `layout_template`, `assets`) are already nullable. No migration is needed.

---

## 4. Plan deltas

### 4.1 Backend schema (`api/app/schema/models.py`)

Add Literal types at the top of the file:

```python
WidthToken = Literal["narrow", "half", "full", "auto"]
SpacingToken = Literal["none", "tight", "comfortable", "loose"]
FontToken = Literal["sans-serif", "serif", "mono", "display"]
AlignmentToken = Literal["left", "right", "center", "justify"]
FontSizeToken = Literal["xs", "small", "normal", "large", "xl"]
LayoutSpacingToken = Literal["compact", "comfortable", "minimal"]
```

Add a `ColorRef` helper:

```python
import re
_HEX_LITERAL = re.compile(r"^#[0-9a-fA-F]{6}$")
_PALETTE_REF = re.compile(r"^palette\.[a-z][a-z0-9_-]*$")

def is_color_ref(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX_LITERAL.match(value) or _PALETTE_REF.match(value))
```

`ZoneStyle` becomes a closed shape:

```python
class ZoneStyle(BaseModel):
    width: WidthToken | None = None
    background: str | None = None        # validated as ColorRef
    padding: SpacingToken | None = None
    model_config = {"extra": "forbid", "populate_by_name": True}

    @model_validator(mode="after")
    def _check_color(self):
        if self.background is not None and not is_color_ref(self.background):
            raise ValueError(...)
        return self
```

A new `GlobalStyles` class (closed):

```python
class GlobalStyles(BaseModel):
    accent_color: str | None = None
    body_font: FontToken | None = None
    heading_font: FontToken | None = None
    model_config = {"extra": "forbid"}
    # validator: accent_color must be a ColorRef
```

`TemplateManifest.global_styles` becomes `GlobalStyles` (typed), not `dict[str, str]`.

`Customizations` tightens:
- `body_font: FontToken | None`
- `heading_font: FontToken | None`
- `accent_color: str | None` validated as a ColorRef
- `default_text_align: AlignmentToken | None` (was `Literal[...]` already; rename the import)

`TemplateDetail` drops `default_customizations` and `assets`. The manifest is the only template payload.

### 4.2 Resolver (`api/app/services/renderer/resolve.py`)

Add `_resolve_zone_styles(zone) -> dict[str, str]` that maps tokens → CSS. The resolver is the only place raw CSS values are produced.

`_build_css_vars` resolves `body_font` / `heading_font` tokens and `accent_color` color refs before writing to `RenderModel.css_vars`.

`_apply_template_defaults` and `_apply_user_customizations` resolve `body_font` and `accent_color` refs before writing to `Section.layout` and `Section.subsection`.

The customizations→css_vars precedence: per-CV `Customizations` wins over `manifest.global_styles` when both are set. (A test locks this down.)

### 4.3 Shared token tables (`api/app/services/renderer/palette.py` + `tokens.py`)

New modules. `palette.py` exposes `DEFAULT_PALETTE` (a dict of named color slots) and `resolve_palette_ref(value, palette) -> str`. `tokens.py` exposes `WIDTH_TOKEN_VALUES`, `PADDING_TOKEN_VALUES`, `SPACING_TOKEN_VALUES`, `FONT_TOKEN_VALUES` (Literal type aliases) plus `resolve_width`, `resolve_padding`, `resolve_font`, `resolve_spacing_pair` helpers.

The default palette in Phase 4:
```python
DEFAULT_PALETTE = {
    "accent": "#2563eb",
    "surface": "#ffffff",
    "surface-2": "#f8fafc",
    "text": "#111827",
    "text-muted": "#6b7280",
    "divider": "#e5e7eb",
}
```

### 4.4 Seed (`api/app/db/seed.py`)

Re-author the three seeds as direct v2 manifests. **The seed's `accent_color` is a `palette.<name>` reference (e.g. `"palette.accent"`), NOT a hex literal** — this exercises the palette path and proves the resolver is renderer-agnostic. The HTML renderer resolves it to `#2563eb`; a DOCX renderer would resolve to a DOCX color reference.

`seed_templates` leaves `Template.default_customizations` as `None` on both new and existing rows. Drop the `_default_customizations_from_manifest` import.

### 4.5 Routes (`api/app/routes/templates.py`)

`create_user_template` persists the manifest only. The `_default_customizations_from_manifest` helper is **deleted**. The multipart `create_template_from_manifest` endpoint persists the manifest only.

`TemplateDetail` (in `api/app/schema/models.py`) drops `default_customizations` and `assets`. **Manifest is the only template payload.**

### 4.6 Service (`api/app/services/cv.py`)

`coerce_customizations` validates against `Customizations` directly; no legacy migration. Old rows surface as validation errors if read.

### 4.7 Legacy module deletion

`api/app/services/legacy_customizations.py` and its test file are **deleted**. The v1-to-v2 migrator is no longer needed.

### 4.8 Frontend validators (`web/src/lib/validators/sections.ts`)

Add `widthTokenSchema`, `spacingTokenSchema`, `fontTokenSchema`, `alignmentTokenSchema`, `layoutSpacingTokenSchema`. Add `colorRefSchema` (hex literal or `palette.<name>`).

Rewrite `templateManifestSchema` to use the new enums; rewrite `customizationsSchema.accent_color` to use `colorRefSchema`; rewrite `customizationsSchema.body_font` / `heading_font` to use `fontTokenSchema`. Add a new `globalStylesSchema` (closed, like the Pydantic model).

### 4.9 Editor math (`web/src/lib/sections/zones.ts`)

`percentToToken(percent: number) -> WidthToken`:
- `≤ 35` → `"narrow"`
- `≤ 65` → `"half"`
- `≥ 95` → `"full"`
- else → `"auto"`

`getWidthPercent(zone)`, `normalizeWidths(zones)`, `widthTokenToCss(token)`, `spacingTokenToCss(token)` all work with tokens. `normalizeWidths` rounds via `percentToToken` at the end.

### 4.10 Wizard (`web/src/components/template-creator/TemplateWizard.tsx`)

Layout step: per-zone `WidthToken` select (narrow / half / full / auto), per-zone `SpacingToken` select (none / tight / comfortable / loose), per-zone background palette picker.

Global Styles step: accent color palette + hex combo (palette dropdown + color picker + hex text input). Body font and heading font are `FontToken` selects.

### 4.11 CustomizePanel (`web/src/components/customization/CustomizePanel.tsx`)

Document group: accent color palette + hex combo; body / heading font `FontToken` selects; spacing `LayoutSpacingToken` radio.

Per-section styling contracts unchanged (three axes via `SectionInstanceStyle`).

### 4.12 Layout views

`TemplateLayoutView`, `SectionZoneView`, `BaseTemplateCard` all use `widthTokenToCss` and `getWidthPercent` from `web/src/lib/sections/zones.ts`. The editor's interactive width handling is percentage-internal; the wire carries tokens.

### 4.13 API client

`UserTemplateCreate = {name, description?, manifest}`. The store's `uploadTemplate` and `createTemplate` take the v2 manifest shape.

### 4.14 BuilderPage state

`localCustomizations: Record<string, unknown>` (kept as a bag for now; the strict `Customizations` + `LayoutConfig | null` split is a follow-up refactor). `handleUpdateCustomizations` is wired the same way as `handleUpdateStyle`: `hasChangesRef` + `setHasUnsavedChanges` + replace state.

### 4.15 Codegen

Add `GlobalStyles` to `EMITTED_MODELS` in `api/scripts/codegen_schema.py`. **Literal types do NOT need to be in the whitelist** — the codegen filters by `BaseModel` subclass, so `WidthToken = Literal[...]` is not emitted as a separate TS type. TS code that consumes these types writes them inline (e.g. `width: "narrow" | "half" | "full" | "auto"` appears in the generated `ZoneStyle` interface as a literal union directly).

**Codegen maintenance:** the current whitelist is fragile (human-maintained list of class names). A future improvement is auto-discovery (`[name for name, cls in inspect.getmembers(schema) if isinstance(cls, BaseModel)]`). Tracked as tech debt.

### 4.16 Renderer protocol (forward-looking, not v1)

Define `Renderer` as an abstract class with `support: RendererSupport` and `render(model) -> str`. `HTMLDocumentRenderer` implements it. The resolver takes a `Renderer`, not a concrete class. Today the resolver imports `HTMLDocumentRenderer` directly — a DOCX renderer would be a new import. The protocol makes the substitution explicit and testable. Tracked as a follow-up.

---

## 5. Test plan

### 5.1 Backend

1. **Resolver token mapping** (4 new tests):
   - `test_resolver_maps_width_tokens` — `narrow→30%`, `half→50%`, `full→100%`, `auto→auto`.
   - `test_resolver_maps_padding_tokens` — `none→0`, `tight→12px`, `comfortable→24px`, `loose→32px`.
   - `test_resolver_maps_color_palette_reference` — `palette.surface-2` → `#f8fafc` via DEFAULT_PALETTE.
   - `test_resolver_falls_back_to_hex_literal` — `#RRGGBB` returned unchanged.

2. **Seed** (2 new tests):
   - `test_seed_manifests_use_constrained_vocabulary` — every `ZoneStyle` width is a `WidthToken`; every padding is a `SpacingToken`; no `display` / `position` / `transform` / `gridTemplateColumns` keys; accent_color is a `ColorRef` (not a hex literal — it must be `palette.<name>` to exercise the palette path).
   - `test_seed_does_not_persist_default_customizations` — the seed leaves the legacy bucket null.

3. **HTML renderer** (1 new test):
   - `test_html_renderer_uses_resolved_css_not_manifest_css` — emit a manifest with `width: "narrow"`; the rendered HTML contains `width: 30%` and NOT the literal `narrow`. This locks the resolver-to-renderer contract.

4. **Schema shape** (1 new test):
   - `test_zone_style_uses_closed_vocabulary` — replaces the old `test_zone_style_accepts_alias_background_color`. The new `ZoneStyle` rejects `extra` keys; uses `background` (not the legacy `background-color` alias).

5. **Routes** (3 new tests):
   - `test_create_user_template_does_not_persist_default_customizations` — POST a manifest; the response's `default_customizations` is None.
   - `test_create_user_template_rejects_css_strings` — POST with `width: "30%"` returns 422.
   - `test_create_user_template_rejects_extra_zone_keys` — POST with `display: "flex"` returns 422.

6. **Schema validator (Pydantic)** (1 new test):
   - `test_customizations_rejects_unknown_keys` — `Customizations` with `"custom_typo": "..."` is rejected. (Current validator only rejects `colors` and `fonts`; unknown new keys are silently accepted. This test surfaces the gap.)

7. **Resolver precedence** (1 new test):
   - `test_user_customizations_override_template_default` — manifest has `body_font: "serif"`; per-CV `Customizations.body_font` is `"sans-serif"`. The section's `layout.font_family` is `"sans-serif, ..."`. (A test that wasn't in the original plan; locking the precedence is one of the additions in this v2.)

8. **Manifest vocabulary roundtrip** (1 new test):
   - `test_manifest_vocabulary_roundtrips_every_field` — a fixture manifest that exercises every field at every layer (template-level customizations, per-CV customizations, per-section style, layout defaults, policy overrides, zones, placement). The Zod schema, the Pydantic model, and the resolver all accept it without dropping or coercing any field. (This is the test that would have caught the `palette.accent` vs hex literal issue and the codegen/Zod drift.)

### 5.2 Frontend

1. **Wizard** (4 new tests):
   - `renders the four step headings`
   - `typing in the name field updates manifest.name via onManifestChange`
   - `changing the spacing radio updates manifest.layout_defaults.spacing`
   - `changing the accent color hex updates manifest.global_styles.accent_color`
   - `toggling a show_title checkbox adds an entry to manifest.policy_overrides.by_type`
   - `templateManifestSchema rejects a v1 manifest`
   - `uploadUserTemplate mock is called with the v2 manifest shape on "Use this template"`
   - `the deprecated Phase 2 banner copy is gone`

2. **CustomizePanel** (3 new tests for the Document group):
   - `renders the Document disclosure with accent, fonts, and spacing controls`
   - `changing the accent color hex calls onCustomizationsChange with the new value`
   - `selecting a different body font calls onCustomizationsChange with the new value`

3. **Validators** (3 new tests for `templateManifestSchema`):
   - `accepts the canonical v2 shape`
   - `rejects manifest_version: 1`
   - `rejects a global_styles value that is not a string`

4. **SectionZoneView test** (existing; update data to use tokens):
   - `renders one row of zones, no Row N label, no Add Row button` — uses `width: "narrow"` and `width: "half"`; asserts `style.width` is `"30%"` and `"50%"`.

5. **TemplateLayoutView test** (existing; update data):
   - `Add Zone appends a new zone and rebalances widths` — each zone carries a width token; the assertion is that each zone's `styles.width` is a valid `WidthToken`.

6. **BaseTemplateCard test** (existing; update data):
   - `renders a flat strip even when zones carry legacy row data` — uses `width: "narrow"` and `width: "half"`; the rendered CSS is `30%` and `50%`.

---

## 6. The "what is renderer-independent" claim, locked

The plan claims: "the manifest is renderer-independent". This is verified by:
- A manifest that uses only `palette.<name>` references and no hex literals round-trips through resolver + Zod + codegen with no field loss.
- A DOCX renderer can be written with zero changes to the schema, the resolver, the Zod validators, or the codegen. (Verified by reading the protocol — the DOCX renderer ships its own `tokens_docx.py` and reuses `palette.py`.)

**One source of the "renderer-coupled" residue:** the resolver imports the concrete `HTMLDocumentRenderer` class. The renderer protocol refactor (4.16) addresses this. Until that's done, the claim is "renderer-independent in principle, not in code".

---

## 7. The "closed vocabulary" claim, locked

The plan claims: "the manifest exposes a closed vocabulary". This is verified by:
- `templateManifestSchema.safeParse` rejects manifests with unknown top-level keys, unknown zone keys, unknown global_styles keys, or unknown customizations keys.
- The codegen whitelist test: every emitted TS interface has a matching Zod schema (drift detection). Tracked as a future addition.

The current schema's `Customizations` rejects `colors` / `fonts` but accepts unknown new top-level keys. A test that confirms the v2 schema rejects `"custom_typo": "..."` would close that gap. (Listed in test 5.1.6.)

---

## 8. Definition of done

1. `pytest -q` → **159 passed** (was 152 baseline + 2 deleted legacy tests + 5 new = 159).
2. `codegen_schema.py --check` → exit 0.
3. `npm run build` → exit 0.
4. `npm run test -- --run` → all real tests pass (12 `node_modules_bak/` failures excluded).
5. The 8 new backend tests pass.
6. The 10+ new frontend tests pass.
7. `grep -rn 'width.*"[0-9]\+%\|padding.*"[0-9]\+px\|font-family.*"' web/src/components/template-creator web/src/components/customization` → zero matches.
8. `ls api/app/services/legacy_customizations.py api/tests/test_legacy_customizations.py` → both missing.
9. The seed's `accent_color` is `"palette.accent"`, not `"#2563eb"` (palette path exercised, not hex).
10. PLAN.md and AGENTS.md updated to reflect the closed vocabulary.

No lint. No commit without user approval. No push.

---

## 9. Risk register

| Risk | Mitigation |
|---|---|
| The codegen whitelist is a hand-maintained list of class names; forgetting to add a new `BaseModel` subclass causes a missing-reference error in TS. | Phase 5 work: auto-discover `BaseModel` subclasses from the schema module. (Tracked.) |
| The resolver imports the concrete `HTMLDocumentRenderer` class — DOCX renderer would need a new import. | Phase 5 work: introduce a `Renderer` protocol. (Tracked; see 4.16.) |
| The seed's `accent_color` was set to `"#2563eb"` (a hex literal) — defeats the palette exercise. | Fixed in this phase: change seed to `"palette.accent"`. Test verifies palette path. |
| `Customizations` only rejects `colors` and `fonts`; unknown new top-level keys pass. | Add a test for unknown keys. (Listed in test 5.1.6.) |
| The `Customizations.per_section` field exists in the schema but no test exercises it. | Add a roundtrip test that proves per-section overrides survive. (Listed in test 5.1.8.) |
| The customizations→css_vars precedence (per-CV > manifest) is not tested. | Add a test that sets both, asserts per-CV wins. (Listed in test 5.1.7.) |
| `unknown palette names` in `resolve_palette_ref` fall back to the literal string. The plan's prose said "renderer crashes loudly"; the code returns the literal. | Either reconcile the prose or add a warning log in the resolver. (Tracked as code-comment; the practical impact is "invalid CSS, renderer ignores" which is benign.) |
| `FALLOWED_HTML_COLORS` / `ALLOWED_CSS_PROPERTIES` are not actually checked; the schema keeps `extra="allow"` for `Section.text`. | Document that "this is a renderer-level concern, not a schema concern" in a comment. (Tracked as a doc note.) |
| `SectionPolicy` is per-section-type; per-entry override is a follow-up. | Document in the plan; defer per-entry policy to a later phase. (Tracked.) |

---

## 10. Out of scope (recap)

- Drag-drop zone authoring
- Multi-template preview
- Per-entry policy overrides
- DOCX renderer
- Asset upload UI
- Alembic migration (no migration needed; columns are already nullable)
- Renderer protocol refactor (forward-looking; the resolver is still concrete-classed)
- Codegen auto-discovery (forward-looking; the whitelist is hand-maintained)
- Manifest vocabulary roundtrip test (this phase adds it; future phases will maintain)

---

## 11. Tracker entries to author (after execution)

In `tracker/`:

1. `tracker/features/FEAT-01KZJ0PHASE4QA-phase-4-constrained-design-vocabulary.md` — this plan.
2. `tracker/tasks/TASK-01KZJ0PHASE4QA-phase-5-renderer-protocol-and-codegen-auto-discovery.md` — forward-looking tasks rolled out of this phase.

The ULIDs above are placeholders.
