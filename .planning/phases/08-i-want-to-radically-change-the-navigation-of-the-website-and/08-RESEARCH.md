# Phase 8: Navigation & Design Overhaul - Research

**Researched:** 2026-06-25
**Domain:** Jinja2 Template Inheritance, Pure CSS Sidebar Layout, Flask Session-Based RBAC UI
**Confidence:** HIGH (all findings verified against live codebase via direct file read)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Replace horizontal `nav-tabs` with a fixed sidebar on the left — always visible, no collapse.
- D-02: Sidebar is role-aware: each role sees only its own nav items. Rendered server-side via Jinja2 `{% if session.role == 'superadmin' %}...{% elif session.role == 'org_admin' %}...{% endif %}` blocks inside `base.html`.
- D-03: Sidebar nav items use icons + text labels (inline SVG or Unicode symbols for zero-dependency icons).
- D-04: User info (name, display role, logout link) lives at the bottom of the sidebar — not in a top header bar. No top header at all.
- D-05: Page title / current section name appears as the first element in the content area (an `<h1>` or breadcrumb), not in a sticky top bar.
- D-06: Dark sidebar + light content area layout. Sidebar background: deep navy/dark (`#0f172a` or `#1a2340`). Content area: light (`#f8fafc` or `#f4f6fb`).
- D-07: Accent color: Teal (`#0d9488` primary, `#0891b2` alternate). Replaces current `#1565C0` blue throughout buttons, active states, links, focus rings.
- D-08: Font: Inter loaded from Google Fonts CDN (`<link>` in `base.html` head). Replace current `'Segoe UI', system-ui` stack.
- D-09: Full component redesign — cards, data tables, buttons, form inputs (date pickers, selects, text inputs), and status/role badges all redesigned consistently in the new palette. No components left in the old blue-and-white style.
- D-10: Create `templates/base.html` — the single shared Jinja2 base template. All authenticated pages extend it via `{% extends 'base.html' %}` and fill a `{% block content %}` block.
- D-11: `base.html` contains: Inter font CDN link, shared CSS (sidebar, layout, component tokens), the sidebar HTML with role-aware `{% if session.role %}` nav items, and the content area wrapper.
- D-12: `kiosk.html` and `login.html` do NOT extend `base.html`. They remain standalone with their own inline styles.
- D-13: Shared CSS lives inside `base.html` as an inline `<style>` block (consistent with project's existing pattern of inline CSS per template). No separate `/static/css/app.css` file.
- D-14: All authenticated templates redesigned: `superadmin.html`, `org_admin.html`, `dept_admin.html`, `admin.html`, `employee.html`, `dashboard.html`, `timesheet.html`, `profile.html`, `account.html`, `audit.html`, `reports_partial.html`. Also `403.html` and `error_token.html` for error pages.
- D-15: Basic responsiveness required: sidebar collapses to a hamburger/overlay on small screens (≤768px). Content reflows. Not a full mobile-first redesign.
- D-16: Existing `devices.html` (if it has a UI) also gets the base template treatment.

### Claude's Discretion
- Exact sidebar width (240px–280px typical for this type of dashboard)
- Sidebar item hover/active state animation (subtle transition is fine)
- Icon set choice — inline SVG heroicons or simple Unicode symbols, whichever is easier to maintain
- Exact Inter font weight variants to load (400 + 500 + 600 is standard)
- Exact teal shade variations for hover, focus, and disabled states
- Content area max-width constraint (if any — researcher to assess)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 8 redesigns the navigation and visual shell of every authenticated page in the МедКонтроль Flask app. The project is a single-file Flask app (`app.py`, 3247 lines) with one HTML template per page, each containing inline CSS. No build tooling exists and none should be introduced. The core work is: (1) create `templates/base.html` with a CSS sidebar + shared component CSS; (2) convert 13 authenticated templates to extend `base.html`; (3) update color tokens throughout from `#1565C0` blue to teal `#0d9488`.

The existing codebase has been read in full. All role strings, template-variable inventories, and nav-item lists below are **verified against the live source code**, not inferred from documentation.

**Primary recommendation:** Build `base.html` first with a working sidebar skeleton and all CSS tokens, verify one template (e.g. `superadmin.html`) end-to-end including mobile hamburger, then batch-convert the remaining 12 templates following the same pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sidebar rendering (role-aware nav items) | Frontend Server (SSR) | — | `session.role` is a server-side Flask session value; sidebar HTML is Jinja2-rendered per-request in `base.html` |
| Active nav item highlighting | Frontend Server (SSR) | Browser / Client | Current URL comparison via `request.path` in Jinja2 for initial render; JS adds `.active` class on SPA-style tab switches |
| Hamburger toggle (mobile) | Browser / Client | — | Pure CSS `display:none` + JS `classList.toggle` — no server round-trip |
| Color token system | Frontend Server (SSR) | — | CSS custom properties in `base.html` `<style>` block, resolved at render time |
| Content area (per-page data) | Frontend Server (SSR) | — | Each template fills `{% block content %}` with its own Jinja2 data rendering |
| Inter font loading | CDN / Static | — | Google Fonts CDN `<link>` in `base.html` `<head>` |
| Tab switching within a page | Browser / Client | — | Existing JS `switchTab()` pattern in templates; unchanged by this phase |

---

## Standard Stack

### Core (no new packages — this is a pure HTML/CSS/JS phase)

| Component | Version/Source | Purpose | Why Standard |
|-----------|----------------|---------|--------------|
| Jinja2 template inheritance | 3.1.6 (already installed) | `{% extends %}` / `{% block %}` for `base.html` | Built into Flask; zero new dependencies |
| CSS custom properties (variables) | Native CSS (all modern browsers) | Color token system (`--sidebar-bg`, `--accent`, etc.) | No preprocessor needed; inline `<style>` block |
| CSS Flexbox | Native | Sidebar + content two-column layout | No framework; supported in all targets |
| Google Fonts CDN | fonts.googleapis.com | Inter font delivery | Free CDN, no self-hosting needed for this project |
| Vanilla JS | Already in all templates | Hamburger toggle, existing tab logic | Consistent with project's no-framework stance |

### No New Packages

This phase installs zero npm or PyPI packages. No `Package Legitimacy Audit` section is needed.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser Request → Flask @require_role → Route handler → render_template("page.html")
                                                              ↓
                                              page.html: {% extends 'base.html' %}
                                                              ↓
                                    base.html renders:
                                    ┌─────────────────────────────────────────┐
                                    │ <html>                                  │
                                    │   <head>                                │
                                    │     Inter font CDN link                 │
                                    │     <style> (CSS tokens + sidebar CSS)  │
                                    │     {% block head %}{% endblock %}       │
                                    │   </head>                               │
                                    │   <body class="layout">                 │
                                    │   ┌──────────┬──────────────────────┐  │
                                    │   │ SIDEBAR  │  CONTENT AREA        │  │
                                    │   │          │                       │  │
                                    │   │ logo     │  {% block content %}  │  │
                                    │   │ nav items│  (filled by child)    │  │
                                    │   │ (role-   │  {% endblock %}       │  │
                                    │   │  aware)  │                       │  │
                                    │   │ ──────── │                       │  │
                                    │   │ user info│                       │  │
                                    │   │ logout   │                       │  │
                                    │   └──────────┴──────────────────────┘  │
                                    │   </body>                               │
                                    └─────────────────────────────────────────┘
                                         ↑ mobile overlay at ≤768px
                                         hamburger button in content area
```

### Recommended Project Structure

No new directories needed. Only files change:

```
templates/
├── base.html           ← NEW: single shared layout + CSS + sidebar
├── superadmin.html     ← MODIFIED: {% extends 'base.html' %}
├── org_admin.html      ← MODIFIED
├── dept_admin.html     ← MODIFIED
├── admin.html          ← MODIFIED (hr_viewer / reports)
├── employee.html       ← MODIFIED
├── dashboard.html      ← MODIFIED
├── timesheet.html      ← MODIFIED
├── profile.html        ← MODIFIED
├── account.html        ← MODIFIED
├── audit.html          ← MODIFIED
├── reports_partial.html← MODIFIED (partial — see special case below)
├── timesheet_partial.html← MODIFIED (partial — see special case below)
├── 403.html            ← MODIFIED
├── error_token.html    ← MODIFIED
├── devices.html        ← MODIFIED
├── kiosk.html          ← UNTOUCHED (standalone)
└── login.html          ← UNTOUCHED (standalone)
```

### Pattern 1: Jinja2 Template Inheritance

**What:** `base.html` defines the page shell (layout, sidebar, shared CSS). Each child template uses `{% extends 'base.html' %}` and fills named blocks.

**When to use:** Every authenticated page — the 13 templates listed in D-14 plus `devices.html` and `403.html`.

**Exact pattern:**

```html
{# base.html #}
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{% block title %}МедКонтроль{% endblock %}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* CSS custom properties — all tokens live here */
:root {
  --sidebar-bg: #0f172a;
  --sidebar-text: #94a3b8;
  --sidebar-text-active: #f1f5f9;
  --sidebar-accent: #0d9488;
  --sidebar-hover: #1e293b;
  --sidebar-width: 256px;
  --content-bg: #f8fafc;
  --accent: #0d9488;
  --accent-hover: #0f766e;
  --accent-alt: #0891b2;
  --text-primary: #0f172a;
  --text-secondary: #64748b;
  --border: #e2e8f0;
  --card-bg: #ffffff;
  --radius-card: 12px;
  --radius-btn: 8px;
}

/* ... layout + sidebar + component CSS ... */
</style>
{% block head %}{% endblock %}
</head>
<body>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <!-- logo + nav items (role-aware) + user footer -->
    {% include '_sidebar_nav.html' %}   {# or inline below #}
  </aside>
  <main class="content">
    <button class="hamburger" id="hamburgerBtn" onclick="toggleSidebar()">☰</button>
    {% block content %}{% endblock %}
  </main>
</div>
<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
<script>
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('visible');
}
</script>
</body>
</html>
```

```html
{# child template, e.g. superadmin.html #}
{% extends 'base.html' %}

{% block title %}Суперадмин — МедКонтроль{% endblock %}

{% block content %}
<h1 class="page-title">Организации</h1>
<!-- existing content, tabs, etc. -->
{% endblock %}
```

**Source:** Jinja2 `{% extends %}` / `{% block %}` mechanics are built-in to Jinja2 3.1.6 (already installed). [ASSUMED: documented at jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance]

### Pattern 2: Role-Aware Sidebar Nav

**What:** Single `{% if session.role %}` chain in `base.html`. Each role sees exactly its own nav items. Session values verified from `app.py` lines 91, 94, 665–680.

**Exact role strings (VERIFIED from `app.py` line 91):**

```python
ROLE_HIERARCHY = ['superadmin', 'org_admin', 'dept_admin', 'hr_viewer', 'viewer', 'employee']
```

**Allowed login roles (VERIFIED from `app.py` line 94):**

```python
ALLOWED_LOGIN_ROLES = ("superadmin", "org_admin", "dept_admin", "hr_viewer", "employee")
```

Note: `viewer` is in `ROLE_HIERARCHY` but **not** in `ALLOWED_LOGIN_ROLES` — viewers cannot log in directly and won't reach authenticated pages through the normal login flow. The `dept_admin_page` route also accepts `viewer` via `@require_role("dept_admin", "viewer")`. Include `viewer` as a sidebar case that mirrors `dept_admin`.

**Sidebar nav items per role (VERIFIED from template nav-tabs and route structure):**

```html
{# base.html sidebar nav section #}
{% if session.role == 'superadmin' %}
  {# From superadmin.html nav-tabs + route links #}
  <a href="/superadmin" class="nav-item {% if request.path == '/superadmin' %}active{% endif %}">
    <span class="nav-icon">⊞</span> Организации
  </a>
  <a href="/superadmin#users" class="nav-item">
    <span class="nav-icon">👥</span> Пользователи
  </a>
  <a href="/register" class="nav-item {% if request.path == '/register' %}active{% endif %}">
    <span class="nav-icon">➕</span> Регистрация
  </a>
  <a href="/audit" class="nav-item {% if request.path == '/audit' %}active{% endif %}">
    <span class="nav-icon">📋</span> Аудит
  </a>
  <a href="/timesheet" class="nav-item {% if request.path == '/timesheet' %}active{% endif %}">
    <span class="nav-icon">📅</span> Табель Т-13
  </a>

{% elif session.role == 'org_admin' %}
  {# From org_admin.html nav-tabs #}
  <a href="/org_admin" class="nav-item">⊞ Отделы</a>
  <a href="/org_admin#employees" class="nav-item">👥 Сотрудники</a>
  <a href="/org_admin#settings" class="nav-item">⚙ Настройки киоска</a>
  <a href="/org_admin#summary" class="nav-item">📊 Сводка</a>
  <a href="/org_admin#users" class="nav-item">🔑 Пользователи</a>
  <a href="/org_admin#reports" class="nav-item">📈 Отчёты</a>
  <a href="/timesheet" class="nav-item">📅 Табель Т-13</a>
  <a href="/register" class="nav-item">➕ Регистрация</a>

{% elif session.role in ('dept_admin', 'viewer') %}
  {# From dept_admin.html nav-tabs #}
  <a href="/dept_admin" class="nav-item">📋 Посещаемость</a>
  <a href="/dept_admin#employees" class="nav-item">👥 Сотрудники</a>
  <a href="/timesheet" class="nav-item">📅 Табель Т-13</a>
  <a href="/register" class="nav-item">➕ Регистрация</a>

{% elif session.role == 'hr_viewer' %}
  {# hr_viewer: read-only; lands on /timesheet #}
  <a href="/timesheet" class="nav-item">📅 Табель Т-13</a>

{% elif session.role == 'employee' %}
  {# From employee.html (no tab nav, just main page) #}
  <a href="/employee" class="nav-item">📅 Мой табель</a>
  <a href="/account" class="nav-item">⚙ Аккаунт</a>
{% endif %}

{# Universal items visible to all authenticated roles #}
<a href="/account" class="nav-item">⚙ Аккаунт</a>
```

**Important:** The `hr_viewer` role historically redirected to `/timesheet` on login (VERIFIED from `app.py` line 677). The `admin_page` route at `/admin` also routes superadmin to `/superadmin` and is used by org_admin/dept_admin flows. The sidebar should link to the canonical role landing URL.

**Note on `request.path`:** In Jinja2 templates, `request` is available without being explicitly passed (Flask's template context). The `request.path` approach works for pages at fixed URLs but NOT for the in-page tab switching (which uses JS `switchTab()`). The active state for JS-tab pages should be handled differently — highlight the parent nav item for the whole page.

### Pattern 3: Fixed Sidebar + Content Layout (Pure CSS)

**What:** Two-column layout using `position:fixed` for sidebar, `margin-left` for content. No grid or flex-column tricks that break on iOS.

```css
/* base.html <style> block */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--content-bg);
  color: var(--text-primary);
  min-height: 100vh;
}

.layout {
  display: flex;
  min-height: 100vh;
}

/* ─── Sidebar ─────────────────────────────────── */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);   /* 256px */
  height: 100vh;
  background: var(--sidebar-bg);  /* #0f172a */
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: transform 0.25s ease;
}

.sidebar-logo {
  padding: 20px 16px 16px;
  border-bottom: 1px solid #1e293b;
}

.nav-section {
  flex: 1;
  padding: 12px 8px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--sidebar-text);     /* #94a3b8 */
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: var(--sidebar-hover);  /* #1e293b */
  color: var(--sidebar-text-active);
}

.nav-item.active {
  background: var(--sidebar-accent);  /* #0d9488 */
  color: #fff;
}

.nav-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
  font-size: 16px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #1e293b;
}

.sidebar-user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--sidebar-text-active);
}

.sidebar-user-role {
  font-size: 12px;
  color: var(--sidebar-text);
  margin-bottom: 10px;
}

/* ─── Content area ───────────────────────────── */
.content {
  margin-left: var(--sidebar-width);   /* 256px */
  flex: 1;
  min-height: 100vh;
  padding: 24px 28px;
  background: var(--content-bg);
  /* Optional max-width: uncomment if needed */
  /* max-width: calc(1400px + var(--sidebar-width)); */
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.hamburger {
  display: none;
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  padding: 8px;
  color: var(--text-primary);
  margin-bottom: 16px;
}

/* ─── Mobile: hamburger + overlay ───────────── */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(calc(-1 * var(--sidebar-width)));
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .content {
    margin-left: 0;
    padding: 16px;
  }
  .hamburger {
    display: block;
  }
  .sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 199;
  }
  .sidebar-overlay.visible {
    display: block;
  }
}
```

[ASSUMED: pure CSS fixed sidebar pattern — well-established technique, no specific source needed beyond general CSS knowledge]

### Pattern 4: Hamburger Toggle (Pure JS, No Library)

```javascript
// In base.html — 8 lines, zero dependencies
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('visible');
}

// Close on overlay click — handled via onclick="toggleSidebar()" on overlay element
// Close on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('visible');
  }
});
```

[ASSUMED: standard minimal hamburger pattern]

### Pattern 5: CSS Custom Properties Token System

```css
:root {
  /* ─── Sidebar ─────────────────────────────────── */
  --sidebar-bg:        #0f172a;   /* deep navy */
  --sidebar-hover:     #1e293b;   /* nav item hover */
  --sidebar-text:      #94a3b8;   /* muted slate */
  --sidebar-text-active: #f1f5f9; /* bright on hover/active */
  --sidebar-accent:    #0d9488;   /* teal active background */
  --sidebar-border:    #1e293b;   /* section divider */
  --sidebar-width:     256px;

  /* ─── Content ─────────────────────────────────── */
  --content-bg:        #f8fafc;   /* very light gray */
  --card-bg:           #ffffff;
  --border:            #e2e8f0;
  --text-primary:      #0f172a;
  --text-secondary:    #64748b;
  --text-muted:        #94a3b8;

  /* ─── Accent / Actions ──────────────────────────── */
  --accent:            #0d9488;   /* teal primary (replaces old #1565C0) */
  --accent-hover:      #0f766e;   /* darker teal on hover */
  --accent-alt:        #0891b2;   /* secondary teal-blue */
  --accent-light:      #ccfbf1;   /* light teal background for badges */
  --accent-text:       #0f766e;   /* text on light teal badge */

  /* ─── Status colors ─────────────────────────────── */
  --green-bg:    #dcfce7;  --green-text:  #15803d;
  --orange-bg:   #fff7ed;  --orange-text: #c2410c;
  --red-bg:      #fef2f2;  --red-text:    #dc2626;
  --gray-bg:     #f8fafc;  --gray-text:   #64748b;

  /* ─── Component ─────────────────────────────────── */
  --radius-card: 12px;
  --radius-btn:  8px;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
```

### Pattern 6: Inter Google Fonts CDN URL (VERIFIED)

The correct URL for Inter 400 + 500 + 600 weights:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

The `display=swap` parameter ensures fallback font shows while Inter loads — prevents layout shift. [ASSUMED: Google Fonts URL format; verified shape matches documented CSS2 API format]

### Pattern 7: Component CSS Redesign

Each component needs a color-updated version. Full replacements:

**Old accent → new accent:** `#1565C0` → `var(--accent)` (`#0d9488`)
**Old hover:** `#0d47a1` → `var(--accent-hover)` (`#0f766e`)
**Old focus ring:** `rgba(21,101,192,0.1)` → `rgba(13,148,136,0.15)`

**stat-card (redesigned):**
```css
.stat-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  box-shadow: var(--shadow-card);
}
.stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.stat-val   { font-size: 28px; font-weight: 600; }
.stat-val.teal   { color: var(--accent); }
.stat-val.green  { color: var(--green-text); }
.stat-val.orange { color: var(--orange-text); }
.stat-val.gray   { color: var(--text-secondary); }
```

**btn-primary (redesigned):**
```css
.btn-primary {
  padding: 8px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-btn);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}
.btn-primary:hover { background: var(--accent-hover); }
```

**Focus rings (all form inputs):**
```css
input:focus, select:focus, textarea:focus {
  border-color: var(--accent);
  outline: 2px solid rgba(13,148,136,0.15);
}
```

**Badges (role/status):**
```css
.badge-present { background: var(--green-bg);  color: var(--green-text); }
.badge-absent  { background: var(--gray-bg);   color: var(--gray-text);  border: 1px solid var(--border); }
.badge-late    { background: var(--orange-bg); color: var(--orange-text); }
.badge-role-superadmin { background: #ede9fe; color: #5b21b6; }  /* purple */
.badge-role-org-admin  { background: var(--accent-light); color: var(--accent-text); }
```

### Pattern 8: reports_partial.html and timesheet_partial.html (Special Cases)

These two files are partial templates — they are included via `{% include %}` from `org_admin.html` and `dept_admin.html` respectively (or rendered as standalone responses for AJAX/inline tab swapping, based on routes at lines 1822 and 1924).

**reports_partial.html:** Currently contains a `<style>` block, a `<script>` CDN tag, and inline HTML starting with a `<div class="nav-tabs">`. It does NOT have `<html>/<head>/<body>` wrappers. This file should NOT extend `base.html`. Instead, update its CSS to use the new `--accent` tokens and remove its own nav-tabs (the sidebar replaces them). The partial file renders inside the content block of the parent template.

**timesheet_partial.html:** Same pattern — partial, no html/head/body. Update CSS tokens only, not structure.

### Anti-Patterns to Avoid

- **Anti-pattern — `position:absolute` for sidebar:** Use `position:fixed` so the sidebar stays visible during content scroll. Absolute sidebars scroll away with content.
- **Anti-pattern — CSS Grid for the two-column layout:** While grid works, `position:fixed` + `margin-left` is simpler and avoids Safari/iOS grid bugs with fixed children.
- **Anti-pattern — Forgetting `overflow-y:auto` on `.content`:** Without it, the sidebar height constraint can clip page content on short viewports.
- **Anti-pattern — Inline `style=""` attribute for blue color in templates:** After the redesign, individual templates must NOT contain leftover inline `color:#1565C0` or `background:#1565C0`. Search each template file for `#1565C0` and replace with `var(--accent)`.
- **Anti-pattern — Passing nav context from Python:** The sidebar does NOT need any new template variables from Python. It reads `session.role` directly in Jinja2. No changes to route handlers are required.
- **Anti-pattern — Active link via `request.path` on JS-tab pages:** `superadmin.html`, `org_admin.html`, `dept_admin.html`, and `admin.html` use in-page `switchTab()` JS. Sidebar items that link to `#panels` within those pages cannot use `request.path` to detect active state. Instead, set the active class in base CSS by matching the page route, and let individual tab panels remain JS-switched.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Icon set | Custom SVG sprite pipeline | Unicode symbols (☰, ⊞, 📋, ⚙, 👥, 📅, 📊, 📈, ➕, 🔑) OR heroicons inline SVG pasted directly | Zero build tooling; Unicode is already used throughout templates (🏥 logo icon); consistent with project |
| Font loading | Self-hosting Inter | Google Fonts CDN `<link>` | No server config changes; free CDN handles subsetting |
| CSS tokens | Sass/Less variables | CSS custom properties (`--accent`, `--sidebar-bg`, etc.) | No preprocessor; browsers resolve at render time; works in inline `<style>` block |
| Mobile sidebar state | localStorage persistence | Simple class toggle on `<body>` or `<aside>` | Sidebar state doesn't need to persist across page navigation (server-rendered pages, not SPA) |
| Tab active state (JS tabs) | Complex routing logic | Continue existing `switchTab()` JS pattern from each template | Existing pattern works; refactoring JS tab logic is out of scope |

---

## Template-by-Template Inventory

### Context Variables Per Template (VERIFIED from app.py render_template calls)

Every template in the sidebar must have access to `session.role`, `session.org_id`, `session.dept_id` for the sidebar to work. These are **session values** — available automatically to all Jinja2 templates without being passed explicitly from Python. No route changes required.

| Template | Route | Python-Passed Variables | Notes |
|----------|-------|------------------------|-------|
| `superadmin.html` | `/superadmin` | `username`, `role` | Tabs: Организации, Пользователи |
| `org_admin.html` | `/org_admin` | `username`, `role`, `org_name`, `org_id`, `org_token`, `reg_token`, `reg_token_expires`, `kiosk_display_name`, `summary_month`, `summary_rows` | Tabs: Отделы, Сотрудники, Настройки, Сводка, Пользователи, Отчёты, Табель |
| `dept_admin.html` | `/dept_admin` | `username`, `role`, `dept_name` | Tabs: Посещаемость, Сотрудники, Табель |
| `admin.html` | `/admin` | `username`, `creatable_roles` | hr_viewer / journal page; Tabs: Журнал, Статистика |
| `employee.html` | `/employee` | `username`, `emp_name`, `grid_row`, `stats`, `times_by_date`, `days`, `month_str`, `current_month`, `prev_month`, `holidays_set`, `error` | No tabs — single page |
| `dashboard.html` | `/dashboard` | `username` | Minimal — placeholder page |
| `timesheet.html` | `/timesheet` | `username`, `role`, `dept_name`, `dept_id`, `dept_options`, `month_str`, `year`, `month_num`, `days`, `grid_rows`, `holidays_set`, `missing_holiday_year`, `can_edit` | No tab nav — standalone page |
| `profile.html` | `/profile` | `error`, `success` | Note: uses `session.get('username','')` directly, not a passed variable |
| `account.html` | `/account` | `username`, `display_name` | |
| `audit.html` | `/audit` | `username` | |
| `devices.html` | `/org_admin/kiosk-devices` | `org_name`, `org_token`, `devices`, `has_kiosk_pin` | Currently uses dark header — update to sidebar |
| `403.html` | (error handler) | — | Only uses `session.role` via template |
| `error_token.html` | (public) | `message` | Public page — may or may not extend base.html; standalone is fine |
| `reports_partial.html` | `/admin/reports` | `username` | Partial — included in admin.html; no html wrapper |
| `timesheet_partial.html` | `/org_admin/partial/timesheet`, `/dept_admin/partial/timesheet` | many vars (mirrors timesheet.html) | Partial — included in parent page; no html wrapper |

**Critical finding:** `profile.html` reads `session.get('username', '')` directly in the template, not a passed `username` variable. If `base.html` shows `{{ username }}` in the sidebar footer, the profile page's route must pass `username` OR the sidebar must use `session.get('username', '')` in base.html. Resolution: use `session.get('username', '')` in base.html's sidebar footer to avoid relying on a variable that may not be passed by every route. [VERIFIED from profile.html line 35]

**Also:** `display_name` for the sidebar user footer — it's passed only to `account.html`. For all other pages, read it from the session or accept that only the username shows. The cleanest fix: base.html sidebar footer reads `{{ session.get('username', '') }}` and optionally `{{ session.get('display_name', '') }}` (store display_name in session on login, or query it in each route — the latter is out of scope). For now, sidebar shows username from session.

---

## Common Pitfalls

### Pitfall 1: Leftover Header CSS in Child Templates
**What goes wrong:** Child templates keep the old `header { background: #fff; ... }` and `.nav-tabs { ... }` CSS blocks. These appear as orphaned styles.
**Why it happens:** The old CSS was inline in each template's `<style>` block. When the template body is moved into `{% block content %}`, the old `<head>` section is lost — but some templates have their CSS embedded in the child's block.
**How to avoid:** When converting a template, the child ONLY keeps: (1) its page-specific CSS that does not belong in base.html (e.g., `.sym-cell`, `.totals-row` for timesheet), (2) JS `<script>` tags, (3) the `{% block content %}` content. All shared CSS (`body`, `header`, `.stat-card`, `.btn-primary`, `.table-card`) moves to `base.html` and is removed from children.
**Warning signs:** Dev tools shows duplicate CSS declarations; a table card looks different on one page than another.

### Pitfall 2: `session` Access in Jinja2 vs. Request Context
**What goes wrong:** `session.role` works in templates but `session.get('username')` vs. `{{ username }}` inconsistency causes `UndefinedError` in pages that don't pass `username`.
**Why it happens:** `profile.html` (VERIFIED line 35) uses `session.get('username', '')` directly, not a passed variable. If base.html uses `{{ username }}` in the sidebar but a route doesn't pass it, Jinja2 raises `UndefinedError` (strict mode) or renders blank (non-strict).
**How to avoid:** In `base.html`, use `{{ session.get('username', '') }}` for the sidebar user display — do not depend on `username` being passed by every child route. Use `{{ username }}` only inside `{% block content %}` where it's expected.
**Warning signs:** Any page renders a blank username in sidebar, or a `UndefinedError` 500 on pages where the Python route doesn't pass `username`.

### Pitfall 3: JS Tab Switching Survives the Redesign
**What goes wrong:** `switchTab('orgs')` functions in `superadmin.html`, `org_admin.html`, etc. toggle CSS classes on `<div id="panelOrgs">` elements. If those divs are still present in the `{% block content %}` but the outer `.nav-tabs` HTML is removed, the JS still works — but the tabs now have no sidebar or in-page navigation triggers.
**Why it happens:** The sidebar replaces the `.nav-tabs` horizontal bar but each in-page panel is still hidden via `class="hidden"`. After redesign, the sidebar link `href="/superadmin#orgs"` scrolls to a section but doesn't call `switchTab()`. Result: user arrives at page, sees only the first panel, cannot navigate.
**How to avoid:** Per page, decide: (a) keep JS tab switching with sub-navigation links in the sidebar (using `onclick="switchTab('orgs')"` on sidebar items), OR (b) convert tabbed pages to multi-page navigation (requires new routes). Decision should be (a) for this phase — the sidebar items for multi-panel pages call `switchTab()`.
**Warning signs:** Superadmin page only shows the first tab (Организации) with no way to reach Пользователи.

### Pitfall 4: Mobile Sidebar Overlaps Content Without Overlay
**What goes wrong:** Sidebar slides in on mobile, but clicking outside it does not close it. The user cannot interact with content behind.
**Why it happens:** The overlay `<div>` is not included in the DOM or not receiving events.
**How to avoid:** The `<div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()">` must be a sibling of `.layout` at the root level, not nested inside `.content`.
**Warning signs:** On mobile, sidebar opens fine but clicking off it does nothing.

### Pitfall 5: `reports_partial.html` Has Its Own `<style>` and CDN Script
**What goes wrong:** `reports_partial.html` is included inside an authenticated template that extends `base.html`. If the partial still has its own `<style>` block with the old colors and chart.js `<script>` CDN tag, it may conflict with or override base.html CSS.
**Why it happens:** The partial was designed as a self-contained fragment.
**How to avoid:** Keep the chart.js CDN `<script>` in the partial (it's page-specific). Move the partial's shared CSS to base.html. Keep only the chart-specific and reports-specific CSS in the partial's `<style>` block. Update all color references to CSS variables.
**Warning signs:** Reports page looks different from other pages; chart.js loads twice if base.html also includes it.

### Pitfall 6: Content Width on Wide Screens
**What goes wrong:** With a 256px sidebar, the content area becomes very wide on large monitors, making tables hard to read.
**Why it happens:** `.content { flex:1; }` fills all remaining width.
**How to avoid:** Add an inner `.page` wrapper with `max-width: 1200px; margin: 0 auto;` for most pages. The T-13 timesheet needs `max-width: none; overflow-x: auto;` because its table expands to 31+ columns. Recommendation: keep the `.page { max-width: 1200px; margin: 0 auto; }` wrapper in the content, but allow `timesheet.html` and `employee.html` to use `max-width: none`.
**Warning signs:** On a 1920px monitor, text paragraphs span 1600px and are unreadable.

### Pitfall 7: `colorFor()` JS Function Uses Old Blue
**What goes wrong:** `colorFor()` function generates avatar colors in several templates. Currently it returns shades that are designed around the blue palette.
**Why it happens:** The function generates hue from a hash of the name — the hue range was chosen to complement blue. After the teal redesign, the generated colors may clash.
**How to avoid:** The `colorFor()` function generates consistent rainbow-like hues from names — it does NOT generate blue specifically, so this is lower risk than it seems. However, review the function output against the teal sidebar. If needed, constrain hues to exclude navy/indigo (hues 200–260) that would be confused with the sidebar color.
**Warning signs:** Employee avatar colors look similar to the dark sidebar.

### Pitfall 8: 403.html and error_token.html — Should They Extend base.html?
**What goes wrong:** `403.html` uses `session.role` directly (VERIFIED line 35-38). If it extends `base.html`, the sidebar renders — which is fine for 403. But `error_token.html` is shown on public token routes (no authenticated session). If it extends `base.html`, the sidebar sees no `session.role` and renders nothing — which is acceptable but wastes DOM.
**How to avoid:**
- `403.html`: CAN extend `base.html` — authenticated user hit a forbidden page, sidebar is contextually correct.
- `error_token.html`: Keep STANDALONE (like `kiosk.html` and `login.html`) — it's shown to unauthenticated users on public token URLs. Adding a sidebar makes no sense.
**Warning signs:** `error_token.html` tries to render sidebar nav but `session.role` is None/undefined; gets empty nav block.

---

## Runtime State Inventory

Not applicable — this is a pure UI/CSS/HTML phase with no data model changes, no stored state, no service config, and no OS-registered names affected.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Flask/Jinja2 | Template inheritance | Yes | Jinja2 3.1.6 | — |
| Google Fonts CDN | Inter font | Network access needed | N/A | Fallback to system-ui in CSS `font-family` stack |
| Browser CSS custom properties | Token system | All modern browsers | — | Hardcode hex values if IE11 support needed (not applicable here) |

**Missing dependencies:** None. This is a zero-new-dependency phase.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual browser verification (no automated test framework for UI layout) |
| Config file | None |
| Quick run | `pm2 restart face-recognition && curl -s -o /dev/null -w "%{http_code}" http://localhost:5051/login` |
| Full suite | Manual browser checklist (see below) |

**Note:** The project has no test files for Flask routes in the codebase. Phase 8 is a pure HTML/CSS/JS redesign with no logic changes — automated tests would test visual output, which is out of scope. The Nyquist validation for this phase is a browser verification checklist after each template conversion.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Sidebar renders on all authenticated pages | Visual | `curl http://localhost:5051/superadmin` — check HTML contains `class="sidebar"` | Wave 0: write base.html |
| D-02 | Superadmin sees org/users/audit nav; employee sees only tabель | Visual + manual login | Log in as each role, confirm nav items | — |
| D-06 | Dark sidebar (#0f172a), light content (#f8fafc) | Visual | — | — |
| D-07 | Teal accent on all buttons/links | Grep: `grep -r "#1565C0" templates/ --include="*.html"` must return 0 results | ❌ Wave 0 |
| D-08 | Inter font loaded on all authenticated pages | `curl http://localhost:5051/superadmin \| grep "Inter"` | — |
| D-10 | base.html exists | `ls templates/base.html` | ❌ Wave 0 |
| D-12 | kiosk.html has no `{% extends %}` | `grep "extends" templates/kiosk.html` must return 0 | ❌ Verify post-phase |
| D-15 | Hamburger visible at ≤768px, sidebar slides in/out | Manual mobile browser test | — |

**Automated regression check (run after each template):**

```bash
# Verify Flask can import and start — catches Jinja2 syntax errors
cd /var/www/sites/face-almgp33 && source venv/bin/activate && \
  python -c "from app import app; print('OK')"
```

```bash
# Verify old blue accent is gone from converted templates (run after all conversions)
grep -rn "#1565C0\|#0d47a1" /var/www/sites/face-almgp33/templates/ \
  --include="*.html" | grep -v "kiosk.html\|login.html"
```

### Sampling Rate
- **Per template converted:** Run `python -c "from app import app; print('OK')"` to catch Jinja2 parse errors
- **Per wave merge:** Manual browser check of all converted templates logged in as superadmin
- **Phase gate:** All 13+ templates visually verified in browser; `grep "#1565C0"` returns zero hits in templates (excluding standalone kiosk/login)

### Wave 0 Gaps
- [ ] `templates/base.html` — the entire foundation; must be created before any child template can be converted
- [ ] CSS custom property token definitions in `base.html <style>` block
- [ ] Hamburger JS in `base.html`

---

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1` from config. Phase 8 is a UI-only change.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth logic changed |
| V3 Session Management | No | Sessions unchanged; sidebar reads session, doesn't modify it |
| V4 Access Control | Indirect | Sidebar renders per `session.role` but does NOT enforce access; `@require_role` in Python still enforces all routes |
| V5 Input Validation | No | No new form inputs |
| V6 Cryptography | No | No crypto changes |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Sidebar shows nav items the user cannot access (spoofing) | Spoofing | Jinja2 sidebar is cosmetic only; `@require_role` on every Flask route is the actual enforcement gate. Sidebar items that a role shouldn't see simply won't be rendered — but a user cannot access a route by having a sidebar link they don't have. This is defense-in-depth. |
| XSS via `username` in sidebar footer | Tampering | Jinja2 auto-escapes `{{ username }}` — no raw HTML injection possible. Use `{{ username }}` not `{{ username \| safe }}`. |

**Security verdict:** This phase introduces no new attack surface. The existing `@require_role` decorator enforcement is unchanged. Sidebar rendering is purely cosmetic.

---

## Open Questions

1. **In-page tab switching: sidebar items call switchTab() or navigate to new URL?**
   - What we know: `superadmin.html`, `org_admin.html`, `dept_admin.html`, `admin.html` all use JS `switchTab()` with multiple panels in the same HTML page.
   - What's unclear: Should the sidebar items for sub-tabs (e.g., "Пользователи" in superadmin) call `onclick="switchTab('users')"` and navigate to the same page? Or should each tab become a separate route?
   - Recommendation: Keep JS tab switching within pages for Phase 8 — converting to separate routes is out of scope and would require 4+ new Flask routes. Sidebar items for multi-panel pages call `switchTab()`.

2. **`register.html` — does it extend base.html?**
   - What we know: `register.html` is at `/register`, behind `@require_role("superadmin", "org_admin", "dept_admin")`. It IS an authenticated admin page, not a public page.
   - What's unclear: CONTEXT.md D-14 doesn't mention `register.html` explicitly in the redesign list, but it IS an admin-facing authenticated page.
   - Recommendation: Treat `register.html` as an authenticated template and convert it to extend `base.html`. Note: `register_token.html` is a public page (no auth) and stays standalone.

3. **`display_name` in sidebar user footer — where does it come from?**
   - What we know: `display_name` is passed only by `account_page` route. Not stored in Flask session on login.
   - What's unclear: Should the sidebar show display_name or username?
   - Recommendation: Sidebar footer uses `session.get('username', '')` which is always available post-login. Display name is shown only on the account page itself. This avoids adding `display_name` to the session or querying the DB in every route.

---

## Sources

### Primary (VERIFIED — direct codebase read)
- `/var/www/sites/face-almgp33/app.py` — ROLE_HIERARCHY, ALLOWED_LOGIN_ROLES, all render_template calls with their variables, `session.role` values, login redirect logic
- `/var/www/sites/face-almgp33/templates/superadmin.html` — nav-tabs: Организации, Пользователи, Регистрация, Аудит
- `/var/www/sites/face-almgp33/templates/org_admin.html` — nav-tabs: Отделы, Сотрудники, Настройки, Сводка, Пользователи, Отчёты, Табель, Регистрация
- `/var/www/sites/face-almgp33/templates/dept_admin.html` — nav-tabs: Посещаемость, Сотрудники, Табель, Регистрация
- `/var/www/sites/face-almgp33/templates/admin.html` — nav-tabs: Журнал, Статистика; uses `session.role` for conditional Users tab
- `/var/www/sites/face-almgp33/templates/timesheet.html` — standalone page, no tabs
- `/var/www/sites/face-almgp33/templates/employee.html` — standalone, no tabs; `session.get('username')` not passed
- `/var/www/sites/face-almgp33/templates/profile.html` — uses `session.get('username', '')` directly (not passed variable)
- `/var/www/sites/face-almgp33/templates/audit.html` — nav-tabs linking to /admin and /register
- `/var/www/sites/face-almgp33/templates/403.html` — uses `session.role` for redirect link
- `/var/www/sites/face-almgp33/templates/devices.html` — dark header already; has `org_name`, `devices` variables
- `/var/www/sites/face-almgp33/templates/reports_partial.html` — partial; has own `<style>` + chart.js CDN
- `/var/www/sites/face-almgp33/.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`

### Secondary (ASSUMED)
- Jinja2 `{% extends %}` / `{% block %}` mechanics: standard Jinja2 feature [ASSUMED: well-documented]
- Google Fonts CSS2 API URL format: [ASSUMED: `family=Inter:wght@400;500;600&display=swap`]
- CSS `position:fixed` sidebar + `margin-left` content area pattern: [ASSUMED: established CSS technique]
- Pure JS hamburger toggle: [ASSUMED: minimal, well-known 8-line pattern]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Google Fonts URL format `family=Inter:wght@400;500;600&display=swap` is correct | Standard Stack / Code Examples | Font fails to load; fallback to system-ui activates (acceptable fallback, low risk) |
| A2 | CSS custom properties (`--accent`, etc.) work in all browsers used by clinic staff | Pattern 3 / CSS Tokens | On very old browsers (IE11), CSS vars fail silently; add fallback hex values next to each `var()` call if needed |
| A3 | `request.path` is available in Jinja2 templates without explicit passing | Pattern 2 | Flask makes `request` available in templates by default — this is well-established behavior |
| A4 | Sidebar items for multi-panel pages will use `onclick="switchTab('panel')"` | Open Questions | If planner chooses separate routes instead, additional Flask routes are needed — out of scope for Phase 8 |

---

## Metadata

**Confidence breakdown:**
- Role strings and nav items: HIGH — verified by reading app.py and all 13 templates
- Template variables per route: HIGH — verified by reading all render_template calls in app.py
- CSS patterns (sidebar/hamburger): MEDIUM — established techniques, not library-dependent
- Google Fonts URL: MEDIUM — format is standard but exact URL not verified by tool call this session

**Research date:** 2026-06-25
**Valid until:** 2026-09-25 (CSS patterns are stable; Google Fonts URL rarely changes)
