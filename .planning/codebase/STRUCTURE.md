# Directory Structure

**Mapped:** 2026-06-11

---

## Layout

```
/var/www/sites/face-almgp33/
├── app.py                     # Main Flask application (~423 lines)
├── templates/
│   ├── kiosk.html             # Attendance kiosk interface (camera + recognition)
│   ├── register.html          # Employee registration + face capture
│   ├── admin.html             # Attendance reports + CSV export
│   └── login.html             # Admin authentication
├── data/
│   ├── config.json            # Admin credentials (hashed)
│   ├── employees.json         # Employee records array
│   ├── attendance.json        # Daily check-in/out records
│   ├── logs.json              # Audit trail (capped at ~10k entries)
│   └── faces/
│       └── {emp_id}/          # Per-employee face sample directory
│           ├── face_1.jpg
│           ├── face_2.jpg
│           └── ...            # Up to 10 samples per employee
├── .claude/                   # Claude Code / GSD configuration
│   └── gsd-core/              # GSD workflow engine
├── .planning/                 # GSD planning artifacts
│   └── codebase/              # This codebase map
└── README.md                  # Project documentation
```

---

## Key File Locations

| File | Purpose |
|------|---------|
| `app.py` | Everything: routes, CV logic, data helpers, auth |
| `templates/kiosk.html` | Primary user-facing interface; polls `/api/recognize` |
| `templates/admin.html` | Admin dashboard; CSV export; attendance view |
| `data/employees.json` | Source of truth for employee records |
| `data/attendance.json` | Daily attendance state per employee |
| `data/faces/{id}/` | Face training images; presence required before recognition |

---

## Naming Conventions

**Employee IDs:** Timestamp-based millisecond integers (e.g. `1781154410853`). Generated at creation time. Not sequential — deletion leaves gaps.

**Face files:** `face_1.jpg` through `face_10.jpg` under `data/faces/{emp_id}/`. Fixed filename scheme.

**Routes:**
- Pages: `/`, `/login`, `/register`, `/admin`
- API: `/api/recognize`, `/api/employees`, `/api/register_face`, `/api/attendance`

**Python:** `snake_case` for functions and variables. JSON helpers follow `load_{noun}()` / `save_{noun}()` pattern.

**JavaScript:** `camelCase` in template `<script>` blocks. No external JS files — all frontend logic is inline.

---

## Where to Add New Code

| Need | Where |
|------|-------|
| New page | Add `.html` to `templates/`, add route in `app.py` |
| New API endpoint | Add `@app.route` in `app.py`, use existing data helpers |
| New data schema | Extend JSON objects in `data/`, add `load_*/save_*` helpers |
| New frontend logic | Add JS in template `<script>` tags |

---
*Last mapped: 2026-06-11*
