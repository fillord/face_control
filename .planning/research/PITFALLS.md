# Pitfalls Research

**Domain:** Flask RBAC + Organizational Data Isolation + T-13 Timesheet (brownfield extension)
**Researched:** 2026-06-11
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Role Bypass via Unprotected API Endpoints

**What goes wrong:**
The existing app exposes unauthenticated API endpoints (`GET /api/employees`, `POST /api/employees`, `GET /api/attendance`, `GET /api/stats`). After adding the role system, developers protect the new admin UI pages but forget the API routes. Any user — including unauthenticated requests — can call `/api/employees` and get all employee records across all orgs, or post to `/api/attendance` to inject fake check-ins.

**Why it happens:**
Brownfield code has the anti-pattern baked in: `get_employees()` has no `@login_required`. When adding RBAC, it is easy to focus on the new UI routes and miss the 8-10 existing API routes that have no auth at all. Role decorators get applied to new code; old code stays untouched.

**How to avoid:**
In Phase 1 (auth/RBAC foundation), perform an exhaustive audit of every route in app.py and apply the appropriate role decorator before writing any new code. Add a test that enumerates all routes via `app.url_map` and asserts that each one has an `auth_required` attribute — failing the test if any route is added without explicit auth declaration. The kiosk route `/` and `/api/recognize` are the only intentional exceptions.

**Warning signs:**
- Any `@app.route` that is not also decorated with `@login_required` or a role check
- `curl http://localhost:5051/api/employees` returns data without a session cookie
- New role UI works correctly but raw API calls still return full unfiltered data

**Phase to address:** Phase 1 — RBAC Foundation (before any new feature work)

---

### Pitfall 2: Data Isolation Enforced Only in UI, Not at Query Layer

**What goes wrong:**
A dept_admin sees only their department in the HTML table, but the underlying `GET /api/attendance?date=2026-06-11` still returns attendance for the entire organization. A determined user (or a script) calls the API directly and harvests data for employees outside their scope.

**Why it happens:**
The most natural implementation is: load all data, then filter before passing to the template. This works for UI rendering but leaves the API completely open. The filtering logic lives in the template context, not in the data access layer.

**How to avoid:**
Create a `get_employees_for_user(current_user)` helper that applies org/dept filtering at load time, not render time. Every API endpoint that returns employee or attendance data must call this helper rather than `load_employees()` directly. The filter must check `session["role"]`, `session["org_id"]`, and `session["dept_id"]` server-side. Never trust query parameters like `?org=foo` to scope data — a viewer can change those.

**Warning signs:**
- API returns different count than UI shows for the same user
- Removing the HTML template filter still shows cross-org data in JSON response
- `?dept=other_dept` in the URL changes the response data

**Phase to address:** Phase 1 — RBAC Foundation; must be designed into data helpers before Phase 2 features use them

---

### Pitfall 3: bcrypt Upgrade Locks Out the Existing Admin Account

**What goes wrong:**
The existing `config.json` stores a bcrypt hash under `password_hash`. The new system creates a separate users store (e.g. `users.json`) for the 5-role system. During migration, if the superadmin account is not correctly ported — or if the system looks in the new store and finds nothing — the superadmin is locked out on first deployment. Recovery requires SSH access and manual JSON editing.

**Why it happens:**
The migration script seeds the new users store from the old `config.json` entry, but uses the wrong field name, or forgets to set `role: superadmin`, or the new login route checks `users.json` while the old route still checks `config.json`, creating two parallel auth paths that diverge.

**How to avoid:**
The migration (Phase 1) must: (1) read `config.json`, (2) write the existing bcrypt hash verbatim into the new users store as the superadmin entry — do NOT re-hash, (3) delete the old auth path entirely, (4) set `DEFAULT_SUPERADMIN_SEEDED=true` in config so a re-run does not reset the password. Test login as superadmin immediately after migration with the known password `admin123` before committing any other changes.

**Warning signs:**
- New login route has a `load_config()` call alongside `load_users()` — two auth paths
- `superadmin` not present in `users.json` after first run
- Existing password does not authenticate after deployment

**Phase to address:** Phase 1 — Auth Migration

---

### Pitfall 4: JSON File Race Conditions Under Concurrent Writes

**What goes wrong:**
The existing pattern is: read file → mutate in memory → write file. Under concurrent access (kiosk face check-in + admin saving an employee record simultaneously), two processes read the same file, each mutates their copy, and the last writer wins — silently discarding the first writer's changes. With roles, this worsens: a dept_admin saving employee metadata can overwrite a superadmin's org assignment that was written 50ms earlier.

**Why it happens:**
Python's `json.dump` is not atomic. Two processes can interleave reads and writes because there is no advisory lock. The existing code has no locking at all; adding more writers (5 roles) multiplies the risk.

**How to avoid:**
Wrap every `load_X` / `save_X` pair with a `fcntl.flock` advisory lock (Linux) using a context manager:
```python
import fcntl
from contextlib import contextmanager

@contextmanager
def json_lock(path):
    lock_path = path + ".lock"
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
```
Every save operation must use this. Writes must be atomic: write to a temp file, then `os.replace()` — this is crash-safe on Linux. Do not add SQLite at this milestone; locking is sufficient for clinic scale (< 50 concurrent users).

**Warning signs:**
- Attendance records disappear or get truncated after periods of high kiosk activity
- Employee count drops unexpectedly after multiple simultaneous registrations
- `employees.json` contains partial JSON (truncation mid-write)

**Phase to address:** Phase 1 — Core Infrastructure (before any new write paths are added)

---

### Pitfall 5: Employee Label Integer Integrity Break During Migration

**What goes wrong:**
The existing face recognizer maps employee → integer label (1, 2, 3…). The `train_recognizer()` function looks up `emp.get("label", 0)` from `employees.json`. If the migration script rewrites `employees.json` into a new org/dept structure and does not preserve the `label` integer field exactly, the recognizer will either fail to map labels back to employees (`emp = next(...) → None`) or misidentify employees. This breaks the kiosk — the primary device use case.

**Why it happens:**
Migration scripts transform data structure and often normalize field names. A developer converting `employees.json` to include `org_id` and `dept_id` may accidentally omit `label` or reset it during the transformation. Even a JSON key rename (`label` → `face_label`) breaks recognition.

**How to avoid:**
The migration script must be a pure additive operation: it adds `org_id`, `dept_id`, `schedule` fields to each employee record but does not rename or remove any existing fields — especially `label`, `id`, `face_count`, `name`. Write a post-migration assertion: for every employee with `face_count > 0`, verify `label` is a positive integer and that the recognizer can be trained. Run this check as part of the migration script's output. The kiosk must be tested immediately after migration.

**Warning signs:**
- After migration, `GET /api/recognize` returns `unknown` for employees who were previously recognized
- `train_recognizer()` returns `False` after migration
- Any employee record missing the `label` field

**Phase to address:** Phase 2 — Data Migration

---

### Pitfall 6: T-13 Symbol Logic Silently Wrong for Edge Cases

**What goes wrong:**
The T-13 grid assigns daily symbols per employee. The naive implementation assigns `Я` (worked) if `check_in` exists. This silently produces wrong symbols for: (1) employees who arrived after the late threshold — should show `О` (late) not `Я`; (2) weekends — should show `В` (weekend/day off) not blank; (3) holidays — Kazakhstan has 14 public holidays that must show `П`; (4) partial months in the first/last export — day columns must still align correctly with weekdays. The HR staff signs and submits the T-13 to accounting; wrong symbols cause legal and payroll errors.

**Why it happens:**
Attendance data only stores `check_in` time, not a resolved symbol. Symbol resolution requires combining: attendance record + employee schedule + calendar (weekends + holidays). Developers implement the happy path (check_in → Я) and miss the combinatorial cases. Kazakh public holidays are not in Python's standard library and must be hardcoded or fetched.

**How to avoid:**
Implement a `resolve_symbol(emp_id, date, attendance_record, schedule)` function that is the single source of truth for all symbol resolution. Priority order: (1) if date is a public holiday → `П`; (2) if date is not a working day per employee schedule → `В`; (3) if `check_in` exists and employee was absent for less than the minimum hours → `У` (partial); (4) if `check_in` exists → `Я`; (5) if no check_in and it is a working day → `О` (absent). Hardcode Kazakh public holidays for 2025–2026 as a list of ISO date strings. Write unit tests for every symbol branch before integrating into the export.

**Warning signs:**
- Exported T-13 shows `Я` on a Saturday
- Public holidays show as `О` (absent) instead of `П`
- Late employees show `Я` instead of `О` in the grid
- Day columns shift by 1 for partial months

**Phase to address:** Phase 3 — T-13 Timesheet Generation

---

### Pitfall 7: `next` Redirect Parameter Open Redirect Vulnerability

**What goes wrong:**
The existing login route reads `next = request.args.get("next", ...)` and redirects there after login. The new multi-role system adds more redirects (role-specific dashboards). If `next` is not validated to be a relative path on the same host, an attacker sends a link like `https://face.almgp33.kz/login?next=https://evil.example/steal` — after login the user is redirected to the attacker's site, which can steal session data or credentials.

**Why it happens:**
The existing code already has this: `return redirect(next_url)` with no validation. It is carried forward into the new login flow without being noticed.

**How to avoid:**
Validate `next` with `urllib.parse.urlparse`: only redirect if `netloc` is empty (relative URL). Use Flask-Login's `is_safe_url` pattern or inline the check:
```python
from urllib.parse import urlparse
def is_safe_redirect(url):
    ref = urlparse(url)
    return not ref.netloc and not ref.scheme
```
Apply this to every redirect that uses user-supplied input.

**Warning signs:**
- `next` parameter in login URL contains `http://` or `https://`
- Login redirects to an external domain

**Phase to address:** Phase 1 — Auth Migration

---

### Pitfall 8: Department Hierarchy Allows Privilege Escalation via Role Creation

**What goes wrong:**
The requirement states "each role can create roles one level below itself." If this is implemented as a form field without server-side enforcement, an org_admin can POST a request to create another org_admin (same level) or a superadmin (one level above). The UI may only show `dept_admin` as an option, but a direct POST request bypasses UI constraints.

**Why it happens:**
Developers implement the UI dropdown correctly but validate the submitted role value only for non-empty, not against the permitted set for the current user's role.

**How to avoid:**
Define a `ROLE_HIERARCHY` dict and validate server-side:
```python
ROLE_HIERARCHY = {
    "superadmin": ["org_admin"],
    "org_admin": ["dept_admin", "viewer"],
    "dept_admin": ["viewer", "employee"],
}
def can_create_role(creator_role, target_role):
    return target_role in ROLE_HIERARCHY.get(creator_role, [])
```
Every role creation endpoint must call this check with `session["role"]`. Return HTTP 403 if the check fails — never just redirect.

**Warning signs:**
- A POST to the user-creation API with `role=superadmin` from an org_admin session succeeds
- The `role` field in the creation form is not re-validated on the server
- Role creation endpoint trusts the submitted role value directly

**Phase to address:** Phase 1 — RBAC Foundation

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store all data in one `employees.json` (no per-org split) | Simple reads, single migration | File grows with orgs; all writers contend on one lock | Acceptable for v1 with < 200 employees total |
| Hardcode Kazakhstan holidays as a list | No external API dependency; works offline | Must update list each year manually | Acceptable for v1; add a warning to flag when current year has no holidays defined |
| Use `fcntl` file locking instead of SQLite | No schema migration; stays in existing pattern | Does not survive multi-process gunicorn workers | Acceptable only if PM2 runs a single Flask worker; document this constraint explicitly |
| Keep `app.py` as a single file | No refactoring overhead | Role decorators, data helpers, and timesheet logic in one file will exceed 1,500 lines | Acceptable for v1 milestone; plan a Blueprint refactor for v2 |
| Session variables carry `role`, `org_id`, `dept_id` | Simple to read anywhere | Session tampering if secret key leaks; no server-side session revocation | Never acceptable without ensuring SECRET_KEY is environment-only (not the hardcoded fallback) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| openpyxl T-13 export | Writing Cyrillic strings without specifying UTF-8; Excel opens `.xlsx` but shows `?????` | openpyxl handles encoding internally for `.xlsx`; the issue is with `.csv` export — always write CSV with `utf-8-sig` (BOM) encoding so Excel on Windows opens it correctly without import wizard |
| openpyxl cell merging for T-13 header | Merging cells then writing to the merged range raises `IllegalCharacterError` if the cell already has a value from a previous iteration | Write value first, then merge; never re-write to a merged cell's slave cells |
| bcrypt in Python 3.14 | Passing `str` instead of `bytes` to `bcrypt.checkpw` raises `TypeError` silently swallowed in a try/except | Always encode: `password.encode("utf-8")`, `stored_hash.encode("utf-8")` before passing to bcrypt |
| Flask session with role data | Storing large objects (employee lists) in session; session is stored in a signed cookie with a 4KB limit | Store only scalar identifiers in session: `role`, `user_id`, `org_id`, `dept_id` — never lists or dicts |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all `attendance.json` for T-13 generation | T-13 export takes 10+ seconds; server appears hung | Load only the date range needed: iterate keys, skip outside month range | When attendance.json exceeds ~500KB (approx. 18 months × 50 employees) |
| Loading `employees.json` on every API request | Each role-filtered API call reads and parses the full file | Cache the parsed dict in a module-level variable with a TTL or invalidate on write | Noticeable at > 100 employees; problematic at > 500 |
| Generating T-13 synchronously in a web request | HR clicks Export and the browser times out at 30s | For this clinic scale (< 100 employees, 1 month), synchronous is fine; do not add a task queue for v1 | Would break at > 500 employees × 31 days |
| `train_recognizer()` called on every employee metadata save | Saving an org assignment triggers full model retrain with no face changes | Only call `train_recognizer()` when face data changes (`face_count` mutates); metadata-only saves must not trigger it | Already a problem at 3 employees; will get worse |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `next` redirect not validated (open redirect) | Credential phishing after login | Validate `next` is a relative path before redirecting (see Pitfall 7) |
| Hardcoded `SECRET_KEY` fallback in source code | Attacker reads source → forges session cookies → becomes superadmin | Make `SECRET_KEY` env-only; raise `RuntimeError` at startup if not set; remove the hardcoded fallback entirely |
| No CSRF on role mutation endpoints | Forged POST from another tab or iframe changes a user's role | Add Flask-WTF CSRF token to all state-changing forms and API calls that use session auth |
| Employee ID as sequential timestamp in URL | Predictable IDs allow IDOR: `GET /api/employee/1781154410853` leaks data if auth check is missing | Auth check is the fix, not ID obfuscation; but do not rely on ID unpredictability as a security control |
| Viewer role can access export endpoint | Viewer is read-only attendance view; export endpoint bypassed by direct URL access | Export must check role explicitly: only `dept_admin`, `org_admin`, `superadmin` may call export routes |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Kiosk (`/`) redirects to login after session expiry | Face check-in breaks silently at night; morning staff cannot clock in | Kiosk route must remain permanently public — never add `@login_required` to `/` or `/api/recognize` |
| T-13 export filename has no month/org in it | HR downloads multiple files named `timesheet.xlsx` and cannot tell them apart | Filename: `T13_{org_name}_{dept_name}_{YYYY-MM}.xlsx` |
| Error messages expose role/org structure to unauthorized users | `403 Forbidden: You are not org_admin for org_id=42` reveals org IDs | Return generic `403 Access denied` with no internal detail |
| Partial month T-13 shows empty columns for future days | HR gets confused by blank columns mid-month | Render columns only up to `min(today, last_day_of_month)` |
| Password change has no confirmation field | Admin changes password, typo locks them out | Require password + confirm password fields; verify match server-side |

---

## "Looks Done But Isn't" Checklist

- [ ] **Role enforcement:** UI hides links correctly — verify that direct URL access (`/admin/users`) returns 403 for unauthorized roles, not just a redirect
- [ ] **Data isolation:** API returns correct scoped data — verify with a curl call using a dept_admin session that employees from other departments are absent from the response
- [ ] **Kiosk still works:** After RBAC deployment — verify `GET /` loads without a session cookie and face recognition still works
- [ ] **bcrypt migration:** Admin can log in with the existing password — test immediately after Phase 1 deployment before any other testing
- [ ] **T-13 weekends:** Export for a full month — verify Saturday and Sunday columns show `В`, not blank or `О`
- [ ] **T-13 totals:** Manually verify `days_worked + absences + days_off = total_working_days` for at least one employee
- [ ] **CSV encoding:** Open the exported CSV in Excel on Windows without an import wizard — verify Cyrillic displays correctly (requires UTF-8 BOM)
- [ ] **Role creation scope:** Log in as org_admin and attempt to POST `role=superadmin` directly — verify 403 is returned
- [ ] **Employee migration:** After migration, verify every employee in the new store has `label` intact and face recognition still works
- [ ] **Viewer cannot edit:** Verify viewer session cannot POST to `/api/employees` or `/api/attendance`

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Superadmin locked out after migration | MEDIUM | SSH to server → edit `users.json` directly → set known bcrypt hash → restart pm2 |
| `employees.json` corrupted by race condition | HIGH | Restore from the most recent git-committed snapshot of `data/`; any attendance since then is lost — this is why all data files should be git-tracked or backed up before each deployment |
| Recognizer maps wrong label after migration | MEDIUM | Restore pre-migration `employees.json` snapshot; re-run migration with the additive-only script |
| T-13 wrong symbols discovered after HR submits | HIGH | Correct `resolve_symbol()` logic; re-export and have HR re-sign; no automated recovery — prevention is essential |
| Open redirect exploited | HIGH | Rotate `SECRET_KEY` (invalidates all sessions); patch redirect validation; notify affected users |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Unprotected API endpoints (role bypass) | Phase 1 — RBAC Foundation | Enumerate all routes; assert auth decorator present; curl without cookie returns 401/403 |
| Data isolation at query layer | Phase 1 — RBAC Foundation | API response scoped correctly for each role in integration test |
| bcrypt migration lockout | Phase 1 — Auth Migration | Login with known password succeeds immediately after migration deploy |
| JSON race conditions | Phase 1 — Core Infrastructure | Run concurrent registration + check-in; verify no data loss |
| Label integrity in migration | Phase 2 — Data Migration | Post-migration: train recognizer; recognize known face successfully |
| T-13 symbol edge cases | Phase 3 — Timesheet Generation | Unit test all symbol branches; manually verify exported PDF for a full month |
| Open redirect | Phase 1 — Auth Migration | Attempt redirect to external URL; verify it is rejected |
| Privilege escalation via role creation | Phase 1 — RBAC Foundation | POST `role=superadmin` as org_admin; verify 403 |

---

## Sources

- Direct codebase analysis: `/var/www/sites/face-almgp33/app.py` (422 lines, actual routes and data helpers)
- Direct data analysis: `/var/www/sites/face-almgp33/data/employees.json` (flat structure, no org/dept, integer labels)
- Codebase concerns audit: `.planning/codebase/CONCERNS.md` (race conditions, no CSRF, no input validation documented)
- Project requirements: `.planning/PROJECT.md` (5-role system, isolation constraints, kiosk constraint)
- Domain knowledge: Flask session auth patterns, RBAC implementation mistakes, Kazakhstan T-13 form requirements, openpyxl encoding behavior

---
*Pitfalls research for: Flask RBAC + T-13 Timesheet (brownfield, clinic)*
*Researched: 2026-06-11*
