<!-- GSD:project-start source:PROJECT.md -->

## Project

**Face Recognition Attendance System — Role & Timesheet Extension**

A brownfield extension of an existing Flask + OpenCV face recognition attendance system. The extension adds multi-level role-based access control, organizational/departmental data isolation, and a T-13 timesheet with Excel/CSV export. The kiosk (public face check-in) remains unchanged; the new system layers HR management, reporting, and employee self-service on top.

**Core Value:** Department heads and HR staff can view, manage, and export attendance data for exactly the employees they are authorized to see — no more, no less.

### Constraints

- **Tech stack**: Flask + Python, no framework migration — extend in place
- **Storage**: JSON files in `data/` — no DB migration for v1
- **Python**: 3.14.4 on venv, openpyxl available via pip
- **Deployment**: PM2 manages the process; final step is `pm2 restart face-recognition`
- **Isolation**: Data isolation must be enforced server-side, not just hidden in UI

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.14.4 - Server-side application logic, face recognition, and API
- JavaScript (Vanilla) - Frontend interactivity, WebRTC camera access, real-time UI
- HTML5 - Page structure with Jinja2 templating
- CSS3 - Styling with CSS Grid and Flexbox
- JSON - Configuration and data storage format

## Runtime

- Python 3.14.4 (from `/var/www/sites/face-almgp33/venv/bin/python`)
- pip 25.1.1
- Lockfile: Not detected (using venv with installed packages list available)

## Frameworks

- Flask 3.1.3 - Web framework for HTTP routing, request handling, and session management (`app.py`)
- Jinja2 3.1.6 - Template engine for rendering HTML with dynamic data (`templates/`)
- OpenCV (opencv-contrib-python 4.13.0.92) - Face detection using Haar Cascades and LBPH face recognition (`app.py` lines 20-22, 105-127)
- Not detected
- gunicorn 26.0.0 - Production WSGI application server (referenced in README.md)

## Key Dependencies

- opencv-contrib-python 4.13.0.92 - Face detection and recognition using Cascade Classifier and LBPH (Local Binary Pattern Histograms) algorithm
- numpy 2.4.6 - Array operations for image processing
- Flask 3.1.3 - Web server and routing
- bcrypt 5.0.0 - Password hashing for admin authentication
- Werkzeug 3.1.8 - WSGI utilities (Flask dependency)
- Jinja2 3.1.6 - Template rendering
- click 8.4.1 - CLI framework (Flask dependency)
- blinker 1.9.0 - Signal support (Flask dependency)
- itsdangerous 2.2.0 - Data signing for session management
- MarkupSafe 3.0.3 - Safe string handling

## Configuration

- Flask secret key: Configured via `SECRET_KEY` environment variable or hardcoded default in `app.py` line 10
- File-based storage: No database - all data persists in JSON files in `data/` directory
- Application port: 5050 (default) or configurable at runtime
- No build configuration needed - pure Python/HTML/CSS/JavaScript stack
- Development: Flask built-in server with `debug=True`
- Production: gunicorn WSGI server (see README.md lines 80-84)

## Platform Requirements

- Python 3.8+ (official requirement per README.md)
- Webcam with browser MediaDevices API support
- Modern browser with WebRTC support (Chrome, Firefox, Edge)
- Linux/Unix server (PM2 process manager referenced in project memory)
- Port 5050 exposed for HTTP traffic
- Nginx reverse proxy recommended (see README.md line 76)
- File system with read/write permissions for `data/` and `data/faces/` directories

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Python: snake_case (`app.py`)
- HTML: lowercase with hyphens (`kiosk.html`, `admin.html`, `register.html`, `login.html`)
- Directories: snake_case (`data/`, `templates/`, `faces/`)
- snake_case for all functions: `load_employees()`, `save_config()`, `train_recognizer()`, `append_log()`
- Decorator names also snake_case: `login_required()`
- Private helpers prefixed with underscore (none observed in current codebase, all functions are public)
- snake_case for variables: `emp_id`, `emp_dir`, `recognizer_trained`, `cooldown_until`
- CONSTANT_CASE for module-level constants: `FACES_DIR`, `EMPLOYEES_FILE`, `ATTENDANCE_FILE`, `LOGS_FILE`, `CONFIG_FILE`, `COOLDOWN_MS`, `TARGET_PHOTOS`
- File paths: constructed using `os.path.join()` throughout
- camelCase for all functions: `startCamera()`, `addEmployee()`, `capturePhoto()`, `loadEmployees()`, `updateQualityBadge()`, `showToast()`, `colorFor()`, `initials()`
- Event handlers: `onclick` attributes use camelCase function references
- camelCase for all variables: `scanning`, `cooldownUntil`, `hasEmployees`, `currentFaceCount`, `detectInterval`, `empId`, `vw`, `vh`
- CONSTANT_CASE for module-level constants: `COOLDOWN_MS`, `TARGET_PHOTOS`, `COLORS`
- HTML element IDs: lowercase with hyphens: `empSelect`, `captureBtn`, `qualityBadge`, `progressLabel`, `samplesRow`
- No type hints used in `app.py`
- Data stored in dictionaries with string keys: `employees[emp_id]`, `attendance[today]`
- kebab-case: `.status-chip`, `.employee-card`, `.progress-bar`, `.quality-badge`, `.log-item`, `.emp-avatar`, `.time-val`
- State classes use modifiers: `.active`, `.visible`, `.pulse`, `.good`, `.ok`, `.done`, `.in-event`, `.out-event`, `.late`

## Code Style

- No automated formatter configured (no `.prettierrc`, `pyproject.toml`, or `setup.cfg`)
- Indentation: 2 spaces for JavaScript, 4 spaces for Python (follows Python convention from `app.py`)
- Line breaks: Functions separated by 2-3 blank lines, sections separated by horizontal comment dividers (e.g., `# ─── Config / Auth ────────`)
- No linter configuration found (no `.eslintrc`, `.flake8`, or `biome.json`)
- Code follows basic PEP 8-like conventions but not enforced
- JavaScript follows no strict linting rules
- Section headers use Unicode box-drawing characters: `# ─── Section Name ───────────────────`
- Provides visual structure in `app.py` and HTML `<script>` blocks

## Import Organization

- No module imports (no `import` statements)
- CDN libraries loaded in `<script src>` tags:
- Inline scripts in `<script>` blocks after HTML body
- No separation of concerns into modules; all code inline per page
- No path aliases configured
- Files referenced relatively: `../../app.py` would be relative to templates

## Error Handling

- Try/except blocks used for file I/O and image decoding:
- Try/except for CV operations:
- Guard clauses for validation before processing:
- Returns use JSON responses with status codes: `jsonify({...}), 400` or `jsonify({...}), 404`
- Async/await with try/catch for fetch calls:
- Guard clauses for early returns:
- Optional chaining and null coalescing:
- UI-level error handling through status messages and toasts rather than throwing

## Logging

- `append_log()` function writes structured event objects to `data/logs.json`
- Log format: `{"ts": ISO timestamp, "event": "check_in", "emp_id": "...", "name": "...", "confidence_raw": float, "confidence_pct": float}`
- Logs capped at 10,000 entries (oldest removed): `if len(logs) > 10000: logs = logs[-10000:]` (line 81-82)
- No console logging in production code
- Error responses include confidence metrics for debugging: `"confidence_raw": float(confidence)`

## Comments

- Section headers using box-drawing dividers: `# ─── API: Recognition ─────────────────────────────────────`
- Inline comments explain non-obvious logic:
- Comments for "setup only once" code:
- Minimal use
- Function docstrings in Python: single line in triple quotes (line 245)
- JavaScript has no formal documentation comments

## Function Design

- Small, focused functions (15–40 lines typical)
- Longest functions are API endpoints (`recognize()` 64 lines, `get_stats()` 49 lines)
- Helper functions extracted for reuse: `colorFor()`, `initials()`, `train_recognizer()`, `extract_face()`
- Flask route handlers accept minimal parameters (mostly from request context)
- Helper functions take 1–3 parameters
- Python uses positional arguments throughout
- JavaScript uses positional arguments and destructuring in some cases: `const {x, y, w, h} = max(faces, ...)`
- Python: Returns JSON objects via `jsonify()` for HTTP responses, tuples/dicts for internal helpers
- JavaScript: Async functions return Promises, synchronous functions return void or DOM elements
- Early returns used to avoid deep nesting (guard clauses)

## Module Design

- Python: Single file `app.py` with all code (no modules)
- JavaScript: No module exports; all functions in global scope (inline `<script>` blocks)
- Not applicable; no module structure
- Python: Module-level constants for file paths, file-backed state (no in-memory singletons)
- JavaScript: Module-level state variables in each HTML file:
- OpenCV cascade and recognizer stored as module globals in Python:
- Single monolithic Python file for simplicity
- One HTML template per page, each with embedded JavaScript
- Shared utilities (color generation, initials) duplicated across templates
- No cross-file imports for frontend code

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## Overview

## Layers

```

```

## Key Data Flows

### Recognition Flow (Kiosk)

### Registration Flow

## Entry Points

- **Web server:** `app.py` lines 420–423 (`app.run(...)`)
- **Kiosk UI:** `GET /` → `templates/kiosk.html`
- **Admin panel:** `GET /admin` (requires login) → `templates/admin.html`
- **Registration:** `GET /register` → `templates/register.html`

## Global State

- `recognizer` — OpenCV LBPH face recognizer, loaded at startup and after each training
- `face_cascade` — Haar cascade classifier for face detection, loaded at startup

## Abstractions

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
