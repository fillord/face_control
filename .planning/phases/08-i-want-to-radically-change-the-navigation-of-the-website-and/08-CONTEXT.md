# Phase 8: Navigation & Design Overhaul - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete redesign of all authenticated internal-facing pages: navigation structure, visual style, shared layout architecture, and all UI components (cards, tables, buttons, form inputs, status badges). Delivers a `base.html` Jinja2 template that all role pages extend. Scope includes superadmin, org_admin, dept_admin, admin (hr_viewer), employee, dashboard, timesheet, profile, account, audit, and reports templates. Excludes kiosk (`/`) and login — those stay standalone.

</domain>

<decisions>
## Implementation Decisions

### Navigation Layout
- **D-01:** Replace horizontal `nav-tabs` with a **fixed sidebar** on the left — always visible, no collapse.
- **D-02:** Sidebar is **role-aware**: each role sees only its own nav items. Rendered server-side via Jinja2 `{% if session.role == 'superadmin' %}...{% elif session.role == 'org_admin' %}...{% endif %}` blocks inside `base.html`.
- **D-03:** Sidebar nav items use **icons + text labels** (inline SVG or Unicode symbols for zero-dependency icons).
- **D-04:** **User info (name, display role, logout link) lives at the bottom of the sidebar** — not in a top header bar. No top header at all.
- **D-05:** Page title / current section name appears as the first element in the content area (e.g., an `<h1>` or breadcrumb), not in a sticky top bar.

### Color Scheme & Visual Style
- **D-06:** **Dark sidebar + light content area** layout. Sidebar background: deep navy/dark (e.g., `#0f172a` or `#1a2340`). Content area: light (`#f8fafc` or `#f4f6fb`).
- **D-07:** Accent color: **Teal** (`#0d9488` primary, `#0891b2` alternate). Replaces current `#1565C0` blue throughout buttons, active states, links, focus rings.
- **D-08:** Font: **Inter** loaded from Google Fonts CDN (`<link>` in `base.html` head). Replace current `'Segoe UI', system-ui` stack.
- **D-09:** **Full component redesign** — cards, data tables, buttons, form inputs (date pickers, selects, text inputs), and status/role badges all redesigned consistently in the new palette. No components left in the old blue-and-white style.

### Base Template Architecture
- **D-10:** Create `templates/base.html` — the single shared Jinja2 base template. All authenticated pages extend it via `{% extends 'base.html' %}` and fill a `{% block content %}` block.
- **D-11:** `base.html` contains: Inter font CDN link, shared CSS (sidebar, layout, component tokens), the sidebar HTML with role-aware `{% if session.role %}` nav items, and the content area wrapper.
- **D-12:** `kiosk.html` and `login.html` do **not** extend `base.html`. They remain standalone with their own inline styles — different layout needs (full-screen camera; centered auth form).
- **D-13:** Shared CSS lives inside `base.html` as an inline `<style>` block (consistent with project's existing pattern of inline CSS per template). No separate `/static/css/app.css` file unless researcher recommends otherwise.

### Redesign Scope
- **D-14:** All authenticated templates redesigned: `superadmin.html`, `org_admin.html`, `dept_admin.html`, `admin.html`, `employee.html`, `dashboard.html`, `timesheet.html`, `profile.html`, `account.html`, `audit.html`, `reports_partial.html`. Also `403.html` and `error_token.html` for error pages.
- **D-15:** **Basic responsiveness required**: sidebar collapses to a hamburger/overlay on small screens (≤768px). Content reflows. Not a full mobile-first redesign — functional on tablets and phones is sufficient.
- **D-16:** Existing `devices.html` (if it has a UI) also gets the base template treatment.

### Claude's Discretion
- Exact sidebar width (240px–280px typical for this type of dashboard)
- Sidebar item hover/active state animation (subtle transition is fine)
- Icon set choice — inline SVG heroicons or simple Unicode symbols, whichever is easier to maintain
- Exact Inter font weight variants to load (400 + 500 + 600 is standard)
- Exact teal shade variations for hover, focus, and disabled states
- Content area max-width constraint (if any — researcher to assess)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs or ADRs — requirements fully captured in decisions above.

### Existing templates (read before redesigning each)
- `templates/superadmin.html` — superadmin page: org management, users, audit tabs
- `templates/org_admin.html` — org admin page: departments, reports, timesheets
- `templates/dept_admin.html` — dept admin page: dept attendance, employees
- `templates/admin.html` — hr_viewer page: attendance journal, stats, users
- `templates/employee.html` — employee cabinet: own attendance, T-13
- `templates/dashboard.html` — general dashboard (role-aware landing)
- `templates/timesheet.html` — T-13 timesheet grid
- `templates/profile.html` — user profile
- `templates/account.html` — account settings
- `templates/audit.html` — superadmin audit log
- `templates/kiosk.html` — PUBLIC, do not redesign, keep standalone
- `templates/login.html` — PUBLIC, do not redesign, keep standalone

### Project context
- `.planning/PROJECT.md` — project constraints (Flask + JSON, no framework migration, PM2 deployment)
- `.planning/REQUIREMENTS.md` — active requirements; data isolation rules must not be broken by nav changes
- `app.py` — Flask routes and `session.role` values used for Jinja2 role checks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.nav-tabs` pattern in `admin.html`/`superadmin.html` — understand existing tab content to know what sidebar items to create
- `.stat-card` component — used across multiple templates for KPI display; redesign to match new palette
- `.table-card` pattern — used for attendance/employee data tables; modernize while keeping data structure
- `colorFor()` JS function — generates avatar colors from names; keep logic, update colors to teal palette

### Established Patterns
- **Inline CSS per template** — project uses `<style>` blocks, no build step; `base.html` should follow the same convention
- **Jinja2 session checks** — `session.role` is already used for tab visibility (e.g., `{% if session.role == 'superadmin' %}`); extend this for sidebar
- **No CSS framework** — plain CSS Grid/Flexbox only; keep zero build-tool dependency
- **kebab-case CSS classes** — `.status-chip`, `.employee-card`, `.time-val`; new classes follow same convention

### Integration Points
- `app.py` Flask routes pass `role=session.role` (or equivalent) to templates — sidebar role checks use this
- `session['username']` and `session['display_name']` available for bottom-of-sidebar user info
- All `@require_role` protected routes will benefit from the sidebar navigation pattern
- `templates/reports_partial.html` is included via `{% include %}` — it will need to work inside the new base layout

</code_context>

<specifics>
## Specific Ideas

- Modern admin dashboard feel — think Linear, Vercel Dashboard, or Railway in terms of sidebar + content layout pattern
- Dark sidebar with teal accent creates a strong visual identity distinct from generic clinic software
- Inter font significantly elevates the perceived quality of the UI with zero backend changes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and*
*Context gathered: 2026-06-25*
