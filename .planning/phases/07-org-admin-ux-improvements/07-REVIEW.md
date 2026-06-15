---
phase: 07-org-admin-ux-improvements
reviewed: 2026-06-15T10:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - templates/org_admin.html
  - templates/reports_partial.html
  - templates/timesheet_partial.html
findings:
  critical: 3
  warning: 6
  info: 3
  total: 12
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-06-15T10:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three template files were reviewed: the main org-admin shell (`org_admin.html`), the reports partial injected into it (`reports_partial.html`), and the T-13 timesheet partial (`timesheet_partial.html`). The partials are fetched and injected via `innerHTML` + script-tag re-execution, which is a legitimate pattern for this stack.

Critical issues are concentrated in two areas: (1) unescaped user-controlled strings embedded directly in `onclick` attributes across all three files, enabling stored-XSS if any ID or username contains a quote or parenthesis; (2) several `async` fetch calls have no `try/catch` and no `resp.ok` check, meaning a network error or a 4xx/5xx response silently crashes the function and leaves the UI in an undefined state.

---

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Unescaped `u.username` injected into onclick attribute (stored XSS)

**File:** `templates/reports_partial.html:251`
**Issue:** The `rDeactivateUser` button is built with a template literal that splices `u.username` directly into an HTML `onclick` attribute:
```js
`<button onclick="rDeactivateUser('${u.id}', '${u.username}')" ...>`
```
`u.username` is a stored string from the database. If an org_admin creates a username containing a single-quote, for example `O'Brien`, the generated HTML breaks the attribute and may execute arbitrary JS. A deliberately crafted username such as `x');alert(1);//` results in full script injection. `rEscapeHtml` is applied to the table cell display value (line 254) but not to the onclick string.

**Fix:** Pass the ID only via the attribute and look up the username from the already-rendered DOM, or encode the value:
```js
// Option A: use a data-attribute and look up in the function
`<button data-uid="${rEscapeHtml(u.id)}" data-name="${rEscapeHtml(u.username)}"
  onclick="rDeactivateUser(this.dataset.uid, this.dataset.name)" ...>`

// Option B: JSON-encode the argument (safe against quote injection)
`<button onclick="rDeactivateUser(${JSON.stringify(u.id)}, ${JSON.stringify(u.username)})" ...>`
```

---

### CR-02: Unescaped `emp.id` and `u.id` embedded in onclick attributes (potential XSS if IDs are not strictly UUID)

**File:** `templates/org_admin.html:471-472, 611, 624, 865-866`
**Issue:** Multiple `innerHTML`-built button elements embed ID values directly into onclick strings without escaping:
```js
`<button onclick="startEditDept('${dept.id}')">…`
`<button onclick="deleteDept('${dept.id}', '${escapeHtml(dept.name)}')">…`
`<button onclick="resetFace('${emp.id}')">…`
`<button onclick="startEditEmp('${emp.id}')">…`
`<button onclick="toggleUser('${u.id}', false)">…`
```
The models store IDs as `String(36)`, and the current migration generates UUIDs (safe). However, the format is not enforced at the application layer; if an import or a future code path writes a non-UUID string containing `'` or `)`, every affected button becomes an XSS vector. The pattern is fragile. `escapeHtml()` is called on `dept.name` (line 472) but **not** on any ID.

**Fix:** Use `data-*` attributes for all values injected from server data, and read them in the event handler:
```js
// Example for dept table
`<button class="btn-edit" data-id="${escapeHtml(dept.id)}"
  onclick="startEditDept(this.dataset.id)">Изменить</button>`
```

---

### CR-03: `rLoadDates`, `rLoadData`, and `rLoadStats` have no error handling — uncaught exceptions crash silently

**File:** `templates/reports_partial.html:304-313, 325-342, 413-464`
**Issue:** All three functions `await fetch(...)` and immediately call `.json()` on the response with no `try/catch` and no `resp.ok` guard. If the server returns a 4xx/5xx, `.json()` may succeed but the payload will be `{"error": "..."}` rather than the expected array/object, causing a `TypeError` when the code iterates `rows.forEach(...)` or accesses `data.daily_counts.map(...)`. A network failure throws an unhandled promise rejection that leaves the table frozen on "Загрузка...".

```js
// rLoadDates (line 304): no try/catch, no resp.ok check
async function rLoadDates() {
  const resp = await fetch("/api/attendance/dates");
  const dates = await resp.json();   // crashes on non-array error response
  ...
}

// rLoadData (line 325): same pattern
async function rLoadData(dateStr) {
  const resp = await fetch("/api/attendance?date=" + dateStr);
  const rows = await resp.json();   // rows.forEach(...) crashes if rows is {error:...}
  ...
}
```

**Fix:**
```js
async function rLoadDates() {
  try {
    const resp = await fetch("/api/attendance/dates");
    if (!resp.ok) return;
    const dates = await resp.json();
    if (!Array.isArray(dates)) return;
    // ... populate select
  } catch (e) {
    console.error("rLoadDates failed", e);
  }
}
```
Apply the same pattern to `rLoadData` and `rLoadStats`.

---

## Warnings

### WR-01: `toggleUser` silently ignores API errors

**File:** `templates/org_admin.html:919-922`
**Issue:** `toggleUser` fires-and-forgets the PATCH request with no error handling. If the server returns an error (e.g., the user is the last active org_admin and the server rejects the deactivation), `loadOrgUsers()` is called anyway and re-renders from the unchanged server state — giving the appearance of success to the user for a moment before snapping back. More importantly, a network failure throws an uncaught promise rejection.

```js
async function toggleUser(userId, active) {
  await fetch(`/api/users/${userId}`, {...});  // no resp.ok check, no try/catch
  await loadOrgUsers();
}
```

**Fix:**
```js
async function toggleUser(userId, active) {
  try {
    const resp = await fetch(`/api/users/${userId}`, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({active}),
    });
    if (!resp.ok) {
      const data = await resp.json();
      alert(data.error || 'Ошибка при изменении статуса.');
    }
  } catch (e) {
    alert('Ошибка соединения.');
  }
  await loadOrgUsers();
}
```

---

### WR-02: Late/early-leave thresholds are hardcoded to 09:00 / 18:00, ignoring per-employee schedules

**File:** `templates/reports_partial.html:363-364, 398-399`
**Issue:** The journal view marks a check-in as "late" if it is after `"09:00:00"` and a check-out as "early leave" if before `"18:00:00"` — global constants baked into the client-side rendering code. The data model stores per-employee schedules (`start_time`, `end_time` in `EmployeeSchedule`). If an employee's schedule is 07:00–16:00, every attendance record from 08:00 will be incorrectly flagged as "on time", and a 15:50 check-out will be shown as "ранний уход" despite being correct.

The same literals also appear in the CSV export (lines 398-399), so the exported data will contain incorrect "Опоздание" and "Ранний уход" columns.

**Fix:** The `/api/attendance` endpoint should include the employee's `schedule_start` and `schedule_end` in each attendance row, and the client should compare against those values:
```js
const isLate       = r.check_in  && r.schedule_start && r.check_in  > r.schedule_start;
const isEarlyLeave = r.check_out && r.schedule_end   && r.check_out < r.schedule_end;
```

---

### WR-03: `rInitials` crashes with `TypeError` when an employee name contains an empty segment

**File:** `templates/reports_partial.html:191`
**Issue:**
```js
function rInitials(name) {
  return name.split(" ").slice(0,2).map(w => w[0]).join("").toUpperCase();
}
```
If `name` contains leading/trailing/double spaces (e.g., `"John  Doe"` or `" Smith"`), `split(" ")` produces empty strings. `w[0]` on an empty string is `undefined`, and `undefined.toUpperCase()` is not called (`.join("")` handles `undefined` by converting to `"undefined"`) — but `"undefined".toUpperCase()` would not crash. However `w[0]` on an empty string `""` returns `undefined`, and joining produces the string `"undefined"` in the avatar, corrupting the display. The same utility exists in other templates (`rColorFor` similarly takes the raw name).

**Fix:**
```js
function rInitials(name) {
  return (name || '').split(' ').filter(w => w.length > 0).slice(0, 2)
    .map(w => w[0]).join('').toUpperCase();
}
```

---

### WR-04: `_inlinePanelLoaded` flag prevents timesheet from refreshing after form submit

**File:** `templates/org_admin.html:997-1026`, `templates/timesheet_partial.html:221-249`
**Issue:** `loadInlinePanel` sets `_inlinePanelLoaded['timesheet'] = true` after the first load (org_admin.html line 1026). The timesheet partial contains a form (`ts-selector-form`) that submits via `tsSubmitForm`, which fetches a new partial and replaces `inlineTimesheetContent.innerHTML` directly. This correctly re-renders the grid for a new month/department selection.

However, if the user navigates away from the Timesheet tab and then returns, `switchTab('timesheet')` calls `loadInlinePanel('timesheet')`, which returns early because `_inlinePanelLoaded['timesheet']` is still `true` — restoring the original initial load rather than the most recently selected timesheet view. The tab switch overwrites whatever the form submission had rendered with the initial blank state from the first load (if the initial fetch loaded a "no dept selected" state, the refresh clears the user's form selection).

Actually re-reading more carefully: `loadInlinePanel` does NOT re-fetch when the flag is set, so the content remains as the user last set it via `tsSubmitForm`. The stale state problem is inverted: after the user submits the form and navigates away and back, they see the correct last-rendered content. This is intentional caching. No bug here on re-navigation.

The actual bug: `tsSubmitForm` replaces `inlineTimesheetContent.innerHTML` with the fetched HTML and re-executes scripts, but does **not** reset `_inlinePanelLoaded['timesheet']`. If the initial load returns an error (line 1009) and the flag is never set to `true`, subsequent tab switches will re-try the load — which is correct. But if `tsSubmitForm` succeeds and later `switchTab` is called again, it correctly skips re-fetch because the flag was set on the first successful `loadInlinePanel` call. This is fine.

However: `tsSubmitForm` re-appends a new `<script>` to `document.body` on every submit (lines 235-244 of timesheet_partial.html). Functions from the injected script like `tsSubmitForm`, `tsOpenOverrideDropdown`, `tsApplyOverride`, etc. are **re-declared globally with each form submission**. Since the scripts are not modules, each `document.body.appendChild(newScript)` execution overwrites the previous global definitions. While this appears harmless (they are redeclared identically), the `document.addEventListener('click', ...)` and `document.addEventListener('keydown', ...)` handlers at lines 264 and 273 of `timesheet_partial.html` are **added again** on every form submit without removing the previous ones. After N submissions, N copies of those listeners are active simultaneously.

**Fix:** Use `{ once: false }` is not the issue — the fix is to guard against re-registration, or use a flag, or detach previous listeners. The simplest approach: before re-appending scripts, remove existing duplicate event listeners. Or restructure so the listeners are only registered once in `org_admin.html`.

---

### WR-05: `rLoadUsers` skips error handling on failed fetch

**File:** `templates/reports_partial.html:233-236`
**Issue:**
```js
async function rLoadUsers() {
  const resp = await fetch("/api/users");
  if (!resp.ok) return;   // silently returns, table stays on "Загрузка..."
  const users = await resp.json();
  ...
}
```
There is no `try/catch`. A network failure throws an unhandled promise rejection. The table body is never updated from its initial "Загрузка..." placeholder, giving the user no feedback.

**Fix:** Wrap in `try/catch` and show an error message in the table body on failure.

---

### WR-06: `sortEmployees` comparator reads undefined `av`/`bv` for unexpected key values

**File:** `templates/org_admin.html:933-944`
**Issue:** The sort comparator declares `av` and `bv` with `let` but only assigns them inside `if/else if` branches. If `key` is anything other than `'name'`, `'dept'`, or `'date'`, both `av` and `bv` remain `undefined`. The comparison `undefined < undefined` returns `false`, so all elements are treated as equal — sorting does nothing and is silently incorrect. In the current UI only three keys are reachable, but the comparator is fragile:

```js
let av, bv;
if (key === 'name') { ... }
else if (key === 'dept') { ... }
else if (key === 'date') { ... }
// no else — av/bv remain undefined
if (av < bv) return ...;  // undefined < undefined is false
```

**Fix:** Add a default assignment:
```js
let av = '', bv = '';
```
Or add a final `else` that sets them to `''`.

---

## Info

### IN-01: `document.execCommand('copy')` is deprecated

**File:** `templates/org_admin.html:774`
**Issue:** `document.execCommand('copy')` is deprecated and removed in some modern browser contexts (notably cross-origin iframes). It still works in most desktop browsers for now but is on the path to removal.

**Fix:** Replace with the async Clipboard API:
```js
async function copyUrl(inputId) {
  const el = document.getElementById(inputId);
  try {
    await navigator.clipboard.writeText(el.value);
  } catch {
    el.select();
    document.execCommand('copy'); // fallback
  }
}
```

---

### IN-02: Error message for network failure in `loadDepts` says "Ошибка при сохранении" instead of "Ошибка загрузки"

**File:** `templates/org_admin.html:450-452`
**Issue:** The catch block in `loadDepts` shows "Ошибка при сохранении. Попробуйте ещё раз." which is a save-error message, not a load-error message. The same incorrect phrasing appears in `loadEmployees` (line 587).

**Fix:** Use "Ошибка загрузки. Попробуйте ещё раз." in the catch blocks of read-only fetch functions.

---

### IN-03: `tsEscHtml` utility defined in `timesheet_partial.html` is never called

**File:** `templates/timesheet_partial.html:365-372`
**Issue:** The function `tsEscHtml` is defined (lines 365-372) but not called anywhere in the timesheet partial. The timesheet grid is rendered server-side by Jinja2 (which autoescapes `.html` files), so no client-side HTML escaping is needed for static content. The function is dead code.

**Fix:** Remove the dead function, or if future client-side rendering is planned, document the intent with a comment.

---

_Reviewed: 2026-06-15T10:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
