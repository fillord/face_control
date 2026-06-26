---
phase: quick-260626-dfl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app.py
  - templates/org_admin.html
  - templates/superadmin.html
  - templates/dept_admin.html
  - templates/base.html
autonomous: false
requirements: [NAV-DIRECT-URL]
must_haves:
  truths:
    - "Each sidebar tab is reachable at its own direct URL (e.g. /org_admin/employees, /org_admin/reports, /superadmin/users, /dept_admin/employees)"
    - "Visiting a per-tab URL directly (fresh load / bookmark / refresh) opens that exact tab"
    - "The sidebar nav item for the current tab URL is highlighted as active"
    - "Existing default hub URLs (/org_admin, /superadmin, /dept_admin) still work and open their default tab"
  artifacts:
    - path: "app.py"
      provides: "Per-tab routes /org_admin/<tab>, /superadmin/<tab>, /dept_admin/<tab> with validated initial_tab"
    - path: "templates/base.html"
      provides: "Sidebar links pointing to real per-tab URLs with path-based active highlighting"
  key_links:
    - from: "templates/base.html nav-item href"
      to: "app.py per-tab route"
      via: "direct GET navigation to /<hub>/<tab>"
    - from: "app.py initial_tab"
      to: "hub template switchTab(initial_tab) on load"
      via: "Jinja-injected initial_tab variable"
---

<objective>
Give every in-page tab its own direct, bookmarkable URL — matching how /register and /account already work as standalone URLs.

Today the three "hub" pages render all tabs in one template and switch between them client-side:
- /org_admin — tabs: depts (default), employees, summary, reports, users, settings, timesheet
- /superadmin — tabs: orgs (default), users
- /dept_admin — tabs: attendance (default), employees, timesheet

The sidebar links to these tabs via an onclick `navSwitchTab(page, tab)` handler, so a tab is not addressable by URL (you can only reach it via a `#hash`). This plan adds real per-tab routes and rewires the sidebar so each tab has a clean URL like `/org_admin/reports`.

Approach decision: rather than physically duplicating each hub's tightly-coupled `<script>` (shared global state like `allDepts`/`allEmployees`, shared CRUD functions) into separate files — which would be a large, fragile copy job — we make each tab a real server route that renders the existing hub template with an injected `initial_tab`. The page opens that tab on load via its existing `switchTab()`. This delivers the user-facing outcome (direct URLs per tab, bookmarkable, refresh-safe, active-highlighted) with minimal risk and no JS duplication.

Purpose: Direct/bookmarkable URLs per tab; correct active highlighting on refresh.
Output: New per-tab Flask routes + rewired sidebar nav.
</objective>

<execution_context>
@/var/www/sites/face-almgp33/.claude/gsd-core/workflows/execute-plan.md
@/var/www/sites/face-almgp33/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app.py
@templates/base.html
@templates/org_admin.html
@templates/superadmin.html
@templates/dept_admin.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add per-tab routes that inject initial_tab</name>
  <files>app.py</files>
  <action>
Add a second route decorator with a `<tab>` segment to each of the three hub view functions and pass a validated `initial_tab` into the existing render_template call. Do NOT create new view functions — extend the existing ones.

For `org_admin_page` (currently `@app.route("/org_admin")` at line ~1004): add `@app.route("/org_admin/<tab>")` above the existing decorator and change the signature to `def org_admin_page(tab="depts"):`. At the top of the body define `VALID_TABS = {"depts","employees","summary","reports","users","settings","timesheet"}` and `initial_tab = tab if tab in VALID_TABS else "depts"`. Add `initial_tab=initial_tab` to the existing `render_template("org_admin.html", ...)` kwargs.

For `superadmin_page` (line ~995): add `@app.route("/superadmin/<tab>")`, signature `def superadmin_page(tab="orgs"):`, `VALID_TABS = {"orgs","users"}`, `initial_tab = tab if tab in VALID_TABS else "orgs"`, and pass `initial_tab=initial_tab` to `render_template("superadmin.html", ...)`.

For `dept_admin_page` (line ~1078): add `@app.route("/dept_admin/<tab>")`, signature `def dept_admin_page(tab="attendance"):`, `VALID_TABS = {"attendance","employees","timesheet"}`, `initial_tab = tab if tab in VALID_TABS else "attendance"`, and pass `initial_tab=initial_tab` to `render_template("dept_admin.html", ...)`.

Invalid tab values fall back to the default tab (render normally) — do NOT call abort/404 (no 404 template exists). The single-segment `<tab>` rule will not shadow existing two-segment static routes like `/org_admin/partial/reports` or `/dept_admin/partial/timesheet` (different segment count, and static rules win), but keep the validation allowlist regardless. The `@require_role(...)` decorators must remain unchanged and stay closest to the function (below the new route decorator).
  </action>
  <verify>
    <automated>cd /var/www/sites/face-almgp33 && venv/bin/python -c "import app; rules=sorted(r.rule for r in app.app.url_map.iter_rules() if '<tab>' in r.rule); print(rules); assert '/org_admin/<tab>' in rules and '/superadmin/<tab>' in rules and '/dept_admin/<tab>' in rules"</automated>
  </verify>
  <done>Module imports without error; url_map contains /org_admin/<tab>, /superadmin/<tab>, /dept_admin/<tab>; default hub routes still present.</done>
</task>

<task type="auto">
  <name>Task 2: Make hub templates open initial_tab on load</name>
  <files>templates/org_admin.html, templates/superadmin.html, templates/dept_admin.html</files>
  <action>
Each hub template ends with a tab-restore IIFE that reads `window.location.hash`. Update it to prefer the server-injected `initial_tab`, falling back to the hash for backward compatibility.

In `templates/org_admin.html` (IIFE near line ~1182) and `templates/superadmin.html` (near line ~446) and `templates/dept_admin.html` (near line ~336), change the line `var h = window.location.hash.slice(1);` to `var h = {{ initial_tab|default('')|tojson }} || window.location.hash.slice(1);`. Leave the rest of the IIFE (`if (h) { switchTab(h); history.replaceState(...); }`) intact.

Note: org_admin.html already calls `init()` before the IIFE and superadmin/dept_admin call their own init in their IIFE/load path — do not reorder; only change the `var h = ...` source line. The `|tojson` filter safely emits a quoted JS string (or `""` when initial_tab is absent, e.g. when this template is somehow rendered without the var).
  </action>
  <verify>
    <automated>cd /var/www/sites/face-almgp33 && grep -c "initial_tab|default" templates/org_admin.html templates/superadmin.html templates/dept_admin.html | grep -v ':0'</automated>
  </verify>
  <done>All three hub templates source the restore tab from `initial_tab` first, then hash; grep shows the new expression present in each file.</done>
</task>

<task type="auto">
  <name>Task 3: Rewire sidebar links to direct per-tab URLs</name>
  <files>templates/base.html</files>
  <action>
In `templates/base.html` sidebar nav (lines ~154-222), replace the `onclick="return navSwitchTab('/page','tab')"` handlers with real `href` URLs and path-based active highlighting. Keep `navSwitchTab` defined in the script (harmless) but stop using it on these links.

Superadmin block: "Организации" → `href="/superadmin"` active when `request.path in ['/superadmin','/superadmin/orgs']`; "Пользователи" → `href="/superadmin/users"` active when `request.path == '/superadmin/users'`. Remove their onclick attributes.

Org_admin block: "Отделы" → `href="/org_admin"` active when `request.path in ['/org_admin','/org_admin/depts']`; "Сотрудники" → `/org_admin/employees`; "Сводка" → `/org_admin/summary`; "Отчёты" → `/org_admin/reports`; "Пользователи" → `/org_admin/users`; "Настройки" → `/org_admin/settings`. Each non-default item gets `{% if request.path == '/org_admin/<tab>' %}active{% endif %}` and its onclick removed.

Dept_admin/viewer block: "Посещаемость" → `href="/dept_admin"` active when `request.path in ['/dept_admin','/dept_admin/attendance']`; "Сотрудники" → `/dept_admin/employees` active when `request.path == '/dept_admin/employees'`. Remove onclicks.

Leave the already-standalone links (/register, /audit, /timesheet, /account, /employee) untouched. After editing, restart the process so changes load: `pm2 restart face-recognition`.
  </action>
  <verify>
    <automated>cd /var/www/sites/face-almgp33 && test "$(grep -c 'navSwitchTab(' templates/base.html)" -le 2 && grep -q 'href="/org_admin/employees"' templates/base.html && grep -q 'href="/superadmin/users"' templates/base.html && grep -q 'href="/dept_admin/employees"' templates/base.html && echo OK</automated>
  </verify>
  <done>Sidebar tab links use direct /hub/tab hrefs (no remaining navSwitchTab onclick on nav-items; only its definition + JS-internal references remain); pm2 process restarted.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Per-tab direct URLs for all hub pages, wired into the sidebar with active highlighting.</what-built>
  <how-to-verify>
    1. Log in as an org_admin. In the sidebar click "Отчёты" — the URL bar should read `/org_admin/reports` and the Reports tab should be shown with "Отчёты" highlighted.
    2. Refresh the page (F5) — it should stay on the Reports tab (not reset to Departments).
    3. Paste `/org_admin/employees` directly into the address bar — the Employees tab should open.
    4. Repeat a spot-check as superadmin (`/superadmin/users`) and as dept_admin (`/dept_admin/employees`).
    5. Confirm /register, /account, /timesheet still load normally.
  </how-to-verify>
  <resume-signal>Type "approved" or describe any tab/URL that did not load correctly.</resume-signal>
</task>

</tasks>

<verification>
- `venv/bin/python -c "import app"` imports cleanly (no syntax/route errors).
- url_map exposes /org_admin/<tab>, /superadmin/<tab>, /dept_admin/<tab>.
- Sidebar nav-items use direct hrefs; active highlight keys off request.path.
- pm2 process `face-recognition` is online after restart.
</verification>

<success_criteria>
- Every hub tab has a direct URL that opens that tab on fresh load/refresh/bookmark.
- Active sidebar highlight matches the current tab URL.
- Default hub URLs and existing standalone pages remain functional.
</success_criteria>

<output>
Create `.planning/quick/260626-dfl-make-separate-page-files-for-each-tab-wi/260626-dfl-SUMMARY.md` when done.
</output>
