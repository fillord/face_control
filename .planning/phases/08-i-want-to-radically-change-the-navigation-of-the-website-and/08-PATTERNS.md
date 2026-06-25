# Phase 8: Navigation & Design Overhaul - Pattern Map

**Mapped:** 2026-06-25
**Files analyzed:** 15 new/modified templates
**Analogs found:** 14 / 15 (reports_partial.html and timesheet_partial.html are partials with special handling)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `templates/base.html` | layout/shell | request-response | `templates/superadmin.html` (header+nav structure) | structural-match |
| `templates/superadmin.html` | page/view | request-response | itself — current version is the primary analog | exact |
| `templates/org_admin.html` | page/view | request-response | `templates/superadmin.html` (same tab+panel pattern) | role-match |
| `templates/dept_admin.html` | page/view | request-response | `templates/superadmin.html` (same tab+panel pattern) | role-match |
| `templates/admin.html` | page/view | request-response | `templates/superadmin.html` (same nav-tabs pattern) | role-match |
| `templates/employee.html` | page/view | request-response | `templates/profile.html` (no tabs, single-page) | role-match |
| `templates/dashboard.html` | page/view | request-response | `templates/profile.html` (simple single-page) | role-match |
| `templates/timesheet.html` | page/view | request-response | `templates/admin.html` (standalone page, tables) | role-match |
| `templates/profile.html` | page/form | request-response | itself — uses `session.get('username','')` directly | exact |
| `templates/account.html` | page/form | request-response | `templates/profile.html` (form page, same layout) | exact |
| `templates/audit.html` | page/view | request-response | `templates/admin.html` (table page, same nav pattern) | role-match |
| `templates/403.html` | error-page | request-response | itself — centered card, uses `session.role` | exact |
| `templates/devices.html` | page/view | request-response | `templates/superadmin.html` (authenticated, same table card) | role-match |
| `templates/reports_partial.html` | partial | request-response | itself — partial; CSS token update only | partial-special |
| `templates/timesheet_partial.html` | partial | request-response | `templates/timesheet.html` (same grid structure) | role-match |

---

## Pattern Assignments

### `templates/base.html` (NEW — shared layout shell)

**This file does not exist yet. It must be created from scratch following the patterns below.**

**HTML document shell pattern** (copy from `templates/superadmin.html` lines 1–6, then extend):
```html
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
/* all shared CSS lives here */
</style>
{% block head %}{% endblock %}
</head>
<body>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <!-- sidebar content inline -->
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
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('visible');
  }
});
</script>
</body>
</html>
```

**CSS reset + body pattern** (from `templates/superadmin.html` lines 8–9, updated):
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; background: var(--content-bg); color: var(--text-primary); min-height: 100vh; }
```

**CSS token block** (new — no existing analog; use RESEARCH.md Pattern 5):
```css
:root {
  --sidebar-bg:          #0f172a;
  --sidebar-hover:       #1e293b;
  --sidebar-text:        #94a3b8;
  --sidebar-text-active: #f1f5f9;
  --sidebar-accent:      #0d9488;
  --sidebar-border:      #1e293b;
  --sidebar-width:       256px;
  --content-bg:          #f8fafc;
  --card-bg:             #ffffff;
  --border:              #e2e8f0;
  --text-primary:        #0f172a;
  --text-secondary:      #64748b;
  --text-muted:          #94a3b8;
  --accent:              #0d9488;
  --accent-hover:        #0f766e;
  --accent-alt:          #0891b2;
  --accent-light:        #ccfbf1;
  --accent-text:         #0f766e;
  --green-bg:  #dcfce7; --green-text:  #15803d;
  --orange-bg: #fff7ed; --orange-text: #c2410c;
  --red-bg:    #fef2f2; --red-text:    #dc2626;
  --gray-bg:   #f8fafc; --gray-text:   #64748b;
  --radius-card: 12px;
  --radius-btn:  8px;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
```

**Sidebar layout CSS** (new — RESEARCH.md Pattern 3):
```css
.layout { display: flex; min-height: 100vh; }

.sidebar {
  position: fixed; top: 0; left: 0;
  width: var(--sidebar-width); height: 100vh;
  background: var(--sidebar-bg);
  overflow-y: auto; overflow-x: hidden;
  display: flex; flex-direction: column;
  z-index: 200; transition: transform 0.25s ease;
}
.sidebar-logo { padding: 20px 16px 16px; border-bottom: 1px solid var(--sidebar-border); }
.nav-section { flex: 1; padding: 12px 8px; overflow-y: auto; }
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 8px;
  font-size: 14px; font-weight: 500;
  color: var(--sidebar-text); text-decoration: none;
  transition: background 0.15s, color 0.15s; margin-bottom: 2px;
}
.nav-item:hover { background: var(--sidebar-hover); color: var(--sidebar-text-active); }
.nav-item.active { background: var(--sidebar-accent); color: #fff; }
.nav-icon { width: 20px; text-align: center; flex-shrink: 0; font-size: 16px; }
.sidebar-footer { padding: 16px; border-top: 1px solid var(--sidebar-border); }
.sidebar-user-name { font-size: 14px; font-weight: 600; color: var(--sidebar-text-active); }
.sidebar-user-role { font-size: 12px; color: var(--sidebar-text); margin-bottom: 10px; }

.content { margin-left: var(--sidebar-width); flex: 1; min-height: 100vh; padding: 24px 28px; background: var(--content-bg); }
.page { max-width: 1200px; margin: 0 auto; }
.page-title { font-size: 22px; font-weight: 600; color: var(--text-primary); margin-bottom: 20px; }
.hamburger { display: none; background: none; border: none; font-size: 22px; cursor: pointer; padding: 8px; color: var(--text-primary); margin-bottom: 16px; }

@media (max-width: 768px) {
  .sidebar { transform: translateX(calc(-1 * var(--sidebar-width))); }
  .sidebar.open { transform: translateX(0); }
  .content { margin-left: 0; padding: 16px; }
  .hamburger { display: block; }
  .sidebar-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 199; }
  .sidebar-overlay.visible { display: block; }
}
```

**Shared component CSS** (migrate from each template's `<style>` block — these are currently duplicated across all templates):
```css
/* ─── stat-card ─── (from superadmin.html lines 23–29, updated to tokens) */
.stat-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 16px 18px; box-shadow: var(--shadow-card); }
.stat-label { font-size: 11px; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-val { font-size: 26px; font-weight: 600; }
.stat-val.teal   { color: var(--accent); }
.stat-val.green  { color: var(--green-text); }
.stat-val.orange { color: var(--orange-text); }
.stat-val.gray   { color: var(--text-secondary); }
/* keep .stat-val.blue as alias → var(--accent) for any remaining template references */
.stat-val.blue   { color: var(--accent); }

/* ─── table-card ─── (from superadmin.html lines 30–35, updated) */
.table-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; margin-bottom: 20px; }
table { width: 100%; border-collapse: collapse; }
thead { background: #f8fafd; }
th { padding: 12px; text-align: left; font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); white-space: nowrap; }
td { padding: 12px; font-size: 13px; border-bottom: 1px solid #f0f3f8; vertical-align: middle; }
tr:last-child td { border-bottom: none; }

/* ─── buttons ─── (from superadmin.html lines 37–43, updated) */
.btn-primary { padding: 8px 16px; background: var(--accent); color: #fff; border: none; border-radius: var(--radius-btn); font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; transition: background 0.15s; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-secondary { padding: 8px 16px; background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-btn); font-size: 13px; font-weight: 600; cursor: pointer; color: var(--text-secondary); font-family: inherit; }
.btn-edit   { padding: 6px 12px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.btn-edit:hover { background: var(--content-bg); }
.btn-delete { padding: 6px 12px; background: var(--card-bg); border: 1px solid #ef9a9a; border-radius: 6px; font-size: 12px; color: #c62828; cursor: pointer; }
.btn-delete:hover { background: var(--red-bg); }

/* ─── form inputs ─── (from superadmin.html lines 46–48, updated) */
.form-group { margin-bottom: 16px; }
.form-group label { font-size: 13px; font-weight: 600; color: var(--text-secondary); display: block; margin-bottom: 6px; }
.form-group input, .form-group textarea, .form-group select { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-btn); font-size: 13px; color: var(--text-primary); outline: none; font-family: inherit; background: var(--card-bg); }
.form-group input:focus, .form-group textarea:focus, .form-group select:focus { border-color: var(--accent); outline: 2px solid rgba(13,148,136,0.15); }
input[type=date]:focus, select:focus, input[type=text]:focus { border-color: var(--accent); outline: 2px solid rgba(13,148,136,0.15); }

/* ─── card ─── (from superadmin.html line 44, updated) */
.card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 24px; margin-bottom: 20px; }

/* ─── badges ─── (from admin.html lines 45–49, updated) */
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: 14px; font-size: 11px; font-weight: 600; }
.badge-present { background: var(--green-bg);  color: var(--green-text); }
.badge-partial  { background: var(--orange-bg); color: var(--orange-text); }
.badge-absent   { background: var(--gray-bg);   color: var(--gray-text); border: 1px solid var(--border); }
.badge-late     { background: var(--orange-bg); color: #BF360C; border: 1px solid #FFCC80; }
.badge-early    { background: var(--accent-light); color: var(--accent-text); border: 1px solid #a5f3eb; }
.badge-role-superadmin { background: #ede9fe; color: #5b21b6; }
.badge-role-org-admin  { background: var(--accent-light); color: var(--accent-text); }

/* ─── misc shared ─── */
.hidden  { display: none; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.toolbar label { font-size: 13px; font-weight: 500; color: var(--text-secondary); white-space: nowrap; }
.error-msg  { font-size: 13px; color: #c62828; margin-top: 8px; }
.form-actions { display: flex; gap: 10px; margin-top: 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
@media (max-width: 700px) { .stats-grid { grid-template-columns: 1fr 1fr; } }
```

**Role-aware sidebar nav** (from RESEARCH.md Pattern 2; `request.path` available in Jinja2 without being passed):
```html
<nav class="nav-section">
{% if session.role == 'superadmin' %}
  <a href="/superadmin" class="nav-item {% if request.path == '/superadmin' %}active{% endif %}" onclick="if(window.location.pathname==='/superadmin'){switchTab('orgs');return false;}">
    <span class="nav-icon">⊞</span> Организации
  </a>
  <a href="/superadmin" class="nav-item" onclick="switchTab('users');return false;">
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
  <a href="/org_admin" class="nav-item {% if request.path == '/org_admin' %}active{% endif %}">
    <span class="nav-icon">⊞</span> Отделы
  </a>
  <a href="/org_admin" class="nav-item" onclick="switchTab('employees');return false;">
    <span class="nav-icon">👥</span> Сотрудники
  </a>
  <a href="/org_admin" class="nav-item" onclick="switchTab('summary');return false;">
    <span class="nav-icon">📊</span> Сводка
  </a>
  <a href="/org_admin" class="nav-item" onclick="switchTab('reports');return false;">
    <span class="nav-icon">📈</span> Отчёты
  </a>
  <a href="/org_admin" class="nav-item" onclick="switchTab('users');return false;">
    <span class="nav-icon">🔑</span> Пользователи
  </a>
  <a href="/org_admin" class="nav-item" onclick="switchTab('settings');return false;">
    <span class="nav-icon">⚙</span> Настройки
  </a>
  <a href="/timesheet" class="nav-item {% if request.path == '/timesheet' %}active{% endif %}">
    <span class="nav-icon">📅</span> Табель Т-13
  </a>
  <a href="/register" class="nav-item {% if request.path == '/register' %}active{% endif %}">
    <span class="nav-icon">➕</span> Регистрация
  </a>

{% elif session.role in ('dept_admin', 'viewer') %}
  <a href="/dept_admin" class="nav-item {% if request.path == '/dept_admin' %}active{% endif %}">
    <span class="nav-icon">📋</span> Посещаемость
  </a>
  <a href="/dept_admin" class="nav-item" onclick="switchTab('employees');return false;">
    <span class="nav-icon">👥</span> Сотрудники
  </a>
  <a href="/timesheet" class="nav-item {% if request.path == '/timesheet' %}active{% endif %}">
    <span class="nav-icon">📅</span> Табель Т-13
  </a>
  <a href="/register" class="nav-item {% if request.path == '/register' %}active{% endif %}">
    <span class="nav-icon">➕</span> Регистрация
  </a>

{% elif session.role == 'hr_viewer' %}
  <a href="/timesheet" class="nav-item {% if request.path == '/timesheet' %}active{% endif %}">
    <span class="nav-icon">📅</span> Табель Т-13
  </a>

{% elif session.role == 'employee' %}
  <a href="/employee" class="nav-item {% if request.path == '/employee' %}active{% endif %}">
    <span class="nav-icon">📅</span> Мой табель
  </a>
{% endif %}

<a href="/account" class="nav-item {% if request.path == '/account' %}active{% endif %}">
  <span class="nav-icon">⚙</span> Аккаунт
</a>
</nav>
```

**Sidebar footer with user info** (uses `session.get()` — CRITICAL: must NOT use `{{ username }}` variable here since some routes like `profile.html` do not pass it):
```html
<div class="sidebar-footer">
  <div class="sidebar-user-name">{{ session.get('username', '') }}</div>
  <div class="sidebar-user-role">{{ session.get('role', '') }}</div>
  <a href="/logout" style="font-size:13px;color:var(--sidebar-text);text-decoration:none;">Выйти →</a>
</div>
```

---

### `templates/superadmin.html` (MODIFY — extend base.html)

**Analog:** `templates/superadmin.html` (self-reference — current version is the source)

**Current structure to understand** (lines 1–73):
- Lines 1–56: full `<html><head><style>` block — ALL of this moves to `base.html`; the child keeps only page-specific CSS
- Lines 58–66: `<header>` block — REMOVE; replaced by sidebar
- Lines 68–73: `.nav-tabs` block — REMOVE; replaced by sidebar nav items that call `switchTab()`
- Lines 75–end: `.page` divs with `panelOrgs`, `panelUsers` — KEEP inside `{% block content %}`

**Conversion pattern** (child template skeleton):
```html
{% extends 'base.html' %}
{% block title %}Суперадмин — МедКонтроль{% endblock %}

{% block head %}
<style>
/* Only superadmin-specific CSS that does not belong in base.html */
/* e.g., org-specific table columns, form widths */
</style>
{% endblock %}

{% block content %}
<h1 class="page-title">Организации</h1>
<div class="page">
  <!-- panelOrgs and panelUsers divs with .hidden class — unchanged -->
  <!-- JS switchTab() still controls visibility -->
</div>
<script>
/* all existing JS from superadmin.html — unchanged */
function switchTab(tab) { ... }
/* fetch/API functions — unchanged */
</script>
{% endblock %}
```

**switchTab JS pattern to keep** (superadmin.html lines 200–205):
```javascript
function switchTab(tab) {
  document.getElementById('tabOrgs').classList.toggle('active', tab === 'orgs');
  document.getElementById('tabUsers').classList.toggle('active', tab === 'users');
  document.getElementById('panelOrgs').classList.toggle('hidden', tab !== 'orgs');
  document.getElementById('panelUsers').classList.toggle('hidden', tab !== 'users');
}
```
Note: After redesign, `tabOrgs`/`tabUsers` elements no longer exist (nav-tabs removed). Remove those two lines from `switchTab()` — only the panel `.hidden` toggles remain.

**Old blue values to replace in this file:**
- `#1565C0` → `var(--accent)`
- `#0d47a1` → `var(--accent-hover)`
- `rgba(21,101,192,...)` → `rgba(13,148,136,...)`
- `.stat-val.blue` → `.stat-val.teal`

---

### `templates/org_admin.html`, `templates/dept_admin.html`, `templates/admin.html` (MODIFY — same pattern as superadmin.html)

**Analog:** `templates/superadmin.html` conversion pattern above.

**Same conversion steps apply:**
1. Remove `<html><head><style>` — move any page-specific CSS to `{% block head %}<style>...</style>{% endblock %}`
2. Remove `<header>` block entirely
3. Remove `.nav-tabs` div — sidebar replaces it; sidebar links call `switchTab('panel')` via `onclick`
4. Wrap remaining content in `{% extends 'base.html' %}` + `{% block content %}...{% endblock %}`
5. Keep all JS `<script>` blocks inside `{% block content %}` at the bottom

**admin.html note — `session.role` conditional tab** (admin.html lines 83–85):
```html
{% if session.role == 'superadmin' %}
<span class="tab" id="tabUsers" onclick="switchTab('users')">Пользователи</span>
{% endif %}
```
This panel conditional STAYS in the JS `switchTab()` logic and the panel div — the sidebar already handles role-based nav visibility.

---

### `templates/employee.html` (MODIFY — extend base.html, no tabs)

**Analog:** `templates/profile.html` (single-page, no tabs, different content)

**Note:** `employee.html` is a standalone page with no in-page JS tab switching. The content area is entirely `{% block content %}`. No `switchTab()` needed in sidebar — the sidebar link `/employee` is the only nav item for this role.

**Conversion:**
```html
{% extends 'base.html' %}
{% block title %}Мой табель — МедКонтроль{% endblock %}
{% block content %}
<h1 class="page-title">Мой табель</h1>
<div class="page">
  <!-- existing employee grid/table content -->
</div>
<script>/* existing JS */</script>
{% endblock %}
```

---

### `templates/profile.html` (MODIFY — extend base.html, session.get pattern)

**Analog:** itself — `templates/profile.html` lines 1–72

**Critical pattern** (profile.html line 35) — uses `session.get()` NOT a passed variable:
```html
<span class="user-badge">{{ session.get('username', '') }}</span>
```
This is already compatible with `base.html` sidebar pattern. The child template body does NOT need to display username — the sidebar handles it.

**Form focus style to update** (profile.html lines 23–24):
```css
/* OLD: */
input[type=password]:focus { border-color: #1565C0; box-shadow: 0 0 0 3px rgba(21,101,192,0.1); }
/* NEW: */
input[type=password]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(13,148,136,0.15); }
```

**Button to update** (profile.html line 25):
```css
/* OLD: */
.btn { ... background: #1565C0; ... }
.btn:hover { background: #0d47a1; }
/* NEW: */
.btn { ... background: var(--accent); ... }
.btn:hover { background: var(--accent-hover); }
```

**Card shadow to update** (profile.html line 18):
```css
/* OLD: box-shadow: 0 4px 24px rgba(21,101,192,0.07); */
/* NEW: box-shadow: 0 4px 24px rgba(13,148,136,0.07); */
```

**Conversion skeleton:**
```html
{% extends 'base.html' %}
{% block title %}Профиль — МедКонтроль{% endblock %}
{% block head %}
<style>
/* profile-specific CSS only: .card, .form-group, .btn, input[type=password], .error, .success */
/* (these are narrow-page styles that may not be in base.html shared components) */
</style>
{% endblock %}
{% block content %}
<div class="page" style="max-width:480px;">
  <div class="card">
    <h2>Смена пароля</h2>
    <!-- form content unchanged -->
  </div>
</div>
{% endblock %}
```

---

### `templates/account.html` (MODIFY — extend base.html)

**Analog:** `templates/profile.html` (same form layout, same single-page structure)

Same conversion pattern as `profile.html`. The `account.html` route passes `username` and `display_name` — these can still be used inside `{% block content %}` but the sidebar uses `session.get('username', '')`.

---

### `templates/dashboard.html` (MODIFY — extend base.html)

**Analog:** `templates/profile.html` (minimal single page)

Simplest conversion — likely just a placeholder page with no complex CSS. Wrap content in `{% block content %}`.

---

### `templates/timesheet.html` (MODIFY — extend base.html, wide table)

**Analog:** `templates/admin.html` (table-heavy standalone page)

**Special handling required** — T-13 grid spans 31+ columns; needs unrestricted width:
```html
{% block content %}
<h1 class="page-title">Табель Т-13 — {{ month_str }}</h1>
<!-- NO .page wrapper with max-width here — timesheet needs full width -->
<div style="overflow-x: auto;">
  <!-- existing timesheet table -->
</div>
{% endblock %}
```

Do NOT apply `.page { max-width: 1200px }` to timesheet. The `.content` padding (24px 28px) is enough outer spacing.

---

### `templates/audit.html` (MODIFY — extend base.html)

**Analog:** `templates/admin.html` (table page, similar structure)

Standard conversion. `audit.html` currently links to `/admin` and `/register` in its nav-tabs — those become sidebar items. The sidebar for `superadmin` role already includes Аудит, Регистрация links.

---

### `templates/403.html` (MODIFY — extend base.html)

**Analog:** itself — `templates/403.html` lines 1–43

**403 CAN extend base.html** — the user is authenticated (they hit a forbidden page), so `session.role` is set and the sidebar renders correctly. This gives a better UX than a bare error page.

**Current `session.role` check to keep** (403.html lines 35–39):
```html
{% if session.role in ['viewer', 'employee'] %}
<a href="{{ url_for('dashboard_page') }}" class="btn">← Вернуться к панели</a>
{% else %}
<a href="{{ url_for('admin_page') }}" class="btn">← Вернуться к панели</a>
{% endif %}
```

**Conversion:**
```html
{% extends 'base.html' %}
{% block title %}Доступ запрещён — МедКонтроль{% endblock %}
{% block content %}
<div class="page" style="max-width:480px;padding-top:48px;">
  <h2 style="font-size:20px;font-weight:600;margin-bottom:8px;">403 — Доступ запрещён</h2>
  <p style="color:var(--text-secondary);margin-bottom:20px;">У вас нет прав для просмотра этой страницы.</p>
  {% if session.role in ['viewer', 'employee'] %}
  <a href="{{ url_for('dashboard_page') }}" class="btn-primary">← Вернуться к панели</a>
  {% else %}
  <a href="{{ url_for('admin_page') }}" class="btn-primary">← Вернуться к панели</a>
  {% endif %}
</div>
{% endblock %}
```

---

### `templates/devices.html` (MODIFY — extend base.html)

**Analog:** `templates/superadmin.html` (authenticated, table card, similar layout)

**Current dark header** (devices.html lines 10–11):
```css
header { background: #0d1429; ... }
```
This dark header is REPLACED by the sidebar. The sidebar already has a dark background — no special handling needed.

**Blue values to replace** in devices.html (lines 20, 28, 33–34, 37):
- `.count-chip { color: #1565C0; }` → `color: var(--accent)`
- `.device-name-input { border: 1.5px solid #1565C0; }` → `border: 1.5px solid var(--accent)`
- `.btn-rename { color: #1565C0; }` → `color: var(--accent)`
- `.btn-save { background: #1565C0; }` → `background: var(--accent)`
- `.btn-save:hover { background: #0d47a1; }` → `background: var(--accent-hover)`

**Conversion:**
```html
{% extends 'base.html' %}
{% block title %}Устройства киоска — {{ org_name }}{% endblock %}
{% block head %}
<style>
/* devices-specific CSS: .device-card, .device-icon, .device-info, .device-actions, .no-pin-warn, .toast-bar */
/* Update blue values to var(--accent) and var(--accent-hover) */
</style>
{% endblock %}
{% block content %}
<h1 class="page-title">Устройства киоска</h1>
<!-- existing content -->
{% endblock %}
```

---

### `templates/reports_partial.html` (MODIFY CSS tokens only — partial, NO extends)

**Analog:** itself — partial fragment, no `<html>/<head>/<body>` wrappers

**This file MUST NOT extend base.html.** It is included via `{% include %}` inside `org_admin.html` and `admin.html`, which already extend `base.html`. Adding `{% extends %}` to a partial causes Jinja2 errors.

**What to change:**
1. Remove all CSS classes that are now in `base.html` shared CSS: `.nav-tabs`, `.tab`, `.logo`, `.logo-icon`, `.header-right`, `.user-badge`, `.btn-logout`, `.stat-card`, `.stat-label`, `.stat-val`, `.table-card`, `table`, `thead`, `th`, `td`, `.badge*`, `.hidden`, `.toolbar`, `.page`
2. Keep only reports-specific CSS: `.chart-card`, `.chart-title`, `.monthly-table`, `.emp-cell`, `.emp-av`, `.time-cell`, `.row-late`, `.row-early-leave`, `.btn-export`, `.search-input`
3. Remove the `.nav-tabs` HTML block at line 58 — the sidebar replaces it
4. Keep the `<script src="chart.js CDN">` tag — it's page-specific
5. Update remaining color values:
   - `.btn-export { background: #1565C0 }` → `background: var(--accent)`
   - `.btn-export:hover { background: #0d47a1 }` → `background: var(--accent-hover)`
   - `input:focus { border-color: #1565C0 }` → `border-color: var(--accent)`
   - `.stat-val.blue` → `.stat-val.teal` (or keep `.blue` as alias)
   - `.logo-icon { background: #1565C0 }` — REMOVE (logo moves to sidebar in base.html)

**Current nav-tabs HTML to remove** (reports_partial.html line 58+):
```html
<!-- REMOVE this entire block: -->
<div class="nav-tabs" id="reportsNavTabs">
  <span class="tab active" id="rTabJournal" onclick="rSwitchTab('journal')">...</span>
  ...
</div>
```

---

### `templates/timesheet_partial.html` (MODIFY CSS tokens only — partial, NO extends)

**Analog:** `templates/timesheet.html` (same grid structure)

Same rule as `reports_partial.html` — partial, no extends. Update CSS tokens only. Remove any `.nav-tabs` blocks. Replace `#1565C0` with `var(--accent)`.

---

## Shared Patterns

### CSS Reset + Font Stack
**Source:** `templates/superadmin.html` lines 8–9 (to be moved to base.html)
**Apply to:** `base.html` ONLY — children do not repeat this
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; background: var(--content-bg); color: var(--text-primary); min-height: 100vh; }
```

### Old Blue Color Removal (global find-replace)
**Source:** `templates/superadmin.html` line 19, 37–38; `templates/admin.html` line 26, 28–29 (current values)
**Apply to:** Every template being converted
```
#1565C0       → var(--accent)         /* primary buttons, borders, logo-icon bg */
#0d47a1       → var(--accent-hover)   /* hover states */
rgba(21,101,192,0.07)  → rgba(13,148,136,0.07)  /* card shadows */
rgba(21,101,192,0.1)   → rgba(13,148,136,0.15)  /* focus rings */
.stat-val.blue → .stat-val.teal       /* stat card color modifier */
```
**Verification command (run after all conversions):**
```bash
grep -rn "#1565C0\|#0d47a1" /var/www/sites/face-almgp33/templates/ --include="*.html" | grep -v "kiosk.html\|login.html"
```

### switchTab() JS Adaptation
**Source:** `templates/superadmin.html` lines 200–205
**Apply to:** `superadmin.html`, `org_admin.html`, `dept_admin.html`, `admin.html`

After redesign, `switchTab()` in each template must drop the `tabX.classList.toggle('active', ...)` lines (those referenced `.tab` elements that are now removed). Keep only the panel `.hidden` toggle lines:
```javascript
// AFTER redesign — keep only panel visibility lines:
function switchTab(tab) {
  document.getElementById('panelOrgs').classList.toggle('hidden', tab !== 'orgs');
  document.getElementById('panelUsers').classList.toggle('hidden', tab !== 'users');
  // etc. for each panel in this template
}
```

### Error/Success Message Pattern
**Source:** `templates/profile.html` lines 27–28
**Apply to:** `profile.html`, `account.html` (form pages with flash messages)
```css
.error   { background: var(--red-bg);   color: var(--red-text);   border: 1px solid #ef9a9a; border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }
.success { background: var(--green-bg); color: var(--green-text); border: 1px solid #a5d6a7; border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }
```

### Jinja2 Session Check Pattern
**Source:** `templates/profile.html` line 35; `templates/403.html` lines 35–39
**Apply to:** `base.html` sidebar footer AND any template that checks role without it being passed as a variable
```html
<!-- Use session.get() not {{ username }} in base.html: -->
{{ session.get('username', '') }}
{{ session.get('role', '') }}
<!-- Use session.role directly in conditionals: -->
{% if session.role == 'superadmin' %}
{% elif session.role in ('dept_admin', 'viewer') %}
{% endif %}
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `templates/base.html` | layout-shell | SSR | Does not exist yet; no existing base template in project. Build from scratch using RESEARCH.md patterns (all patterns in this file are ASSUMED/standard techniques, not codebase analogs). |

---

## Metadata

**Analog search scope:** `/var/www/sites/face-almgp33/templates/` (all 19 template files)
**Files read directly:** `superadmin.html`, `admin.html`, `profile.html`, `403.html`, `reports_partial.html`, `devices.html`
**Pattern extraction date:** 2026-06-25

**Implementation order recommendation:**
1. Create `base.html` with full CSS token block + sidebar + hamburger JS
2. Convert `superadmin.html` as the pilot — verify end-to-end in browser
3. Batch-convert remaining tab-based pages: `org_admin.html`, `dept_admin.html`, `admin.html`
4. Convert single-page templates: `employee.html`, `timesheet.html`, `profile.html`, `account.html`, `audit.html`, `dashboard.html`, `403.html`, `devices.html`
5. Update partials CSS tokens: `reports_partial.html`, `timesheet_partial.html`
6. Run `grep -rn "#1565C0\|#0d47a1" templates/ --include="*.html"` — must return zero hits (excluding kiosk/login)
