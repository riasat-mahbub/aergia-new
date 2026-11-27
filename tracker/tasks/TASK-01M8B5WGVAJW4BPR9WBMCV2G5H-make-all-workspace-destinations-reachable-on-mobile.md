---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M8B5WGVAJW4BPR9WBMCV2G5H
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: High
TAGS:
- frontend
- responsive
- navigation
RELATIONS:
  related:
  - BUG-01M8AY219XEH2HRA09GSQ3H8D2
  - TASK-01M8AY219XV55JCZZ8B84QANVK
AFFECTS:
  files:
  - web/src/app-shell/components/SiteNavbar.tsx
  - web/src/app-shell/layouts/WorkspaceLayout.tsx
  - web/src/routes/_authenticated/builder/route.tsx
LINKS: null
VERIFIED_BY: codex
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-11-26T05:40:06.122587+00:00'
UPDATED_AT: '2026-11-26T05:59:17.557+00:00'
---

# Make all workspace destinations reachable on mobile

## Background

Implementation plan for [BUG-01M8AY219XEH2HRA09GSQ3H8D2](../bugs/BUG-01M8AY219XEH2HRA09GSQ3H8D2-mobile-navbar-hides-workspace-destinations.md).

## Investigation

The authenticated header gives the five workspace links a narrow horizontal scroll area. At 390 px, part of Library and all of Applications and Settings are offscreen. The compact header has no visible control that reveals them.

## Decision

Use a visible **Menu** disclosure below Tailwind's `md` breakpoint and a horizontal link row at desktop widths. Open the mobile links in a vertical list below the header controls. Use ordinary navigation links and native Tab order.

## Implementation

1. In `SiteNavbar.tsx`, keep `navItems` as the only list of destinations and render one Primary navigation landmark. Use responsive layout classes to switch between the horizontal row and full-width mobile list. Keep the brand and Log out visible. Provide a visible Menu button with a 44 × 44 px minimum hit area, `aria-expanded`, and `aria-controls` pointing to the navigation ID.
2. Start the mobile list collapsed. A closed mobile list should be absent from the tab order. Use the existing TanStack links and matching behavior, including the active Applications state on nested detail routes. Expose the active destination in the link's accessible state.
3. Close the mobile list on link selection and route changes, including back and forward navigation. Use the existing router's navigation subscription if needed. On Escape from the open menu, close it and restore focus to Menu. If selecting the current route hides the focused link, return focus to Menu.
4. Preserve the current signed-out header and the builder route's `showNavbar={false}` behavior. Keep these checks in the app shell, where the navbar is owned.

## Verification

- At 320 and 390 px, open Menu and reach Dashboard, CVs, Library, Applications, and Settings by touch and keyboard. Confirm no horizontal page overflow and no clipped labels.
- Verify the collapsed links are skipped by Tab. Open from the keyboard, verify link order and active route, then press Escape and confirm focus returns to Menu.
- Verify the menu closes after same-route selection, a different route, and browser history navigation. Check the active Applications state on an application detail page.
- Resize across 767 and 768 px with the disclosure open and closed. Confirm every link stays reachable, desktop navigation fits, and the mobile trigger is hidden at desktop widths. Check signed-out Sign in and the builder's dedicated header.

Chromium reached all five destinations by touch at 320 × 640 and 390 × 844. All links fit within the header, and the header kept Menu and Log out on the top row. Tab skipped the collapsed links and followed their display order when open. Escape and same-route selection returned focus to Menu. New-route selection and browser Back and Forward closed the disclosure. The Applications link stayed active on application detail. Desktop layout at 768 px, the public login link, and the builder header passed.
