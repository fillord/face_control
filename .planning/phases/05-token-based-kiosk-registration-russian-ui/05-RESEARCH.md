# Phase 5: Token-based Kiosk, Registration & Russian UI — Research

**Researched:** 2026-06-12
**Domain:** Flask routing, bcrypt PIN auth, token generation, touchscreen PIN pad UI, data migration, Russian UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data model — organizations.json**
- Add `org_token`: 8-char alphanumeric random string (URL-safe, unique per org)
- Add `kiosk_pin`: bcrypt hash of a 4-digit string; default plaintext "0000" hashed at migration time
- Add `reg_token`: 8-char alphanumeric random string (URL-safe, unique per org)
- Add `reg_pin`: bcrypt hash of a 4-digit string; default plaintext "1234" hashed at migration time
- Add `reg_token_expires`: ISO 8601 datetime string; org_admin can set expiry when sharing registration link
- Add `kiosk_display_name`: human-readable org name shown on kiosk screen (e.g., "Поликлиника №33")

**Data model — users.json**
- Roles allowed: `superadmin`, `org_admin`, `dept_manager` only
- Employees are NOT users — they live in employees.json and authenticate only via face recognition
- If any existing user entry has a role outside these three, it must be rejected at login (not silently allowed)

**Data model — employees.json**
- Keep all existing fields
- Ensure presence of: `org_id`, `dept_id`, `name`, `role`/`position`, `label`, `face_count`, `schedule`
- No new fields required on employees

**Kiosk flow**
- URL: `/kiosk/<org_token>` — the token identifies the org; no login required to load the page
- On load: look up org by `org_token`; if not found → 404
- PIN entry: touchscreen-friendly large number pad (on-screen buttons 0–9, backspace, submit)
- PIN verification: bcrypt.check(entered_pin, org.kiosk_pin)
- On correct PIN: display kiosk camera view (existing face recognition UI adapted for org scope)
- On wrong PIN: show error, allow retry (no lockout required for v1)
- Kiosk shows `kiosk_display_name` in header while idle and after recognition
- Show department name below employee name on successful recognition (absorbs 02-05 requirement)

**Registration flow**
- URL: `/register/<reg_token>` — the token identifies the org
- On load: check `reg_token_expires`; if expired → show "Ссылка истекла" error page
- PIN entry: same touchscreen number pad style as kiosk
- PIN verification: bcrypt.check(entered_pin, org.reg_pin)
- On correct PIN: show employee registration form (name, department, photo capture)
- Page must be mobile-friendly (employees open on phone; use large touch targets, responsive layout)
- Face photo capture via device camera (reuse existing WebRTC logic)

**migrate.py**
- Read existing `data/orgs.json` (file is `orgs.json`, not `organizations.json`)
- For each org that lacks `org_token`: generate one (8 chars, alphanumeric, unique)
- For each org that lacks `reg_token`: generate one (8 chars, alphanumeric, unique)
- For each org that lacks `kiosk_pin`: hash "0000" with bcrypt, store hash
- For each org that lacks `reg_pin`: hash "1234" with bcrypt, store hash
- For each org that lacks `reg_token_expires`: set to None/null (no expiry by default)
- For each org that lacks `kiosk_display_name`: set to org `name` field
- Preserve all existing fields and all other data files unchanged
- Print a summary of what was updated

**Russian UI + МедКонтроль branding**
- All visible text on all pages must be in Russian
- System name: "МедКонтроль"
- Headers per role:
  - superadmin: "МедКонтроль — Суперадмин"
  - org_admin: "МедКонтроль — [org.name]"
  - dept_manager: "МедКонтроль — [dept.name]"
- Navigation: each role sees ONLY the items relevant to their role (no hidden/disabled links for other roles)
- Clean, professional medical system look (not consumer UI)

**Verification after deploy**
- `python migrate.py` must complete without error
- `pm2 restart face-recognition`
- `curl http://127.0.0.1:5051/login` → HTTP 200
- `curl http://127.0.0.1:5051/kiosk/<any_valid_org_token>` → HTTP 200

### Claude's Discretion
- Token generation: `secrets.token_urlsafe(6)` truncated/encoded to 8 chars, or `secrets.token_hex(4)` (8 hex chars) — either is fine
- CSS framework: stay inline/vanilla CSS consistent with existing templates (no new framework)
- PIN pad HTML: build as a simple grid of `<button>` elements, no JS library
- Error pages for expired reg token / invalid org token: minimal, Russian-language, styled consistently

### Deferred Ideas (OUT OF SCOPE)
- PIN lockout after N failed attempts (not required for v1)
- Multiple kiosk PINs per org (v1: single PIN per org)
- QR code generation for registration link (v1: plain URL sharing)
- Email notifications for registration events
</user_constraints>

---

## Summary

Phase 5 has three tightly coupled concerns: (1) upgrading the data model for organizations to carry tokens and bcrypt-hashed PINs, (2) replacing the URL scheme for kiosk and registration from identity-based (org_id) to token-based (org_token/reg_token), and (3) auditing all pages for role-scoped navigation and Russian text.

The critical discovery is that the **existing codebase already partially implements this phase** — `kiosk.html` has a PIN screen, `app.py` has `/kiosk/<org_id>` and `/api/kiosk/<org_id>/verify_pin` routes, and the org settings PATCH endpoint accepts a `kiosk_pin` field. However, the current PIN implementation stores and compares **plaintext** PINs. Phase 5 must upgrade this to bcrypt, change the URL parameter from `org_id` to `org_token`, and add the `reg_token` / `reg_pin` / `reg_token_expires` / `kiosk_display_name` fields.

There is also a role naming ambiguity: `CONTEXT.md` and the ROADMAP both specify `dept_manager` as the third allowed role in users.json, but the entire existing codebase uses `dept_admin`. The planner must resolve this — either the role string in users.json changes (requiring a data migration for existing users) or `dept_manager` in the CONTEXT.md is a documentation alias for `dept_admin`. This is the most significant open question.

**Primary recommendation:** Migrate orgs.json with bcrypt tokens first, update routes next, rebuild kiosk and register templates last. Use `secrets.token_hex(4)` for 8-character tokens (simpler, no padding/truncation).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| org_token lookup | API / Backend (Flask) | — | Token-to-org mapping is server-side; the client never holds the org_id |
| reg_token expiry check | API / Backend (Flask) | — | Time comparison must be server-authoritative |
| bcrypt PIN verification | API / Backend (Flask) | — | Never verify bcrypt in JS; endpoint `/api/kiosk/<org_token>/verify_pin` |
| Touchscreen PIN pad | Browser / Client | — | HTML `<button>` grid rendered in kiosk.html / register template |
| PIN session cache (8h) | Browser / Client | — | localStorage key per org_token (same pattern as current code) |
| Token generation | API / Backend (migrate.py + app.py) | — | `secrets.token_hex(4)` runs server-side only |
| Role-scoped navigation | Frontend (Jinja2 template) | API / Backend (session) | Jinja2 renders nav based on `session.role` passed by Flask route |
| org_admin PIN/token management | API / Backend (Flask PATCH) | Frontend (org_admin.html) | Settings form POSTs to `/api/orgs/<org_id>/settings` |
| Face recognition display (dept name) | Browser / Client | API / Backend | `/api/recognize` already returns `dept_name`; JS in kiosk.html renders it |

---

## Standard Stack

### Core (no new packages required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `bcrypt` | 5.0.0 (already installed) | PIN hashing and verification | Already used throughout app.py for passwords; same pattern for PINs |
| `secrets` | stdlib | Token generation | Python stdlib, cryptographically secure; no install needed |
| `datetime` | stdlib | reg_token_expires comparison | Already imported in app.py |
| Flask | 3.1.3 (already installed) | Route handling for new URLs | Existing framework |

**No new packages are required for this phase.** All needed libraries are already installed in the venv.

[VERIFIED: codebase grep — bcrypt imported at app.py:8, datetime at app.py:4, secrets is stdlib]

### Installation

```bash
# No new packages. Verify existing:
/var/www/sites/face-almgp33/venv/bin/pip show bcrypt
```

---

## Package Legitimacy Audit

**No new packages in this phase.** All functionality is implemented using existing installed packages (`bcrypt` 5.0.0, already in venv) and Python stdlib (`secrets`, `datetime`). Package legitimacy audit: N/A.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (kiosk touchscreen)
    │
    ├─ GET /kiosk/<org_token>
    │       │
    │       └─ Flask: look up org by org_token field in orgs.json
    │               → if not found: 404
    │               → if found: render kiosk.html (org_token, org data passed)
    │
    ├─ POST /api/kiosk/<org_token>/verify_pin  {pin: "1234"}
    │       │
    │       └─ Flask: load org by org_token
    │               → bcrypt.checkpw(pin.encode(), org["kiosk_pin"].encode())
    │               → 200 {verified: true} or 401 {verified: false}
    │
    └─ POST /api/recognize  {image, org_token}  (PIN already verified via localStorage)
            │
            └─ Flask: recognize face, filter by org (use org_token→org_id mapping)
                    → return {employee, dept_name, ...}

Browser (mobile — employee registration)
    │
    ├─ GET /register/<reg_token>
    │       │
    │       └─ Flask: look up org by reg_token field in orgs.json
    │               → check reg_token_expires (if set and expired → 410/show error)
    │               → if OK: render register_token.html (PIN pad phase)
    │
    └─ POST /api/register/<reg_token>/verify_pin  {pin: "1234"}
            │
            └─ Flask: bcrypt.checkpw(pin.encode(), org["reg_pin"].encode())
                    → 200 {verified: true, org_id, org_name} or 401

org_admin browser
    │
    └─ PATCH /api/orgs/<org_id>/settings
            {kiosk_pin: "5678", reg_pin: "4321", reg_token_expires: "2026-07-01T00:00:00",
             kiosk_display_name: "Поликлиника №33", regen_reg_token: true}
            │
            └─ Flask: hash PIN with bcrypt before storing; generate new reg_token if requested
```

### Recommended Project Structure

No new directories needed. New files:

```
/var/www/sites/face-almgp33/
├── migrate.py              # REPLACE — Phase 5 extends Phase 2 migrate.py
├── app.py                  # MODIFY — add new routes, upgrade PIN verification
└── templates/
    ├── kiosk.html          # REPLACE — token-based URL, touchscreen PIN pad, kiosk_display_name
    ├── register.html       # REPLACE — now at /register/<reg_token>, public, mobile-friendly
    ├── superadmin.html     # MODIFY — role-scoped nav, org kiosk settings panel
    ├── org_admin.html      # MODIFY — kiosk/reg PIN settings form, token display, reg_token regen
    ├── dept_admin.html     # MODIFY — header shows dept name, nav is dept-scoped only
    └── error_token.html    # NEW — "Ссылка недействительна" / "Ссылка истекла" error page
```

### Pattern 1: org_token lookup (replace org_id URL parameter)

**What:** Look up org by token field value instead of dict key (org_id)
**When to use:** Any route that uses `org_token` or `reg_token` in the URL

```python
# Source: app.py codebase — adapted from existing load_orgs() pattern
def find_org_by_token(orgs: dict, field: str, value: str):
    """Return (org_id, org) tuple matching field == value, or (None, None)."""
    for org_id, org in orgs.items():
        if org.get(field) == value:
            return org_id, org
    return None, None

@app.route("/kiosk/<org_token>")
def kiosk_token(org_token):
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "org_token", org_token)
    if not org:
        return render_template("error_token.html", message="Организация не найдена"), 404
    employees = load_employees()
    org_employees = {k: v for k, v in employees.items() if v.get("org_id") == org_id}
    return render_template("kiosk.html",
        has_employees=bool(org_employees),
        org_token=org_token,
        org_id=org_id,
        org_name=org.get("kiosk_display_name") or org.get("name"),
        has_pin=bool(org.get("kiosk_pin")),
    )
```

[VERIFIED: codebase grep — existing kiosk_org route at app.py:227 uses identical load_orgs() + employee filter pattern]

### Pattern 2: bcrypt PIN verification endpoint

**What:** Replace plaintext PIN comparison with bcrypt.checkpw
**When to use:** `/api/kiosk/<org_token>/verify_pin` and `/api/register/<reg_token>/verify_pin`

```python
# Source: app.py — same pattern as password verification at line 260
@app.route("/api/kiosk/<org_token>/verify_pin", methods=["POST"])
def verify_kiosk_pin_token(org_token):
    orgs = load_orgs()
    org_id, org = find_org_by_token(orgs, "org_token", org_token)
    if not org:
        return jsonify({"error": "not_found"}), 404
    stored_hash = org.get("kiosk_pin")
    if not stored_hash:
        return jsonify({"verified": True})  # no PIN set — open access
    entered_pin = str((request.json or {}).get("pin", ""))
    if bcrypt.checkpw(entered_pin.encode(), stored_hash.encode()):
        return jsonify({"verified": True})
    return jsonify({"error": "wrong_pin", "verified": False}), 401
```

[VERIFIED: codebase grep — bcrypt.checkpw pattern at app.py:260 and 399]

### Pattern 3: Touchscreen PIN pad (no keyboard)

**What:** CSS grid of `<button>` elements; no `<input>` that triggers mobile keyboard
**When to use:** Both kiosk and registration PIN screens

```html
<!-- Source: CONTEXT.md decision + CSS grid pattern from existing templates -->
<div id="pinDisplay">
  <span id="pinDot0">○</span><span id="pinDot1">○</span>
  <span id="pinDot2">○</span><span id="pinDot3">○</span>
</div>
<div class="pin-grid">
  <button type="button" onclick="pinPress('1')">1</button>
  <button type="button" onclick="pinPress('2')">2</button>
  <button type="button" onclick="pinPress('3')">3</button>
  <button type="button" onclick="pinPress('4')">4</button>
  <button type="button" onclick="pinPress('5')">5</button>
  <button type="button" onclick="pinPress('6')">6</button>
  <button type="button" onclick="pinPress('7')">7</button>
  <button type="button" onclick="pinPress('8')">8</button>
  <button type="button" onclick="pinPress('9')">9</button>
  <button type="button" onclick="pinPress('back')">⌫</button>
  <button type="button" onclick="pinPress('0')">0</button>
  <button type="button" onclick="pinPress('submit')">OK</button>
</div>
<style>
.pin-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; max-width: 280px; }
.pin-grid button { height: 72px; font-size: 26px; font-weight: 600; border-radius: 14px;
  background: #0d1429; border: 2px solid #1e2a4a; color: #e8eaf6; cursor: pointer; }
.pin-grid button:active { background: #1a2240; }
</style>
<script>
let pinDigits = [];
function pinPress(val) {
  if (val === 'back') { pinDigits.pop(); }
  else if (val === 'submit') { if (pinDigits.length === 4) submitPin(); }
  else if (pinDigits.length < 4) { pinDigits.push(val); }
  updatePinDisplay();
  if (pinDigits.length === 4 && val !== 'submit' && val !== 'back') submitPin();
}
function updatePinDisplay() {
  for (let i = 0; i < 4; i++) {
    document.getElementById('pinDot' + i).textContent = i < pinDigits.length ? '●' : '○';
  }
}
async function submitPin() {
  const pin = pinDigits.join('');
  // POST to verify endpoint...
}
</script>
```

[ASSUMED — this specific button layout; the pattern follows the CONTEXT.md decision and CSS grid conventions from existing templates]

### Pattern 4: Token generation in migrate.py

```python
# Source: Python stdlib docs — secrets module
import secrets

def generate_unique_token(existing_tokens: set, length_hex: int = 4) -> str:
    """Generate an 8-char hex token not already in existing_tokens."""
    while True:
        token = secrets.token_hex(length_hex)  # 8 hex chars
        if token not in existing_tokens:
            return token
```

[VERIFIED: Python stdlib — secrets.token_hex(4) produces 8 hex characters, confirmed by runtime test]

### Pattern 5: reg_token_expires comparison

```python
# Source: Python stdlib datetime — already imported in app.py
from datetime import datetime

def is_reg_token_expired(org: dict) -> bool:
    """Return True if reg_token_expires is set and in the past."""
    expires_str = org.get("reg_token_expires")
    if not expires_str:
        return False  # None/null = no expiry
    try:
        expires = datetime.fromisoformat(expires_str)
        # Remove timezone info for naive comparison if needed
        now = datetime.now()
        if expires.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
        return now > expires
    except (ValueError, TypeError):
        return False  # malformed date = treat as not expired (safe default)
```

[VERIFIED: codebase grep — datetime.fromisoformat used in Python 3.7+; confirmed Python 3.14.4 in use]

### Pattern 6: org_admin settings PATCH upgrade (bcrypt PIN storage)

Current `/api/orgs/<org_id>/settings` stores plaintext PIN. Must be upgraded:

```python
# Source: app.py line 546 — existing endpoint, needs upgrade
if "kiosk_pin" in data:
    pin = str(data["kiosk_pin"]).strip()
    if pin and (len(pin) != 4 or not pin.isdigit()):
        return jsonify({"error": "PIN должен быть 4-значным числом"}), 400
    # CHANGED: store bcrypt hash, not plaintext
    orgs[org_id]["kiosk_pin"] = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode() if pin else None
```

[VERIFIED: codebase grep — existing endpoint at app.py:546 stores plaintext; bcrypt.hashpw pattern at app.py:43, 78, 406, 458]

### Anti-Patterns to Avoid

- **Storing plaintext PINs:** The existing `kiosk_pin` in orgs.json is plaintext (e.g., "2386"). After migration it must be a bcrypt hash. The migration must detect plaintext (not starting with `$2b$`) and re-hash it.
- **Using `<input>` for touchscreen PIN:** The existing kiosk.html uses `<input type="password">` per digit which triggers the mobile keyboard. Phase 5 must use `<button>` elements only.
- **Looking up org by `org_id` URL parameter for new routes:** New routes use `org_token` as a URL parameter; the org_id is only used internally after the token-to-org lookup.
- **Keeping old `/kiosk/<org_id>` route as a redirect:** This would leak org_id to external links. The old route should be removed or redirected to `/login` to avoid confusion.
- **Comparing PIN hash as plaintext:** `bcrypt.checkpw` must be used, not `==`.
- **Using `datetime.utcnow()` for expiry comparison:** Deprecated in Python 3.12+; use `datetime.now()` for naive or `datetime.now(timezone.utc)` for aware datetimes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secure PIN hashing | Custom hash/salt logic | `bcrypt.hashpw` / `bcrypt.checkpw` | Already imported; bcrypt handles salting automatically |
| Random token generation | `random.randint()` or `uuid4()` | `secrets.token_hex(4)` | `secrets` is cryptographically secure; `random` is not |
| Token expiry enforcement | Manual timestamp math | `datetime.fromisoformat()` + `datetime.now()` comparison | stdlib handles ISO 8601 parsing |
| PIN uniqueness across orgs | Custom set tracking | Simple set comprehension on org dict values | Tokens are per-org, not globally unique by design |
| Mobile-friendly PIN input | Custom touch event handling | CSS grid of `<button>` elements | No JavaScript library needed |

---

## Runtime State Inventory

> Phase 5 is a migration/upgrade phase — runtime state audit is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/orgs.json`: 2 orgs with `kiosk_pin` stored as **plaintext** ("null" and "2386") | migrate.py must detect plaintext PIN (not starting with `$2b$`) and re-hash with bcrypt before storing |
| Stored data | `data/orgs.json`: missing fields: `org_token`, `reg_token`, `reg_pin`, `reg_token_expires`, `kiosk_display_name` on all records | migrate.py adds these fields |
| Stored data | `data/users.json`: has 4 users with roles: superadmin, dept_admin, org_admin, org_admin | If Phase 5 renames `dept_admin` to `dept_manager`, the existing user record needs its role field updated |
| Live service config | PM2 process "face-recognition" running on port 5051 | `pm2 restart face-recognition` after deploy |
| OS-registered state | PM2 process registered — name "face-recognition" unchanged | No change needed |
| Secrets/env vars | `SECRET_KEY` in ecosystem.config.js — unchanged | No change needed |
| Build artifacts | `tests/__pycache__` and `app.py __pycache__` | Cleared automatically on restart |
| Browser state | `localStorage` key `kiosk_pin_unlocked_<org_id>` in existing kiosk sessions | Will be invalidated naturally — new URL uses `org_token` as key suffix, different from old `org_id` |

**Critical migration detail:** The existing `kiosk_pin` value `"2386"` in `orgs.json` is **plaintext**. The Phase 2 migrate.py stored it as-is. Phase 5 migrate.py must detect non-bcrypt values (check if value starts with `$2b$`) and re-hash them.

---

## Common Pitfalls

### Pitfall 1: Plaintext PIN detection in migrate.py
**What goes wrong:** migrate.py skips orgs that already have `kiosk_pin` set, assuming the value is already a bcrypt hash. But one org has `kiosk_pin: "2386"` (plaintext from Phase 2's settings UI).
**Why it happens:** Phase 2 stored the PIN as plaintext string; Phase 5 wants bcrypt.
**How to avoid:** In migrate.py, check if `kiosk_pin` starts with `"$2b$"`. If not, it is plaintext and must be re-hashed. If it is null, hash the default "0000".
**Warning signs:** `bcrypt.checkpw` raises ValueError if the stored hash is not a valid bcrypt hash (not starting with `$2b$`).

```python
# Detection pattern:
def is_bcrypt_hash(value: str | None) -> bool:
    return bool(value and str(value).startswith("$2b$"))
```

### Pitfall 2: Route conflict between old /kiosk/<org_id> and new /kiosk/<org_token>
**What goes wrong:** Flask has both `@app.route("/kiosk/<org_id>")` (line 227) and `@app.route("/kiosk/<org_token>")`. Flask cannot distinguish them — both are `<string>` URL variables. Keeping both causes a route conflict or the old one never fires.
**Why it happens:** Flask URL variable names are decorative; both match the same URL pattern.
**How to avoid:** Remove the old `/kiosk/<org_id>` route entirely. Replace with the new `/kiosk/<org_token>` route that looks up by `org.org_token` field. Also remove or redirect the old `/api/kiosk/<org_id>/verify_pin` endpoint.

### Pitfall 3: /register route collision
**What goes wrong:** The existing `/register` route (line 288) has `@require_role("superadmin", "org_admin", "dept_admin")`. The new `/register/<reg_token>` must be public. Both must coexist during transition if the admin register page is still needed.
**Why it happens:** `/register` (no token) is for authenticated admins; `/register/<reg_token>` is for public token-based employee registration. These are different pages.
**How to avoid:** Keep `/register` as-is for authenticated admin face registration flow. Add `/register/<reg_token>` as a new public route. The two routes do not conflict — Flask distinguishes them by the presence/absence of the path segment.

### Pitfall 4: dept_manager vs dept_admin role string
**What goes wrong:** CONTEXT.md specifies `dept_manager` as the role string; the entire codebase uses `dept_admin`. If Phase 5 keeps `dept_admin` unchanged and the planner writes new code checking for `dept_manager`, nothing will work for existing users.
**Why it happens:** The user spec used a different label from what Phase 1 implemented.
**How to avoid:** See Open Questions below — this must be resolved before planning begins. **[ASSUMED — the intent is ambiguous between a rename and a documentation alias]**

### Pitfall 5: bcrypt slowness during migrate.py on many orgs
**What goes wrong:** bcrypt.gensalt() uses work factor 12 by default (≈250ms per hash). For 2 orgs with 2 PINs each = 4 hashes ≈ 1 second. Acceptable for migration.
**Why it happens:** bcrypt is intentionally slow.
**How to avoid:** No workaround needed for v1 (few orgs). Print progress messages so the operator knows migration is running.

### Pitfall 6: reg_token_expires timezone awareness
**What goes wrong:** `datetime.fromisoformat("2026-07-01T00:00:00+05:00")` returns a timezone-aware datetime. Comparing with `datetime.now()` (naive) raises TypeError in Python 3.
**Why it happens:** ISO 8601 strings may or may not include timezone offset.
**How to avoid:** Strip timezone info or use `datetime.now(timezone.utc)` consistently. Safest: use `datetime.fromisoformat(s).replace(tzinfo=None)` for naive comparison if the system is on local time.

### Pitfall 7: /api/recognize still uses org_id field in request body
**What goes wrong:** `kiosk.html` sends `org_id: ORG_ID` in the recognize request. After Phase 5, the kiosk knows `org_token` and `org_id` (both passed from Flask to the template). The `/api/recognize` endpoint filters by `org_id` (line 993-994). This must remain `org_id` — the kiosk template gets `org_id` from the Jinja2 render context.
**Why it happens:** The recognize endpoint is in the unchanged face recognition domain.
**How to avoid:** Pass both `org_token` and `org_id` to `kiosk.html` from the Flask route. Keep the JS `ORG_ID` variable (used for recognize and kiosk_log) as the actual org UUID. Use `ORG_TOKEN` only for the verify_pin API call.

---

## Code Examples

### Existing bcrypt pattern (confirmed from app.py)

```python
# Hashing a PIN (same as password hashing at app.py:406, 458):
pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()  # store this string

# Verifying a PIN (same as password check at app.py:260, 399):
valid = bcrypt.checkpw(entered_pin.encode(), stored_hash.encode())  # returns bool
```

[VERIFIED: codebase grep — app.py lines 43, 78, 260, 399, 406, 458]

### Existing save_orgs pattern (confirmed from app.py)

```python
# app.py lines 144-149 — direct flock (not tempfile+replace like save_users)
def save_orgs(data):
    with open(ORGS_FILE, "w", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fcntl.flock(fh, fcntl.LOCK_UN)
```

[VERIFIED: codebase read — app.py lines 144-149]

### Existing kiosk.html JS PIN localStorage cache pattern (confirmed)

```javascript
// app.py kiosk.html line 233-234 — PIN unlock cache key per org
const PIN_UNLOCK_KEY = 'kiosk_pin_unlocked_' + (ORG_ID || 'root');
const PIN_TIMEOUT_MS = 8 * 60 * 60 * 1000; // 8 hours

function isPinUnlocked() {
  const ts = parseInt(localStorage.getItem(PIN_UNLOCK_KEY) || '0', 10);
  return Date.now() - ts < PIN_TIMEOUT_MS;
}
function unlockPin() {
  localStorage.setItem(PIN_UNLOCK_KEY, Date.now().toString());
  document.getElementById('pinScreen').style.display = 'none';
}
```

After Phase 5, the cache key should use `org_token` instead of `org_id` (since the URL is now token-based and org_id is no longer in the URL).

[VERIFIED: codebase read — kiosk.html lines 233-298]

### Existing section header comment style (CLAUDE.md convention)

```python
# ─── New route section ────────────────────────────────────────────────────────
```

### Org settings PATCH endpoint — what currently exists vs what needs to change

```python
# CURRENT (app.py line 546-562) — stores plaintext PIN:
if "kiosk_pin" in data:
    pin = data["kiosk_pin"]
    if pin and (len(str(pin)) != 4 or not str(pin).isdigit()):
        return jsonify({"error": "PIN должен быть 4-значным числом"}), 400
    orgs[org_id]["kiosk_pin"] = str(pin) if pin else None  # PLAINTEXT — must change

# REQUIRED for Phase 5 — store bcrypt hash:
if "kiosk_pin" in data:
    pin = str(data["kiosk_pin"]).strip() if data["kiosk_pin"] else ""
    if pin and (len(pin) != 4 or not pin.isdigit()):
        return jsonify({"error": "PIN должен быть 4-значным числом"}), 400
    orgs[org_id]["kiosk_pin"] = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode() if pin else None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plaintext PIN storage (Phase 2) | bcrypt-hashed PIN storage (Phase 5) | This phase | Phase 5 migrate.py must detect and re-hash existing plaintext PINs |
| URL uses org UUID (/kiosk/<org_id>) | URL uses opaque token (/kiosk/<org_token>) | This phase | Old kiosk URLs become invalid; the route parameter changes |
| Register page is auth-gated | Register page is token-gated (public) | This phase | Old `/register` stays for admin use; `/register/<reg_token>` is new |
| <input type="password"> PIN entry (keyboard) | <button> grid PIN entry (no keyboard) | This phase | Touchscreen devices no longer get a software keyboard popup |

**Deprecated/outdated after Phase 5:**
- `/kiosk/<org_id>` route: replaced by `/kiosk/<org_token>`. Old route must be removed to avoid Flask routing ambiguity.
- `/api/kiosk/<org_id>/verify_pin`: replaced by `/api/kiosk/<org_token>/verify_pin`. Old endpoint must be removed.
- Plaintext `kiosk_pin` storage in orgs.json: replaced by bcrypt hash.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dept_manager` in CONTEXT.md is intended as a rename of the existing `dept_admin` role string | Open Questions | If `dept_admin` is kept, all references to `dept_manager` in new nav/header code will fail for existing users; if renamed, existing user record needs migration |
| A2 | The touchscreen PIN pad should auto-submit after 4 digits (same as existing behavior) | Pattern 3 | User may want explicit OK button; auto-submit is more kiosk-friendly |
| A3 | `/register` (admin face registration) should be kept alongside new `/register/<reg_token>` | Pitfall 3 | If admin registration page is to be removed entirely, different plan structure needed |
| A4 | The 8-hour PIN session cache (localStorage) should use `org_token` as the cache key suffix after Phase 5 | Code Examples | If org_id is used, the cache key is valid but not derived from the visible URL |

---

## Open Questions

1. **`dept_manager` vs `dept_admin` role string**
   - What we know: CONTEXT.md says "dept_manager"; app.py ROLE_HIERARCHY uses "dept_admin"; one user in users.json has `role: "dept_admin"`
   - What's unclear: Does Phase 5 rename the role string from `dept_admin` to `dept_manager` (requiring a data migration of users.json and all `@require_role` calls), or does `dept_manager` mean `dept_admin` is retained as-is and only `viewer` and `employee` are removed from allowed login roles?
   - Recommendation: The planner should treat `dept_manager` as a label that maps to the existing `dept_admin` role string (no rename), and interpret "dept_manager only" as meaning: remove `viewer` and `employee` roles from allowed login. This avoids a data migration and keeps all existing `@require_role("dept_admin")` decorators working. **Planner must confirm with the user if a rename is intended.**

2. **Does the old `/kiosk/<org_id>` route remain as a redirect?**
   - What we know: Existing route uses org UUID as the URL parameter; Phase 5 wants org_token
   - What's unclear: Should `/kiosk/<org_id>` redirect to `/kiosk/<org_token>` for backward compatibility, or be removed entirely?
   - Recommendation: Remove the old route. The route pattern is identical (`/kiosk/<variable>`) so Flask cannot serve both simultaneously. Any existing bookmarks to `/kiosk/<org_id>` will 404, which is acceptable since the URL scheme is being redesigned.

3. **admin `/register` page access in the new org_admin flow**
   - What we know: `org_admin.html` has a tab "Регистрация →" linking to `/register` (the auth-gated admin registration page)
   - What's unclear: Should org_admin still access the admin `/register` page after Phase 5, or only via the token-based `/register/<reg_token>` URL they manage?
   - Recommendation: Keep `/register` for authenticated admins (org_admin, superadmin, dept_admin can still add employees via admin UI). Token-based `/register/<reg_token>` is a separate, employee-facing flow.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 venv | All routes, migrate.py | ✓ | 3.14.4 | — |
| `bcrypt` package | PIN hashing | ✓ | 5.0.0 | — |
| `secrets` module | Token generation | ✓ | stdlib | — |
| PM2 process manager | Deployment | ✓ | active (port 5051) | — |
| `data/orgs.json` | migrate.py | ✓ | 2 orgs present | — |
| `data/users.json` | Login validation | ✓ | 4 users | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed — tests/ directory exists with conftest.py) |
| Config file | none (pytest discovers tests/ automatically) |
| Quick run command | `/var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `/var/www/sites/face-almgp33/venv/bin/python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KIOSK-TOKEN-01 | GET /kiosk/<valid_token> returns 200 with kiosk template | integration | `pytest tests/test_kiosk_token.py::test_valid_org_token -x` | ❌ Wave 0 |
| KIOSK-TOKEN-02 | GET /kiosk/<invalid_token> returns 404 | integration | `pytest tests/test_kiosk_token.py::test_invalid_org_token -x` | ❌ Wave 0 |
| KIOSK-TOKEN-03 | POST /api/kiosk/<token>/verify_pin with correct bcrypt-hashed PIN returns {verified: true} | integration | `pytest tests/test_kiosk_token.py::test_verify_pin_correct -x` | ❌ Wave 0 |
| KIOSK-TOKEN-04 | POST /api/kiosk/<token>/verify_pin with wrong PIN returns 401 | integration | `pytest tests/test_kiosk_token.py::test_verify_pin_wrong -x` | ❌ Wave 0 |
| REG-TOKEN-01 | GET /register/<valid_token> (not expired) returns 200 | integration | `pytest tests/test_reg_token.py::test_valid_reg_token -x` | ❌ Wave 0 |
| REG-TOKEN-02 | GET /register/<expired_token> returns 410 or error page | integration | `pytest tests/test_reg_token.py::test_expired_reg_token -x` | ❌ Wave 0 |
| REG-TOKEN-03 | GET /register/<invalid_token> returns 404 | integration | `pytest tests/test_reg_token.py::test_invalid_reg_token -x` | ❌ Wave 0 |
| MIG-TOKEN-01 | migrate.py adds org_token/reg_token/kiosk_pin(bcrypt)/reg_pin(bcrypt)/kiosk_display_name to all orgs | unit | `pytest tests/test_migrate_tokens.py::test_migrate_adds_all_fields -x` | ❌ Wave 0 |
| MIG-TOKEN-02 | migrate.py re-hashes existing plaintext kiosk_pin values | unit | `pytest tests/test_migrate_tokens.py::test_migrate_rehashes_plaintext -x` | ❌ Wave 0 |
| MIG-TOKEN-03 | migrate.py is idempotent (re-run does not change already-set fields) | unit | `pytest tests/test_migrate_tokens.py::test_migrate_idempotent -x` | ❌ Wave 0 |
| AUTH-ROLE-01 | Login with role "viewer" is rejected after Phase 5 role restriction | integration | `pytest tests/test_auth.py::test_viewer_login_rejected -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_kiosk_token.py` — covers KIOSK-TOKEN-01 through 04
- [ ] `tests/test_reg_token.py` — covers REG-TOKEN-01 through 03
- [ ] `tests/test_migrate_tokens.py` — covers MIG-TOKEN-01 through 03
- [ ] `tests/test_auth.py` — extend with AUTH-ROLE-01 (viewer login rejection)

---

## Security Domain

> `security_enforcement: true`, ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | bcrypt.checkpw for PIN verification; no plaintext PIN comparison |
| V3 Session Management | partial | PIN unlock cached in localStorage (8h); not a user session; acceptable for kiosk use |
| V4 Access Control | yes | Token lookup must fail closed (404 on unknown token); expired reg_token must be rejected |
| V5 Input Validation | yes | PIN: validate `len(pin) == 4 and pin.isdigit()` before bcrypt; token: Flask URL routing handles format |
| V6 Cryptography | yes | bcrypt for PIN hashing (already used); `secrets.token_hex` for token generation (CSPRNG) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Guessing org_token (brute-force kiosk URL) | Information Disclosure | 8-char hex token = 2^32 space; no lockout required for v1 but tokens are not secret (kiosk URL is shared) |
| PIN brute-force on kiosk endpoint | Tampering | No lockout for v1 (per CONTEXT.md deferred); bcrypt slowness provides natural rate limiting (~250ms/attempt) |
| Expired reg_token still accessible | Elevation of Privilege | Server-side expiry check in `/register/<reg_token>` route; client cannot bypass |
| Plaintext PIN storage migration gap | Information Disclosure | migrate.py must detect and re-hash plaintext `kiosk_pin` values before Phase 5 goes live |
| org_token collision | Tampering | Uniqueness checked at generation time in migrate.py and at `POST /api/orgs` creation |
| localStorage PIN cache theft | Information Disclosure | localStorage key stores only a timestamp (not the PIN); acceptable risk for kiosk devices |

---

## Sources

### Primary (HIGH confidence)
- `app.py` codebase — all route definitions, bcrypt usage patterns, JSON helpers, existing kiosk_org and verify_pin implementations (lines 227-237, 546-562, 565-577)
- `data/orgs.json` — actual field names and current values (including plaintext kiosk_pin discovery)
- `data/users.json` — actual role values in production data
- `templates/kiosk.html` — existing PIN screen implementation, JS localStorage cache pattern
- Python stdlib `secrets` module — confirmed token_hex(4) produces 8 hex chars via runtime test

### Secondary (MEDIUM confidence)
- `.planning/phases/05-token-based-kiosk-registration-russian-ui/05-CONTEXT.md` — locked decisions and spec
- `.planning/ROADMAP.md` — Phase 5 requirements list
- `migrate.py` — existing migration pattern and _save_json/_load_json helpers to reuse

### Tertiary (LOW confidence)
- [ASSUMED] touchscreen PIN pad auto-submit behavior preference
- [ASSUMED] `dept_manager` vs `dept_admin` role naming resolution

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all patterns confirmed from codebase
- Architecture: HIGH — existing routes and data structures confirmed by direct file reading
- Pitfalls: HIGH — most discovered by reading actual production data (plaintext PIN, route conflict)
- Role naming ambiguity: LOW — requires planner/user confirmation

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable stack; main risk is if Phase 2 execution changes orgs.json schema further)
