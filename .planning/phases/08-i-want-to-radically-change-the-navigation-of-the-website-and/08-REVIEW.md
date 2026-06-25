---
phase: 08-navigation-redesign
reviewed: 2026-06-25T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - templates/403.html
  - templates/account.html
  - templates/admin.html
  - templates/audit.html
  - templates/base.html
  - templates/dashboard.html
  - templates/dept_admin.html
  - templates/devices.html
  - templates/employee.html
  - templates/error_token.html
  - templates/org_admin.html
  - templates/profile.html
  - templates/register.html
  - templates/reports_partial.html
  - templates/superadmin.html
  - templates/timesheet.html
  - templates/timesheet_partial.html
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-06-25
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Reviewed all 17 HTML templates delivered in the navigation redesign phase. The templates collectively implement a sidebar-driven layout via `base.html` extending to role-specific dashboards. Jinja2 auto-escaping covers most template variable rendering safely. However one critical stored-XSS defect exists in `admin.html` where a user-controlled string is interpolated raw into `innerHTML`-assembled HTML. Six warnings span missing error handling, a broken navigation onclick pattern, and misleading error copy. Five info items cover console logging convention violations, dead code, and stale-data caching.

---

## Critical Issues

### CR-01: Stored XSS — unescaped username in `admin.html` `loadUsers()` onclick

**File:** `templates/admin.html:212`

**Issue:** The `loadUsers()` function builds `tbody.innerHTML` from API data. `u.username` is spliced directly into a JavaScript string inside an inline `onclick` attribute with no HTML-escaping applied:

```javascript
const actionBtn = u.active
  ? `<button onclick="deactivateUser('${u.id}', '${u.username}')" ...>Деактивировать</button>`
  : `<button onclick="reactivateUser('${u.id}')" ...>Активировать</button>`;
```

`escapeHtml()` is defined on the same page and is correctly applied to `u.username` in the table cell (`${escapeHtml(u.username)}`), but is omitted from the `onclick` construction. A username such as `x</button><img src=x onerror=alert(document.cookie)>` would be parsed as raw HTML by the browser, injecting an `<img>` whose `onerror` handler fires immediately on render — no user click required. This is stored XSS: the payload is persisted server-side and executes in any superadmin's browser when the users panel is loaded.

Note: `admin.html` is not linked in the new navigation sidebar (base.html), but the template exists and its route may still be active.

**Fix:** Use `data-*` attributes (the safe pattern already used in `reports_partial.html` line 216 and `org_admin.html` lines 910-914):

```javascript
const actionBtn = u.active
  ? `<button data-uid="${escapeHtml(u.id)}" data-name="${escapeHtml(u.username)}"
       onclick="deactivateUser(this.dataset.uid, this.dataset.name)"
       style="...">Деактивировать</button>`
  : `<button data-uid="${escapeHtml(u.id)}"
       onclick="reactivateUser(this.dataset.uid)"
       class="btn-export" style="...">Активировать</button>`;
```

---

## Warnings

### WR-01: Navigation `switchTab()` called without path guard on several sidebar links

**File:** `templates/base.html:157-158, 174, 177-185`

**Issue:** Multiple sidebar nav items for `superadmin` and `org_admin` roles call `switchTab(tab)` unconditionally and rely on `return false` to prevent page navigation:

```html
<a href="/superadmin" class="nav-item" onclick="switchTab('users');return false;">
```

On any page other than the one that defines `switchTab` (e.g., `/audit`, `/account`), the call throws a `ReferenceError`. Because the exception bubbles before `return false` runs, the browser follows the `href` and navigates anyway — but to the destination page's default tab, not the intended one. Clicking "Пользователи" from `/audit` lands on the Organizations panel instead of Users. One nav item already uses the correct guard pattern (`onclick="if(window.location.pathname==='/superadmin'){switchTab('orgs');return false;}"`); the others do not.

**Fix:** Apply the same path guard to all tab-switch nav items:

```html
<a href="/superadmin" class="nav-item"
   onclick="if(window.location.pathname==='/superadmin'){switchTab('users');return false;}">
```

---

### WR-02: `admin.html` API calls lack error handling

**File:** `templates/admin.html:265-274, 286-303, 375-428`

**Issue:** Three async functions — `loadDates()`, `loadData()`, and `loadStats()` — have no `try/catch` blocks and do not check `resp.ok` before calling `await resp.json()`. If the server returns a non-2xx response or the network fails, an unhandled exception propagates silently. `loadData()` also sets `currentData = rows` before knowing whether `rows` is a valid array, meaning a subsequent `filterTable()` call on malformed data could throw.

```javascript
async function loadDates() {
  const resp = await fetch("/api/attendance/dates");  // no .ok check
  const dates = await resp.json();                    // throws on error body
  // ...
}
```

**Fix:** Wrap each function in `try/catch` and guard with `if (!resp.ok) { ... return; }` before parsing the body:

```javascript
async function loadDates() {
  try {
    const resp = await fetch("/api/attendance/dates");
    if (!resp.ok) return;
    const dates = await resp.json();
    // ...
  } catch (e) {
    // show user-visible error
  }
}
```

---

### WR-03: `superadmin.html` `loadUsers()` has an empty catch block

**File:** `templates/superadmin.html:347`

**Issue:** The `loadUsers()` function has `catch(e) {}` — a completely empty catch. All exceptions are swallowed silently. The users table remains showing "Загрузка..." indefinitely with no error message, no log, and no user feedback:

```javascript
async function loadUsers() {
  try {
    const resp = await fetch('/api/users');
    allUsers = resp.ok ? await resp.json() : [];
    renderUsers();
  } catch(e) {}   // <-- swallows everything
}
```

**Fix:**
```javascript
  } catch(e) {
    document.getElementById('usersTableBody').innerHTML =
      '<tr><td colspan="5" style="text-align:center;color:#c62828;padding:28px;">Ошибка загрузки пользователей.</td></tr>';
  }
```

---

### WR-04: Misleading "save error" message shown on data-load failures

**Files:** `templates/dept_admin.html:151`, `templates/org_admin.html:439, 575`

**Issue:** Three `catch` blocks copy-pasted from save-operation handlers display "Ошибка при сохранении. Попробуйте ещё раз." when the operation that failed was a *read*, not a write. This confuses users into thinking they performed an action that failed:

- `dept_admin.html:147-153` — `loadAttendance()` catch
- `org_admin.html:436-441` — `loadDepts()` catch
- `org_admin.html:572-576` — `loadEmployees()` catch

**Fix:** Change the error text to reflect the actual operation:

```javascript
// dept_admin.html
'<tr><td colspan="5" class="empty-state">Ошибка загрузки посещаемости. Попробуйте ещё раз.</td></tr>'

// org_admin.html loadDepts
'<tr><td colspan="4" ...>Ошибка загрузки отделов. Попробуйте ещё раз.</td></tr>'

// org_admin.html loadEmployees
'<tr><td colspan="7" ...>Ошибка загрузки сотрудников. Попробуйте ещё раз.</td></tr>'
```

---

### WR-05: `register.html` `deleteEmployee()` has no error handling

**File:** `templates/register.html:416-420`

**Issue:** `deleteEmployee()` issues a DELETE request and unconditionally refreshes the employee list, with no `try/catch`, no `resp.ok` check, and no user feedback on failure:

```javascript
async function deleteEmployee(id) {
  if (!confirm("Удалить сотрудника и все его данные?")) return;
  await fetch("/api/employees/" + id, { method: "DELETE" });
  loadEmployees();  // called even if DELETE returned 403 or 500
}
```

A failed deletion is silently ignored. The employee appears to still be listed (nothing deleted), but the user receives no explanation.

**Fix:**
```javascript
async function deleteEmployee(id) {
  if (!confirm("Удалить сотрудника и все его данные?")) return;
  try {
    const resp = await fetch("/api/employees/" + id, { method: "DELETE" });
    if (!resp.ok) {
      const d = await resp.json().catch(() => ({}));
      showToast("addToast", d.error || "Ошибка при удалении", "error");
      return;
    }
    loadEmployees();
  } catch (e) {
    showToast("addToast", "Ошибка соединения", "error");
  }
}
```

---

### WR-06: New org creation — PIN PATCH failure is silently discarded

**File:** `templates/superadmin.html:292-308`

**Issue:** In `saveOrg()`, when creating a new organisation with a PIN, the flow reads the POST response body to get `created.id` and then fires a second PATCH request to set the PIN. The PATCH is not error-checked and its result is never surfaced to the user. If the PIN PATCH fails (network error, validation failure), the organisation is created but the PIN is silently lost with no indication:

```javascript
if (resp.ok && pinRaw) {
  const created = await resp.json();       // consumes POST body
  await fetch(`/api/orgs/${created.id}/settings`, {   // PATCH — result ignored
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({kiosk_pin: pinRaw}),
  });
}
if (resp.ok) {              // checks POST resp, not PATCH
  cancelForm();
  await loadOrgs();
  await loadStats();
}
```

**Fix:** Check the PATCH response and surface any error:

```javascript
if (resp.ok && pinRaw) {
  const created = await resp.json();
  const pinResp = await fetch(`/api/orgs/${created.id}/settings`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({kiosk_pin: pinRaw}),
  });
  if (!pinResp.ok) {
    const d = await pinResp.json().catch(() => ({}));
    errEl.textContent = d.error || 'Организация создана, но PIN не сохранён.';
    errEl.classList.remove('hidden');
    await loadOrgs();
    return;
  }
}
```

---

## Info

### IN-01: `console.error` calls in production code violate project conventions

**Files:** `templates/register.html:183`, `templates/reports_partial.html:226, 287, 325, 459`

**Issue:** CLAUDE.md states "No console logging in production code." Five `console.error` calls remain:
- `register.html:183` — in `startCamera()` catch
- `reports_partial.html:226` — in `rLoadUsers()` catch
- `reports_partial.html:287` — in `rLoadDates()` catch
- `reports_partial.html:325` — in `rLoadData()` catch
- `reports_partial.html:459` — in `rLoadStats()` catch

**Fix:** Remove all `console.error` calls. Errors are already surfaced to users via table cell error messages; the console calls add no production value.

---

### IN-02: Dead code — `reassignEmployee()` in `org_admin.html` is never called

**File:** `templates/org_admin.html:771-790`

**Issue:** The `reassignEmployee()` function is defined but has no callers anywhere in the template. It appears to be a leftover from an earlier implementation of the employees tab that was superseded by `saveEmployeeEdit()`.

**Fix:** Remove the function (lines 771-790).

---

### IN-03: Inline panel cache never invalidated — stale data on tab re-visit

**Files:** `templates/org_admin.html:1132-1165`, `templates/dept_admin.html:89-113`

**Issue:** `loadInlinePanel()` (org_admin) and `loadTimesheetPanel()` (dept_admin) both set a boolean flag after the first successful load and return immediately on subsequent calls:

```javascript
if (_inlinePanelLoaded[tab]) return;  // never re-fetches
```

If a user adds an employee or attendance is recorded after the panel is first loaded, navigating away and back to the Reports or Timesheet tab shows stale data for the rest of the page session. There is no way to force a refresh short of a full page reload.

**Fix:** Either remove the flag (always re-fetch) or add an explicit "Обновить" button that clears the flag and calls `loadInlinePanel(tab)` again.

---

### IN-04: Duplicate password-change templates

**Files:** `templates/profile.html`, `templates/account.html`

**Issue:** Both templates implement identical password-change functionality. `profile.html` uses an HTML form POST to an unlinked route; `account.html` uses a PATCH API call. The new `base.html` navigation links only to `/account`. `profile.html` is an orphaned legacy template. If the `/profile` route remains active in `app.py`, users who discover it would get a different UX (and potentially different validation behaviour) from the canonical `/account` page.

**Fix:** Confirm whether the `/profile` route still exists in `app.py`. If so, either remove it (redirect to `/account`) or consolidate both into a single template. Remove `profile.html` once the route is retired.

---

### IN-05: `org_token` duplicated in Jinja2 inline onclick attributes in `devices.html`

**File:** `templates/devices.html:62-64`

**Issue:** The Jinja2 template renders `{{ org_token }}` directly inside `onclick` attributes on the Save and Revoke buttons (lines 62-64), while the same value is already stored in a JavaScript constant on line 82:

```javascript
const ORG_TOKEN = "{{ org_token }}";
```

```html
<button onclick="saveRename('{{ d.id }}', '{{ org_token }}')" ...>
<button onclick="revokeDevice('{{ d.id }}', '{{ org_token }}')">
```

This duplication means the token is emitted three times per device card. The onclick handlers could reference `ORG_TOKEN` instead, reducing template coupling and making the intent clearer.

**Fix:**
```html
<button onclick="saveRename('{{ d.id }}', ORG_TOKEN)" ...>Сохранить</button>
<button onclick="revokeDevice('{{ d.id }}', ORG_TOKEN)">Отозвать</button>
```

---

_Reviewed: 2026-06-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
