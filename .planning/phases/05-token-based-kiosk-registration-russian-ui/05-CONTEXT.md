# Phase 5: Token-based Kiosk, Registration & Russian UI — Context

**Gathered:** 2026-06-12
**Status:** Ready for planning
**Source:** User spec (synthesized as PRD Express Path)

<domain>
## Phase Boundary

This phase introduces token-based URLs for kiosk and employee registration, replaces the PIN system with bcrypt-hashed 4-digit codes stored on the organization record, migrates existing data, and rebuilds all UI pages in Russian with МедКонтроль branding and role-scoped navigation. Face recognition logic is NOT changed.

</domain>

<decisions>
## Implementation Decisions

### Data model — organizations.json
- Add `org_token`: 8-char alphanumeric random string (URL-safe, unique per org)
- Add `kiosk_pin`: bcrypt hash of a 4-digit string; default plaintext "0000" hashed at migration time
- Add `reg_token`: 8-char alphanumeric random string (URL-safe, unique per org)
- Add `reg_pin`: bcrypt hash of a 4-digit string; default plaintext "1234" hashed at migration time
- Add `reg_token_expires`: ISO 8601 datetime string; org_admin can set expiry when sharing registration link
- Add `kiosk_display_name`: human-readable org name shown on kiosk screen (e.g., "Поликлиника №33")

### Data model — users.json
- Roles allowed: `superadmin`, `org_admin`, `dept_admin` only (NOT `dept_manager` — codebase uses `dept_admin`)
- Employees are NOT users — they live in employees.json and authenticate only via face recognition
- If any existing user entry has a role outside these three, it must be rejected at login (not silently allowed)

### Data model — employees.json
- Keep all existing fields
- Ensure presence of: `org_id`, `dept_id`, `name`, `role`/`position`, `label`, `face_count`, `schedule`
- No new fields required on employees

### Kiosk flow
- URL: `/kiosk/<org_token>` — the token identifies the org; no login required to load the page
- On load: look up org by `org_token`; if not found → 404
- PIN entry: touchscreen-friendly large number pad (on-screen buttons 0–9, backspace, submit)
- PIN verification: bcrypt.check(entered_pin, org.kiosk_pin)
- On correct PIN: display kiosk camera view (existing face recognition UI adapted for org scope)
- On wrong PIN: show error, allow retry (no lockout required for v1)
- Kiosk shows `kiosk_display_name` in header while idle and after recognition
- Show department name below employee name on successful recognition (absorbs 02-05 requirement)

### Registration flow
- URL: `/register/<reg_token>` — the token identifies the org
- On load: check `reg_token_expires`; if expired → show "Ссылка истекла" error page
- PIN entry: same touchscreen number pad style as kiosk
- PIN verification: bcrypt.check(entered_pin, org.reg_pin)
- On correct PIN: show employee registration form (name, department, photo capture)
- Page must be mobile-friendly (employees open on phone; use large touch targets, responsive layout)
- Face photo capture via device camera (reuse existing WebRTC logic)

### migrate.py
- Read existing `data/organizations.json`
- For each org that lacks `org_token`: generate one (8 chars, alphanumeric, unique)
- For each org that lacks `reg_token`: generate one (8 chars, alphanumeric, unique)
- For each org that lacks `kiosk_pin`: hash "0000" with bcrypt, store hash
- For each org that lacks `reg_pin`: hash "1234" with bcrypt, store hash
- For each org that lacks `reg_token_expires`: set to None/null (no expiry by default)
- For each org that lacks `kiosk_display_name`: set to org `name` field
- Preserve all existing fields and all other data files unchanged
- Print a summary of what was updated

### Russian UI + МедКонтроль branding
- All visible text on all pages must be in Russian
- System name: "МедКонтроль"
- Headers per role:
  - superadmin: "МедКонтроль — Суперадмин"
  - org_admin: "МедКонтроль — [org.name]"
  - dept_manager: "МедКонтроль — [dept.name]"
- Navigation: each role sees ONLY the items relevant to their role (no hidden/disabled links for other roles)
- Clean, professional medical system look (not consumer UI)

### Verification after deploy
- `python migrate.py` must complete without error
- `pm2 restart face-recognition`
- `curl http://127.0.0.1:5051/login` → HTTP 200
- `curl http://127.0.0.1:5051/kiosk/<any_valid_org_token>` → HTTP 200

### Claude's Discretion
- Token generation: `secrets.token_urlsafe(6)` truncated/encoded to 8 chars, or `secrets.token_hex(4)` (8 hex chars) — either is fine
- CSS framework: stay inline/vanilla CSS consistent with existing templates (no new framework)
- PIN pad HTML: build as a simple grid of `<button>` elements, no JS library
- Error pages for expired reg token / invalid org token: minimal, Russian-language, styled consistently

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing codebase
- `app.py` — all Flask routes, auth decorators, JSON helpers; face recognition unchanged
- `templates/kiosk.html` — existing kiosk template (will be replaced/updated)
- `templates/login.html` — existing login template (reference for Russian translation)
- `templates/register.html` — existing registration template (will be replaced/updated)
- `templates/superadmin.html` — existing superadmin dashboard (reference for nav pattern)
- `data/organizations.json` — current org data structure (must understand before adding fields)
- `data/employees.json` — current employee structure
- `data/users.json` — current user records + roles

### Planning artifacts
- `.planning/ROADMAP.md` — Phase 5 goal and requirements
- `.planning/STATE.md` — prior decisions (bcrypt usage pattern, JSON storage constraints)

</canonical_refs>

<specifics>
## Specific Ideas

- org_admin must be able to change `kiosk_pin` and `reg_pin` via the admin dashboard (a settings form, not just via migrate.py)
- org_admin must be able to regenerate `reg_token` (to invalidate old registration links)
- org_admin must be able to set `reg_token_expires` (to time-limit registration campaigns)
- The kiosk PIN pad should work without keyboard input (touchscreen only) — no `<input type="text">` that pops a keyboard on mobile
- Department name shown on kiosk recognition screen (absorbs Plan 02-05)

</specifics>

<deferred>
## Deferred Ideas

- PIN lockout after N failed attempts (not required for v1)
- Multiple kiosk PINs per org (v1: single PIN per org)
- QR code generation for registration link (v1: plain URL sharing)
- Email notifications for registration events

</deferred>

---

*Phase: 05-token-based-kiosk-registration-russian-ui*
*Context gathered: 2026-06-12 via user spec*
