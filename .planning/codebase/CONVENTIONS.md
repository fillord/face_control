# Coding Conventions

**Analysis Date:** 2026-06-11

## Naming Patterns

**Files:**
- Python: snake_case (`app.py`)
- HTML: lowercase with hyphens (`kiosk.html`, `admin.html`, `register.html`, `login.html`)
- Directories: snake_case (`data/`, `templates/`, `faces/`)

**Functions (Python):**
- snake_case for all functions: `load_employees()`, `save_config()`, `train_recognizer()`, `append_log()`
- Decorator names also snake_case: `login_required()`
- Private helpers prefixed with underscore (none observed in current codebase, all functions are public)

**Variables (Python):**
- snake_case for variables: `emp_id`, `emp_dir`, `recognizer_trained`, `cooldown_until`
- CONSTANT_CASE for module-level constants: `FACES_DIR`, `EMPLOYEES_FILE`, `ATTENDANCE_FILE`, `LOGS_FILE`, `CONFIG_FILE`, `COOLDOWN_MS`, `TARGET_PHOTOS`
- File paths: constructed using `os.path.join()` throughout

**Functions (JavaScript):**
- camelCase for all functions: `startCamera()`, `addEmployee()`, `capturePhoto()`, `loadEmployees()`, `updateQualityBadge()`, `showToast()`, `colorFor()`, `initials()`
- Event handlers: `onclick` attributes use camelCase function references

**Variables (JavaScript):**
- camelCase for all variables: `scanning`, `cooldownUntil`, `hasEmployees`, `currentFaceCount`, `detectInterval`, `empId`, `vw`, `vh`
- CONSTANT_CASE for module-level constants: `COOLDOWN_MS`, `TARGET_PHOTOS`, `COLORS`
- HTML element IDs: lowercase with hyphens: `empSelect`, `captureBtn`, `qualityBadge`, `progressLabel`, `samplesRow`

**Types (Python):**
- No type hints used in `app.py`
- Data stored in dictionaries with string keys: `employees[emp_id]`, `attendance[today]`

**CSS Classes:**
- kebab-case: `.status-chip`, `.employee-card`, `.progress-bar`, `.quality-badge`, `.log-item`, `.emp-avatar`, `.time-val`
- State classes use modifiers: `.active`, `.visible`, `.pulse`, `.good`, `.ok`, `.done`, `.in-event`, `.out-event`, `.late`

## Code Style

**Formatting:**
- No automated formatter configured (no `.prettierrc`, `pyproject.toml`, or `setup.cfg`)
- Indentation: 2 spaces for JavaScript, 4 spaces for Python (follows Python convention from `app.py`)
- Line breaks: Functions separated by 2-3 blank lines, sections separated by horizontal comment dividers (e.g., `# ─── Config / Auth ────────`)

**Linting:**
- No linter configuration found (no `.eslintrc`, `.flake8`, or `biome.json`)
- Code follows basic PEP 8-like conventions but not enforced
- JavaScript follows no strict linting rules

**Comment Dividers:**
- Section headers use Unicode box-drawing characters: `# ─── Section Name ───────────────────`
- Provides visual structure in `app.py` and HTML `<script>` blocks

## Import Organization

**Python imports (`app.py`):**
1. Standard library imports first: `os`, `json`, `base64`, `time`, `shutil`
2. Datetime imports: `datetime`, `date`
3. Utility imports: `functools.wraps`
4. Flask imports: `Flask`, `request`, `jsonify`, etc.
5. Third-party scientific/CV: `numpy`, `cv2`, `bcrypt`

All imports at top of file, line 1-7.

**JavaScript imports:**
- No module imports (no `import` statements)
- CDN libraries loaded in `<script src>` tags:
  - Chart.js for statistics visualization (`admin.html` line 7)
- Inline scripts in `<script>` blocks after HTML body
- No separation of concerns into modules; all code inline per page

**Path Aliases:**
- No path aliases configured
- Files referenced relatively: `../../app.py` would be relative to templates

## Error Handling

**Python patterns:**
- Try/except blocks used for file I/O and image decoding:
  ```python
  try:
      logs = json.load(f)
  except Exception:
      logs = []
  ```
  (`append_log()` at line 76-79)

- Try/except for CV operations:
  ```python
  try:
      data = request.json
      img = decode_image(data["image"])
      ...
  except Exception:
      return jsonify({"face": False})
  ```
  (`detect_face_only()` at lines 246-260)

- Guard clauses for validation before processing:
  ```python
  if emp_id not in employees:
      return jsonify({"error": "Сотрудник не найден"}), 404
  ```
  (Common pattern in all `/api/employees/` endpoints)

- Returns use JSON responses with status codes: `jsonify({...}), 400` or `jsonify({...}), 404`

**JavaScript patterns:**
- Async/await with try/catch for fetch calls:
  ```javascript
  try {
      const resp = await fetch("/api/recognize", {...});
      const data = await resp.json();
      if (!resp.ok) { ... }
  } catch(e) {
      setStatus("error", "Ошибка соединения");
  }
  ```
  (Common in `kiosk.html` lines 271-302)

- Guard clauses for early returns:
  ```javascript
  if (!hasEmployees || scanning || Date.now() < cooldownUntil) return;
  ```
  (`recognize()` at line 266)

- Optional chaining and null coalescing:
  ```javascript
  rec?.check_in || "—"
  data.employee || {}
  ```

- UI-level error handling through status messages and toasts rather than throwing

## Logging

**Framework:** No logging library used. Application uses JSON files for audit trails.

**Patterns:**
- `append_log()` function writes structured event objects to `data/logs.json`
- Log format: `{"ts": ISO timestamp, "event": "check_in", "emp_id": "...", "name": "...", "confidence_raw": float, "confidence_pct": float}`
- Logs capped at 10,000 entries (oldest removed): `if len(logs) > 10000: logs = logs[-10000:]` (line 81-82)
- No console logging in production code
- Error responses include confidence metrics for debugging: `"confidence_raw": float(confidence)`

## Comments

**When to Comment:**
- Section headers using box-drawing dividers: `# ─── API: Recognition ─────────────────────────────────────`
- Inline comments explain non-obvious logic:
  ```python
  # LBPH: lower confidence = better. Threshold ~80. Convert to % (0–100 good to bad).
  conf_pct = max(0, min(100, round(100 - (confidence / 80 * 100))))
  ```
  (line 283-284)

- Comments for "setup only once" code:
  ```python
  """Detect face bbox without saving — used for live preview overlay."""
  ```
  (line 245)

**JSDoc/TSDoc:**
- Minimal use
- Function docstrings in Python: single line in triple quotes (line 245)
- JavaScript has no formal documentation comments

## Function Design

**Size:** 
- Small, focused functions (15–40 lines typical)
- Longest functions are API endpoints (`recognize()` 64 lines, `get_stats()` 49 lines)
- Helper functions extracted for reuse: `colorFor()`, `initials()`, `train_recognizer()`, `extract_face()`

**Parameters:**
- Flask route handlers accept minimal parameters (mostly from request context)
- Helper functions take 1–3 parameters
- Python uses positional arguments throughout
- JavaScript uses positional arguments and destructuring in some cases: `const {x, y, w, h} = max(faces, ...)`

**Return Values:**
- Python: Returns JSON objects via `jsonify()` for HTTP responses, tuples/dicts for internal helpers
- JavaScript: Async functions return Promises, synchronous functions return void or DOM elements
- Early returns used to avoid deep nesting (guard clauses)

## Module Design

**Exports:**
- Python: Single file `app.py` with all code (no modules)
- JavaScript: No module exports; all functions in global scope (inline `<script>` blocks)

**Barrel Files:**
- Not applicable; no module structure

**Global State:**
- Python: Module-level constants for file paths, file-backed state (no in-memory singletons)
- JavaScript: Module-level state variables in each HTML file:
  ```javascript
  let scanning = false;
  let cooldownUntil = 0;
  let currentFaceCount = 0;
  let detectInterval = null;
  ```
  (`register.html` lines 164-166)
- OpenCV cascade and recognizer stored as module globals in Python:
  ```python
  face_cascade = cv2.CascadeClassifier(...)
  recognizer = cv2.face.LBPHFaceRecognizer_create()
  recognizer_trained = False
  ```
  (lines 20-22)

**Design Approach:**
- Single monolithic Python file for simplicity
- One HTML template per page, each with embedded JavaScript
- Shared utilities (color generation, initials) duplicated across templates
- No cross-file imports for frontend code

---

*Convention analysis: 2026-06-11*
