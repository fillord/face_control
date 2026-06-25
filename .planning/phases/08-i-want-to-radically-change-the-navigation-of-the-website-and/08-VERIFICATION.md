---
phase: 08-i-want-to-radically-change-the-navigation-of-the-website-and
verified: 2026-06-25T17:30:00Z
status: human_needed
score: 17/17 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Log in as superadmin and confirm the dark sidebar renders with correct navy background (#0f172a), teal active states (#0d9488), Inter font, and no top header bar"
    expected: "Sidebar is dark navy, active nav item has teal highlight, Inter font visible, no horizontal header at top"
    why_human: "CSS rendering and font loading can only be confirmed in a browser"
  - test: "Resize browser window to <=768px and tap the hamburger button (☰) in the top-left of the content area"
    expected: "Sidebar slides in from the left; a semi-transparent overlay covers the content area; pressing Escape or clicking the overlay closes the sidebar"
    why_human: "JavaScript interaction and CSS transition require browser execution"
  - test: "Log in as each of the six roles (superadmin, org_admin, dept_admin, viewer, hr_viewer, employee) and inspect the sidebar nav items"
    expected: "superadmin sees: Организации, Пользователи, Регистрация, Аудит, Табель Т-13, Аккаунт. org_admin sees: Отделы, Сотрудники, Сводка, Отчёты, Пользователи, Настройки, Табель Т-13, Регистрация, Аккаунт. dept_admin/viewer see: Посещаемость, Сотрудники, Табель Т-13, Регистрация, Аккаунт. hr_viewer sees: Табель Т-13, Аккаунт. employee sees: Мой табель, Аккаунт."
    why_human: "Role-specific rendering requires a live session with the correct role value"
  - test: "Navigate to any authenticated page (e.g., /superadmin, /timesheet, /profile) and confirm the page content renders inside the sidebar layout to the right of the sidebar, with an h1.page-title as the first visible content element"
    expected: "Content area is to the right of the dark sidebar; h1 heading is visible as the first element; no blank page or Jinja2 rendering error"
    why_human: "Layout rendering (sidebar + content side-by-side) cannot be confirmed by grep"
  - test: "Navigate to /register/<invalid-token> to trigger error_token.html and confirm it renders as a standalone centered page with Inter font and teal logo icon — no sidebar"
    expected: "Centered card with teal logo icon, Inter font, error message displayed, NO sidebar visible (public page)"
    why_human: "Standalone vs. sidebar rendering requires browser confirmation"
---

# Phase 8: Navigation & Design Overhaul Verification Report

**Phase Goal:** Every authenticated page renders inside a single shared `base.html` shell: a dark fixed sidebar with role-aware navigation (replacing horizontal nav-tabs), a teal accent palette replacing the old blue, Inter font, and a responsive hamburger on small screens. The kiosk and login pages stay standalone.
**Verified:** 2026-06-25T17:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | base.html exists as valid HTML5 document with sidebar + content layout | VERIFIED | File exists at 250 lines; starts with `<!DOCTYPE html><html lang="ru">`; contains `.layout`, `.sidebar`, `.content` CSS and HTML structure |
| 2 | Inter font loads from Google Fonts CDN on every page that extends base.html | VERIFIED | `fonts.googleapis.com/css2?family=Inter:wght@400;500;600` present at base.html line 9 |
| 3 | Sidebar renders role-appropriate items for all 6 roles | VERIFIED | base.html lines 153-219: complete `{% if session.role == 'superadmin' %} ... {% elif session.role == 'org_admin' %} ... {% elif session.role in ('dept_admin', 'viewer') %} ... {% elif session.role == 'hr_viewer' %} ... {% elif session.role == 'employee' %}` chain; all 5 elif branches plus universal Аккаунт item present |
| 4 | User name, role, and logout link appear at sidebar bottom (no top header bar) | VERIFIED | `.sidebar-footer` div at base.html lines 225-229 contains `session.get('username','')`, `session.get('role','')`, and `href="/logout"`; grep `<header` in base.html returns 0 |
| 5 | On screens ≤768px the sidebar hides and hamburger toggles it via overlay | VERIFIED | `@media (max-width: 768px)` rule present; `.sidebar.open` class, `.sidebar-overlay.visible`, `toggleSidebar()` function, and `id="hamburgerBtn"` all confirmed |
| 6 | All CSS color tokens defined as custom properties in :root | VERIFIED | 27 custom properties in :root block (lines 13-39): `--sidebar-bg: #0f172a`, `--accent: #0d9488`, `--sidebar-accent: #0d9488`, full status color pairs, `--radius-card`, `--shadow-card` |
| 7 | All 13 authenticated templates extend base.html | VERIFIED | `head -1` of each: superadmin.html, org_admin.html, dept_admin.html, admin.html, employee.html, dashboard.html, timesheet.html, profile.html, account.html, audit.html, 403.html, devices.html, register.html — all return `{% extends 'base.html' %}` |
| 8 | No #1565C0 or #0d47a1 old blue remains in any converted template | VERIFIED | `grep -vE comment_lines ... \| grep -c "#1565C0\|#0d47a1"` returns 0 across all 13 templates; also 0 in reports_partial.html, timesheet_partial.html, error_token.html |
| 9 | All converted templates have DOCTYPE/header/nav-tabs removed | VERIFIED | grep for `<!DOCTYPE`, `<header`, `class="nav-tabs"` returns 0 across all 13 converted templates |
| 10 | All converted templates have `{% block content %}` and `h1.page-title` | VERIFIED | All 13 templates: `{% block content %}` count = 1. 12/13 have page-title; 403.html uses h2 per plan spec (intentional exception to D-05 for error pages — plan action explicitly specified h2) |
| 11 | switchTab() preserved and functional in multi-panel pages | VERIFIED | `function switchTab` present in superadmin.html (1), org_admin.html (1), admin.html (1); dead `.tab` getElementById references removed (`getElementById('tabOrgs')` = 0 in superadmin.html) |
| 12 | T-13 grid renders full-width with horizontal scroll | VERIFIED | `overflow-x` count in employee.html = 2, in timesheet.html = 1; no `.page` max-width wrapper on T-13 grid |
| 13 | 403.html role-based return links preserved | VERIFIED | `url_for('dashboard_page')` count = 1, `url_for('admin_page')` count = 1 in 403.html |
| 14 | reports_partial.html and timesheet_partial.html have no extends/DOCTYPE shell | VERIFIED | `{% extends` count = 0 in both; `<!DOCTYPE` count = 0 in both; no nav-tabs (`class="nav-tabs"` = 0); chart.js CDN script present (grep -ci "chart" = 10); `var(--accent)` count = 1 |
| 15 | error_token.html stays standalone with Inter font, teal, no session | VERIFIED | Starts with `<!DOCTYPE html>`; `{% extends` = 0; Inter font CDN present (`fonts.googleapis.com/css2` = 1); `'Inter'` in font-family = 1; `{{ message }}` = 1; `session` = 0; no old blue = 0 |
| 16 | kiosk.html, login.html, register_token.html remain standalone (D-12) | VERIFIED | All three start with `<!DOCTYPE html>`; none contain `{% extends` |
| 17 | All Jinja2 templates parse through extends chain cleanly; Flask app imports | VERIFIED | Jinja2 Environment parse: OK for all 17 templates including base.html, all 13 converted children, 2 partials, error_token.html. Flask `from app import app` prints `app OK` |

**Score:** 17/17 truths verified

### Notes on D-05 Deviation in 403.html

`403.html` uses `h2` instead of `h1.page-title`. D-05 states "e.g., an h1 or breadcrumb" — the plan action explicitly specified h2 for this error page ("error page exception to D-05"). This is intentional and documented in 08-05-SUMMARY.md. Not a gap.

### Requirements Coverage

Phase 8 requirement IDs (D-01..D-16) are design decisions from `08-CONTEXT.md`, explicitly noted in ROADMAP.md as "Requirements: D-01..D-16 (design decisions from 08-CONTEXT.md)". These are not tracked in REQUIREMENTS.md (which covers AUTH-*, ORG-*, T13-*, etc.). No Phase 8 plans claim any REQUIREMENTS.md IDs. No orphaned requirements.

| Decision | Description | Status |
|----------|-------------|--------|
| D-01 | Replace horizontal nav-tabs with fixed sidebar | VERIFIED |
| D-02 | Sidebar is role-aware (6 roles, Jinja2 if/elif) | VERIFIED |
| D-03 | Sidebar nav items use icons + text labels | VERIFIED |
| D-04 | User info at sidebar bottom, no top header | VERIFIED |
| D-05 | Page title as first content element | VERIFIED (403.html uses h2 per plan spec) |
| D-06 | Dark sidebar + light content (#0f172a / #f8fafc) | VERIFIED |
| D-07 | Teal accent (#0d9488) replaces blue (#1565C0) | VERIFIED |
| D-08 | Inter font from Google Fonts CDN | VERIFIED |
| D-09 | Full component redesign (cards, tables, buttons, badges) | VERIFIED |
| D-10 | base.html created; all authenticated pages extend it | VERIFIED |
| D-11 | base.html contains font CDN, shared CSS, sidebar, content wrapper | VERIFIED |
| D-12 | kiosk.html and login.html stay standalone | VERIFIED |
| D-13 | Shared CSS in base.html inline style block | VERIFIED |
| D-14 | All authenticated templates redesigned (incl. 403.html, error_token.html) | VERIFIED |
| D-15 | Hamburger/overlay responsiveness at ≤768px | VERIFIED (code) |
| D-16 | devices.html gets base template treatment | VERIFIED |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|---------|--------|---------|
| `templates/base.html` | Shared layout shell: CSS tokens, sidebar, role-nav, hamburger JS, content block | VERIFIED | 250 lines; valid HTML5; all structural elements confirmed |
| `templates/superadmin.html` | base.html child (pilot conversion) | VERIFIED | extends base.html; switchTab() preserved; no old blue |
| `templates/org_admin.html` | base.html child | VERIFIED | extends base.html; switchTab() preserved |
| `templates/dept_admin.html` | base.html child | VERIFIED | extends base.html |
| `templates/admin.html` | base.html child | VERIFIED | extends base.html; superadmin Пользователи guard intact |
| `templates/employee.html` | base.html child | VERIFIED | extends base.html; overflow-x:auto on T-13 grid |
| `templates/dashboard.html` | base.html child | VERIFIED | extends base.html |
| `templates/timesheet.html` | base.html child (full-width T-13) | VERIFIED | extends base.html; overflow-x:auto; no .page wrapper on grid |
| `templates/profile.html` | base.html child; no {{ username }} | VERIFIED | extends base.html; grep `{{ username }}` = 0 |
| `templates/account.html` | base.html child | VERIFIED | extends base.html |
| `templates/audit.html` | base.html child | VERIFIED | extends base.html |
| `templates/403.html` | base.html child; role return links preserved | VERIFIED | extends base.html; both url_for return links present |
| `templates/devices.html` | base.html child; dark header removed (D-16) | VERIFIED | extends base.html; grep `#0d1429` = 0 |
| `templates/register.html` | base.html child | VERIFIED | extends base.html; h1.page-title present |
| `templates/reports_partial.html` | Fragment: teal tokens, no shell, no nav-tabs, chart.js | VERIFIED | No extends; no DOCTYPE; nav-tabs = 0; chart refs = 10; var(--accent) = 1 |
| `templates/timesheet_partial.html` | Fragment: teal tokens, no shell | VERIFIED | No extends; no DOCTYPE |
| `templates/error_token.html` | Standalone public page with Inter + teal (D-14, D-12) | VERIFIED | <!DOCTYPE> kept; no extends; Inter font present; no session |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| templates/base.html | session.role | Jinja2 `{% if session.role == ... %}` chain in sidebar nav | VERIFIED | All 5 role checks confirmed in base.html lines 153-219 |
| templates/base.html | Inter font | Google Fonts CDN `<link>` in `<head>` | VERIFIED | `fonts.googleapis.com/css2?family=Inter:wght@400;500;600` at line 9 |
| templates/superadmin.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed; extends chain parses cleanly |
| templates/org_admin.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed |
| templates/dept_admin.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed |
| templates/admin.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed |
| templates/employee.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed |
| templates/timesheet.html | templates/base.html | `{% extends 'base.html' %}` + `{% block content %}` | VERIFIED | First line confirmed |
| templates/profile.html | session.get('username') | base.html sidebar footer reads session (page passes no username) | VERIFIED | grep `{{ username }}` in profile.html = 0; base.html uses `session.get('username','')` |
| templates/reports_partial.html | var(--accent) | CSS token replacement of #1565C0 | VERIFIED | var(--accent) count = 1; old blue = 0 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Flask app imports (no Jinja2 syntax errors) | `SECRET_KEY=testkey venv/bin/python -c "from app import app; print('app OK')"` | `app OK` | PASS |
| All 17 templates parse through extends chain | `Jinja2 Environment.get_template() for all 17 files` | All 17: `OK` | PASS |
| No old blue in all 17 modified files | `grep -vE comment \| grep -c "#1565C0\|#0d47a1"` | `0` | PASS |
| base.html reaches 220+ line threshold | `wc -l templates/base.html` | `250` | PASS |

### Anti-Patterns Found

None. No TBD/FIXME/XXX markers in any phase-modified file. The only "placeholder" text found is HTML input `placeholder="••••••••"` attribute text in profile.html (normal form UI pattern).

### Human Verification Required

#### 1. Visual Sidebar Rendering

**Test:** Log in as superadmin and inspect the sidebar visually.
**Expected:** Dark navy sidebar (#0f172a) on the left; content area light (#f8fafc) on the right; active nav item highlighted in teal (#0d9488); Inter font visible; no horizontal header bar at the top.
**Why human:** CSS rendering and font loading require browser execution.

#### 2. Mobile Hamburger Toggle

**Test:** Resize browser to ≤768px (or use DevTools mobile emulation) and tap the ☰ hamburger button.
**Expected:** Sidebar slides in from left with 0.25s transition; semi-transparent overlay appears over content; tapping the overlay or pressing Escape closes the sidebar and removes the overlay.
**Why human:** JavaScript interaction and CSS transition require browser execution.

#### 3. Role-Based Nav Item Rendering

**Test:** Log in as each of the six roles and inspect the sidebar nav.
**Expected:** superadmin: 5 items + Аккаунт. org_admin: 8 items + Аккаунт. dept_admin/viewer: 4 items + Аккаунт. hr_viewer: 1 item + Аккаунт. employee: 1 item + Аккаунт. No cross-role items visible.
**Why human:** Requires a live session with each role value; Jinja2 server-side rendering confirmed by code, but actual browser render needs visual check.

#### 4. Content Layout (Sidebar + Content Side-by-Side)

**Test:** Navigate to /superadmin, /timesheet, /profile, and /register (authenticated).
**Expected:** On each page: sidebar fixed on left, main content renders to the right inside the layout, h1.page-title is the first visible heading, no blank or broken content area.
**Why human:** Layout rendering (flexbox sidebar + margin-left content) cannot be confirmed by grep.

#### 5. Standalone Public error_token.html

**Test:** Navigate to `/register/invalid-token-value` to trigger error_token.html.
**Expected:** Centered card page (no sidebar), teal logo icon, Inter font, error message displayed, page is visually consistent with new design system.
**Why human:** Public route rendering with no session requires browser test.

---

_Verified: 2026-06-25T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
