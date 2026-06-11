# Codebase Concerns

**Mapped:** 2026-06-11
**Focus:** Technical debt, bugs, security, performance, fragile areas

---

## Security Issues

| Severity | Issue | Location |
|----------|-------|----------|
| High | Hardcoded Flask secret key fallback — should be environment-only | `app.py` config |
| High | Missing CSRF protection on admin endpoints | Admin routes |
| High | No input validation/sanitization on employee data | Employee forms |
| High | Unvalidated base64 image processing — malformed input not rejected | Face capture endpoint |
| Medium | No rate limiting on face processing endpoints | Recognition routes |
| Medium | Only a single hardcoded admin account — no multi-user admin support | Auth config |
| Low | No session timeout | Session config |

---

## Technical Debt

- **Global state for OpenCV recognizer** — shared mutable state across requests; race conditions under concurrent load
- **Synchronous face detection** — blocks the request thread; no async/queue-based processing
- **JSON-based storage** — no transactions, concurrent write collisions possible; not suitable for production scale
- **Face labels based on employee count** — breaks referential integrity when employees are deleted (index shift)
- **Training state not locked during recognition** — model can be partially retrained while a recognition request is in-flight

---

## Performance Bottlenecks

- **Full model retraining on every face registration** — O(n) training cost scales poorly as employee count grows
- **Face detection runs twice per recognition cycle** — redundant computation
- **Attendance log array grows unbounded** — no archiving or pagination; large logs degrade read performance

---

## Fragile Areas

- **Race conditions during concurrent face registrations** — two simultaneous registrations can corrupt training data
- **Attendance assumes single check-in/out per day** — no support for shift workers or multiple sessions
- **Date boundary issues** — midnight-crossing shifts (e.g. night shifts) are not handled correctly
- **No backup of face training data** — loss of training files requires full re-registration of all employees

---

## Missing Capabilities

- No audit trail viewer (who approved what, when)
- No backup/restore for face training data
- No multi-admin support
- No session timeout enforcement

---

## Recommended Priorities

1. **Immediate:** Fix secret key handling (env-only), add CSRF protection
2. **Short-term:** Replace JSON storage with SQLite/PostgreSQL, add input validation
3. **Medium-term:** Move face processing to a background queue, fix label-on-delete bug
4. **Long-term:** Add rate limiting, session timeout, multi-admin support

---
*Last mapped: 2026-06-11*
