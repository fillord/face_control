---
phase: 1
slug: rbac-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (Wave 0 installs via pip) |
| **Config file** | `pytest.ini` — none; Wave 0 creates `tests/conftest.py` |
| **Quick run command** | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q` |
| **Full suite command** | `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -x -q`
- **After every plan wave:** Run `/var/www/sites/face-almgp33/venv/bin/pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 0 | AUTH-01 | — | Valid bcrypt login succeeds; invalid fails | unit | `pytest tests/test_auth.py::test_login_valid -x` | ❌ W0 | ⬜ pending |
| 01-02 | 01 | 0 | AUTH-02 | — | `init_users()` creates superadmin when `users.json` absent | unit | `pytest tests/test_auth.py::test_init_users_bootstrap -x` | ❌ W0 | ⬜ pending |
| 01-03 | 01 | 0 | MIG-03 | — | Hash from `config.json` copied verbatim (not re-hashed) | unit | `pytest tests/test_auth.py::test_init_users_migrates_hash -x` | ❌ W0 | ⬜ pending |
| 01-04 | 01 | 0 | AUTH-03 | — | `dept_admin` can create `viewer`; `viewer` cannot create any account | unit | `pytest tests/test_rbac.py::test_privilege_hierarchy -x` | ❌ W0 | ⬜ pending |
| 01-05 | 01 | 0 | AUTH-04 | — | Session stores `user_id`, `role`, `org_id`, `dept_id` after login | unit | `pytest tests/test_auth.py::test_session_contents -x` | ❌ W0 | ⬜ pending |
| 01-06 | 01 | 0 | AUTH-05 | — | Unauthenticated `/admin` redirects to `/login`; kiosk routes remain public | unit | `pytest tests/test_rbac.py::test_unauthenticated_redirect -x` / `pytest tests/test_rbac.py::test_public_routes -x` | ❌ W0 | ⬜ pending |
| 01-07 | 01 | 0 | AUTH-06 | — | Password change with correct current password succeeds; wrong password rejected | unit | `pytest tests/test_auth.py::test_password_change -x` | ❌ W0 | ⬜ pending |
| 01-08 | 01 | 0 | AUTH-07 | — | Deactivated user login attempt is rejected | unit | `pytest tests/test_auth.py::test_deactivated_user -x` | ❌ W0 | ⬜ pending |
| 01-09 | 01 | 0 | DASH-03 | — | `superadmin` login redirects to `/admin`; `viewer`/`employee` to `/dashboard` | unit | `pytest tests/test_rbac.py::test_post_login_redirect -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — Flask test client fixture, shared test helpers
- [ ] `tests/test_auth.py` — stubs for AUTH-01, AUTH-02, AUTH-04, AUTH-06, AUTH-07, MIG-03
- [ ] `tests/test_rbac.py` — stubs for AUTH-03, AUTH-05, DASH-03
- [ ] `pip install pytest` in venv — pytest 9.0.3 not yet installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 403 page renders correctly with "Back to dashboard" link | AUTH-05 | Visual UI verification | Log in as `viewer`, navigate to `/admin`; confirm 403.html renders with correct message and link |
| Navigation shows only role-appropriate links | DASH-03 | Template rendering depends on session state | Log in as each of the 5 roles; verify nav items visible match role permissions |
| PM2 restart loads new SECRET_KEY env var | AUTH-04 | Process manager integration | After `pm2 restart face-recognition`, check `pm2 logs` shows app started; login session persists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
