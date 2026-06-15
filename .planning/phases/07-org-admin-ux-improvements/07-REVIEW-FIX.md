---
phase: 07-org-admin-ux-improvements
fixed_at: 2026-06-15T10:30:00Z
review_path: .planning/phases/07-org-admin-ux-improvements/07-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-06-15T10:30:00Z
**Source review:** .planning/phases/07-org-admin-ux-improvements/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (CR-01, CR-02, CR-03, WR-01, WR-02, WR-03, WR-04, WR-05, WR-06)
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: Unescaped `u.username` injected into onclick attribute (stored XSS)

**Files modified:** `templates/reports_partial.html`
**Commit:** 456a9d6
**Applied fix:** Replaced direct interpolation of `u.id` and `u.username` into onclick attributes with `data-uid` and `data-name` HTML attributes escaped via `rEscapeHtml`, and updated the onclick handlers to read `this.dataset.uid` / `this.dataset.name`. Applied to both the Деактивировать and Активировать buttons.

---

### CR-02: Unescaped `emp.id` and `u.id` embedded in onclick attributes (potential XSS)

**Files modified:** `templates/org_admin.html`
**Commit:** 227fde3
**Applied fix:** Replaced all direct ID interpolations in onclick attributes across dept table (startEditDept, deleteDept), employees table (resetFace, reassignEmployee, startEditEmp), and users table (toggleUser) with `data-id`/`data-name`/`data-active` attributes read via `this.dataset`. The `escapeHtml()` function is now applied to all attribute values.

---

### CR-03: `rLoadDates`, `rLoadData`, and `rLoadStats` have no error handling

**Files modified:** `templates/reports_partial.html`
**Commit:** 5656a2a
**Applied fix:** Wrapped all three fetch functions in `try/catch` blocks and added `resp.ok` guards. Added `Array.isArray()` guards for `rLoadDates` and `rLoadData`. All failure paths now show user-facing error messages in the respective table bodies instead of leaving the UI frozen or throwing unhandled promise rejections.

---

### WR-01: `toggleUser` silently ignores API errors

**Files modified:** `templates/org_admin.html`
**Commit:** 6e9727b
**Applied fix:** Wrapped the PATCH fetch in `try/catch`, added `resp.ok` check that reads the error body and shows an `alert()`, and added a network-failure alert in the catch block. `loadOrgUsers()` is still called after the try/catch so the list always refreshes to the actual server state.

---

### WR-02: Late/early-leave thresholds hardcoded to 09:00 / 18:00

**Files modified:** `templates/reports_partial.html`, `app.py`
**Commit:** 3389188
**Applied fix:** Added `schedule_start` and `schedule_end` fields to the `/api/attendance` JSON response (formatted as `HH:MM:SS` to match check_in/check_out format). Updated `rRenderTable` and `rExportCSV` in the template to compare `r.check_in > r.schedule_start` and `r.check_out < r.schedule_end` instead of hardcoded strings. Default values of `"09:00:00"` and `"18:00:00"` are used server-side when no schedule row exists, preserving backward compatibility.

---

### WR-03: `rInitials` crashes with empty segments from double/leading spaces

**Files modified:** `templates/reports_partial.html`
**Commit:** daf089d
**Applied fix:** Added `.filter(w => w.length > 0)` after `split(' ')` to discard empty strings, and added a `(name || '')` null guard. The function now correctly handles leading spaces, trailing spaces, and double spaces without producing `"undefined"` in avatar initials.

---

### WR-04: Duplicate event listeners accumulate on each `tsSubmitForm` call

**Files modified:** `templates/timesheet_partial.html`
**Commit:** b3a007b
**Applied fix:** Added `window._tsListenersRegistered` and `window._tsEditableKeyRegistered` guard flags around all three `document.addEventListener` calls (click handler for dropdown close, Escape keydown for dropdown close, Enter/Space keydown for editable cells). On subsequent script re-executions the `if (!window._tsXxx)` check prevents re-registration, so each handler fires exactly once per interaction regardless of how many times the timesheet form is submitted.

---

### WR-05: `rLoadUsers` skips error handling on failed fetch

**Files modified:** `templates/reports_partial.html`
**Commit:** 3a903e8
**Applied fix:** Wrapped the entire function body in a `try/catch`, upgraded the `if (!resp.ok) return` to show a user-facing error message in the table body, and added a `console.error` + error-row display in the catch block for network failures.

---

### WR-06: `sortEmployees` comparator reads undefined `av`/`bv` for unexpected key values

**Files modified:** `templates/org_admin.html`
**Commit:** 278ae4c
**Applied fix:** Changed `let av, bv;` to `let av = '', bv = '';` so that any unrecognized sort key produces stable ordering (all elements equal) rather than `undefined < undefined` comparisons that leave the array unsorted.

---

## Skipped Issues

None — all in-scope findings were successfully fixed.

---

_Fixed: 2026-06-15T10:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
