# Phase 8: Navigation & Design Overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 08-i-want-to-radically-change-the-navigation-of-the-website-and
**Areas discussed:** Navigation layout, Color scheme & visual style, Base template architecture, Redesign scope

---

## Navigation Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed sidebar | Left-side vertical nav, always visible | ✓ |
| Collapsible sidebar | Can collapse to icon-only mode | |
| Top navbar with dropdowns | Horizontal top bar with dropdowns | |
| Keep tabs but redesign style | Same horizontal tabs, new visual style | |

**User's choice:** Fixed sidebar

---

| Option | Description | Selected |
|--------|-------------|----------|
| Role-aware sidebar | Each role sees only its own nav items via Jinja2 session.role | ✓ |
| Universal sidebar with role gating | All items visible, unauthorized grayed out | |
| Flat links list per role | Simple vertical link list, no grouping | |

**User's choice:** Role-aware sidebar (Jinja2 session.role rendering)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Icons + text | Each nav item has icon and label | ✓ |
| Text only | Clean labels, no icon dependency | |
| Icons only (collapsed view) | Icons on hover showing text | |

**User's choice:** Icons + text

---

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom of sidebar | User avatar/name + logout at very bottom | ✓ |
| Top header bar only | Keep current header with user + logout | |
| Top of sidebar | User info at top of sidebar | |

**User's choice:** Bottom of sidebar — no top header bar

---

## Color Scheme & Visual Style

| Option | Description | Selected |
|--------|-------------|----------|
| Dark sidebar + light content | Deep navy sidebar, white content area | ✓ |
| All-light with new accent | Keep light, change accent color | |
| Full dark mode | Dark everywhere | |
| Green-based medical theme | Shift to green/teal light mode | |

**User's choice:** Dark sidebar + light content

---

| Option | Description | Selected |
|--------|-------------|----------|
| Keep blue deeper (#0d47a1) | Darken current blue | |
| Indigo (#3730a3) | Shift to indigo | |
| Teal (#0d9488 / #0891b2) | Medical/clinic association | ✓ |
| You decide | Leave to planner | |

**User's choice:** Teal (#0d9488 / #0891b2)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Google Fonts: Inter | Gold standard for dashboards | ✓ |
| Keep system font | No extra load, Segoe UI / system-ui | |
| Google Fonts: Roboto | Clean, common in medical software | |

**User's choice:** Google Fonts: Inter

---

| Option | Description | Selected |
|--------|-------------|----------|
| Full redesign of all components | Cards, tables, buttons, inputs, badges | ✓ |
| Navigation + colors only | Just nav and palette | |
| Navigation + major components only | Nav, colors, buttons, stat cards | |

**User's choice:** Full redesign of all components

---

## Base Template Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Shared base.html Jinja2 template | All role templates extend base.html | ✓ |
| Shared static CSS file | Common CSS in /static/css/app.css | |
| Keep per-template inline CSS | Redesign each independently | |

**User's choice:** Shared base.html Jinja2 template

---

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 if/elif blocks in base.html | Role nav items via session.role checks inline | ✓ |
| Role-specific sidebar partials | Separate sidebar_superadmin.html etc. | |
| Sidebar data passed from Flask route | nav_items list passed per route | |

**User's choice:** Jinja2 if/elif blocks in base.html

---

| Option | Description | Selected |
|--------|-------------|----------|
| No — kiosk and login stay standalone | Different layout needs, no sidebar | ✓ |
| Login inherits base, kiosk standalone | Minimal base for login | |
| Both inherit from minimal base-public.html | Shared colors/font for public pages | |

**User's choice:** Kiosk and login stay fully standalone

---

## Redesign Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All authenticated pages | Every logged-in page; excludes kiosk + login | ✓ |
| Core role pages only | Main role pages, skip edge pages | |
| All pages including kiosk and login | Redesign everything | |

**User's choice:** All authenticated pages

---

| Option | Description | Selected |
|--------|-------------|----------|
| Basic responsiveness | Sidebar collapses to hamburger ≤768px | ✓ |
| Desktop-only | No mobile requirement | |
| Full mobile-first | Mobile-first with all breakpoints | |

**User's choice:** Basic responsiveness (sidebar hamburger on mobile)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Remove top header, everything in sidebar | No top bar; page title in content area | ✓ |
| Thin top bar for breadcrumb/page title | 48px top bar for current page name | |
| Keep current header style | White header + sidebar replaces tabs | |

**User's choice:** No top header — everything in sidebar, page title in content area

---

## Claude's Discretion

- Exact sidebar width (240–280px typical)
- Sidebar item hover/active animation style
- Icon set choice (inline SVG heroicons or Unicode symbols)
- Inter font weight variants to load
- Exact teal shade variations (hover, focus, disabled states)
- Content area max-width constraint

## Deferred Ideas

None — discussion stayed within phase scope.
