# Library Feature — UI Addendum

**Companion to**: [`library-feature-design.md`](./library-feature-design.md)
**Date**: 2026-08-26

## Design Direction

### Intent

A single user building a CV with a small reusable library of content. They want to pull from the library without leaving the section they're editing. The interaction should feel quick and decisive — one button reveals a list, one click inserts.

### Visual system

The Library ships as the first UI in Aergia that commits to the **modern minimal** direction. White surfaces, ink-900 text, gray-50 canvas, **emerald-600 (`#059669`)** as the single accent. Inter throughout. No serif.

### Tokens (additions to `tokens.css`)

The proof-sheet tokens already exist. This feature introduces a parallel minimal-modern set for the new Library surfaces, with both systems sharing primitives (rule, ink, spacing):

```css
:root {
  /* ── Minimal-modern surfaces ───────────────────────────────── */
  --canvas:        #F8FAFC;   /* page canvas (gray-50) */
  --surface:       #FFFFFF;   /* cards, modal, picker */
  --surface-2:     #F1F5F9;   /* hover / grouped bg (slate-100) */

  /* ── Ink ──────────────────────────────────────────────────── */
  --ink:           #0F172A;   /* slate-900 — primary text */
  --ink-2:         #475569;   /* slate-600 — secondary text */
  --ink-3:         #94A3B8;   /* slate-400 — meta / disabled */

  /* ── Rules ────────────────────────────────────────────────── */
  --rule:          #E2E8F0;   /* slate-200 */
  --rule-soft:     #F1F5F9;   /* slate-100 */

  /* ── Accent (single emerald, used with intent) ────────────── */
  --accent:        #059669;   /* emerald-600 */
  --accent-hover:  #047857;   /* emerald-700 */
  --accent-soft:   #D1FAE5;   /* emerald-100 — pill backgrounds */
  --accent-ink:    #FFFFFF;   /* text on accent bg */

  /* ── Semantic ─────────────────────────────────────────────── */
  --danger:        #DC2626;
  --danger-soft:   #FEE2E2;
}
```

The existing proof-sheet tokens remain untouched and are still consumed by the customize-panel work.

### Typography

- **Family**: Inter (already loaded as `--font-ui`).
- **Scale**: 1.25 ratio from a 14px base: caption 11 · body 14 · label 13/500 · h3 16/600 · h2 20/600 · h1 28/600.
- **Hierarchy levers**: weight and color carry most of the hierarchy (size alone is the second lever).
- **Numbers**: `font-variant-numeric: tabular-nums` on counts.

### Spacing & radius

- Base unit 4px; existing `--s-*` scale reused.
- Cards: 16px padding (`--s-4`), 8px radius (`--r-2`).
- Buttons: 36px height, 12px horizontal padding, 6px radius.
- Modal: 16px radius (`--r-3`).

### Depth

Borders-only with a single shadow for the modal. `--rule` for card edges; `--shadow-pop` only on the picker modal.

### Motion

- Picker open: 180ms, `cubic-bezier(0.23, 1, 0.32, 1)`, scale from 0.97 + opacity.
- Entry insert: the new entry flashes `--accent-soft` for 400ms (subtle pulse) so the user sees where it landed.
- All motion respects `prefers-reduced-motion`.

## UI Surfaces

### 1. `/library` page

**Layout**: `max-w-5xl` centered, page header (h1 + count summary), then six kind sections stacked vertically. Each kind section is a card group with a sticky-on-scroll heading.

```
┌──────────────────────────────────────────────────────────┐
│  Aergia · Library                          + Add entry   │
│                                                          │
│  Library                                                 │
│  Your reusable content. Pull into any CV.                │
│  4 experiences · 2 education · 12 skills · …             │
│                                                          │
│  ─── Experiences ─────────────────────────  + Add        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Senior Backend Engineer              [Edit] [Del]  │  │
│  │ Acme Corp · 2022 – present                         │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Software Engineer II                  [Edit] [Del]  │  │
│  │ Initech · 2019 – 2022                              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ─── Education ──────────────────────────  + Add        │
│  …                                                      │
└──────────────────────────────────────────────────────────┘
```

- **Header**: h1 "Library" 28px/600, subhead "Your reusable content. Pull into any CV." in `--ink-2`. Right side: `+ Add entry` outline button opening a `<LibraryEntryCreateModal>`.
- **Count summary**: below subhead, eyebrow-style 11px/500 uppercase in `--ink-3`, tracking-wide. Format: `{N} experiences · {N} education · {N} skills · {N} projects · {N} certifications · {N} languages`.
- **Kind group**: heading row has the kind name in serif-free uppercase 12px/600 tracked, plus a small `+ Add` button (sized to match) on the right.
- **Entry card**: 16px padding, 8px radius, `--rule` border. Title row: 16px/600 + Edit/Delete text buttons in `--ink-3` (hover `--ink`). Meta row below: 13px/400 in `--ink-2`, single line.
- **Empty state**: When the Library is fully empty, the page renders a centered illustration-free message: "Your library is empty. Promote a CV's entries, or add your first one." Two buttons: "Open a CV to promote" + "+ Add entry".

### 2. `+ Add from library` picker modal

Triggered from the per-section button in the CV builder. Reuses the existing `Modal` primitive, content is a new `<LibraryPicker>` component.

```
┌────────────────────────────────────────────────────────┐
│  Add from library                              ✕       │
│  Experiences                                           │
│  ─────────────────────────────────────────────────     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ▸ Senior Backend Engineer                        │  │
│  │   Acme Corp · 2022 – present                     │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ▸ Software Engineer II                           │  │
│  │   Initech · 2019 – 2022                          │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ▸ Junior Engineer                                │  │
│  │   Hooli · 2017 – 2019                            │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Don't see it? + Create in library                    │
└────────────────────────────────────────────────────────┘
```

- **Modal width**: 560px, max-height 70vh with internal scroll.
- **Heading row**: h2 "Add from library" 20px/600, kind name "Experiences" 13px/500 in `--ink-3` below.
- **Entry rows**: each row is a clickable card. Title 16px/600, meta 13px/400 in `--ink-2`. Hover: `--surface-2` background. Click → entry inserted, modal closes, toast "Added Senior Backend Engineer to Experiences."
- **Empty state** (no entries of this kind): centered message "No library entries yet for experiences." + primary button "Create one" opening the Library page filtered to experiences; secondary link "+ Add new item instead" closes the modal and triggers the existing inline-new flow.
- **"Don't see it?" footer**: small link in `--ink-3`, opens `/library` in a new tab focused on this kind.

### 3. Per-section buttons in the CV builder

In each section's existing add-row in `ContentSectionList`:

```
+ Add new item          + Add from library
```

Two equal-weight buttons. `+ Add new item` (existing) is the secondary/outline style. `+ Add from library` (new) is the **primary emerald** button — emerald background, white text, 36px height. This subtle hierarchy nudges users toward the library path when they have content.

If the user has zero Library entries of this kind, the `+ Add from library` button is **dimmed but still visible** — clicking it opens the picker with its empty state (so they discover the path even when empty).

### 4. Dashboard `Library` card

A new card alongside `CvCard` in `CvListPage`. Smaller than a CV card (1-column width on the grid), visually quieter.

```
┌────────────────────────┐
│  Library               │
│  Your reusable content │
│                        │
│  4 experiences         │
│  2 education           │
│  12 skills             │
│                        │
│  Open library →        │
└────────────────────────┘
```

- White surface, `--rule` border, no top accent bar (CV cards have a colored top bar tied to the template accent — the Library card doesn't have that, which keeps it visually quiet).
- Click anywhere on the card → `/library`.

### 5. `⋯` menu on `CvCard` — Promote to Library

Adds a single menu item below the existing Edit/Copy/Delete actions:

```
┌──────────────────────┐
│ Promote to library   │
└──────────────────────┘
```

On click: toast "Promoted 4 experiences, 2 education, 12 skills, 3 projects to your Library. View →" with the link opening `/library` in the same tab.

## Component Inventory (new)

| Component | Purpose | Reuses |
|---|---|---|
| `<LibraryPicker>` | Modal content for "Add from library" | `Modal` primitive |
| `<LibraryEntryCard>` | Single entry row (used in picker + page) | — |
| `<LibraryKindGroup>` | Kind-grouped section on `/library` page | `AccordionPanel` (optional) |
| `<LibraryCreateModal>` | Create/edit entry modal | `Modal`, existing field editors from `sections/` |
| `<PromoteToLibraryButton>` | Menu item on `CvCard` | — |

## State & Routing

- New Zustand store `libraryStore` in `web/src/lib/store/libraryStore.ts`. Mirrors `cvStore` shape (list, fetch, create, update, remove). Adds `cloneToSectionInstance(entryId, kind)` returning a `SectionInstance`.
- New route `/dashboard/library` mounted under `AppLayout`. (Path fits the existing `/dashboard/*` namespace.)
- New nav link in `AppLayout`: between "My CVs" and "Settings", label "Library", icon `Library` from lucide-react.

## Risks & Decisions Log

| Decision | Rationale |
|---|---|
| Modal picker over popover | User chose modal; gives space for entry preview + future expansion. Per-kind filter avoids irrelevant entries. |
| Modern minimal over proof-sheet | User chose emerald-600 + white. Crisp, defaults-strong but coherent. |
| No signature element | Page-level typography + emerald accents carry differentiation. No decorative flourishes. |
| Per-section `+ Add from library` always visible | Discoverability > visual quietness. Users learn the path even when their Library is empty. |
| Empty-state CTA in picker opens `/library` | First-time users get a clear path to seed their Library from the picker itself. |
| `Library` card on dashboard | Mirrors `CvCard` shape but quieter. Establishes the Library as a sibling concept, not buried in settings. |

## Open Questions

None — design is locked.
