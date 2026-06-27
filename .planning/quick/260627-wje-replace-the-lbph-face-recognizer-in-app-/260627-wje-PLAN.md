---
phase: 260627-wje
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app.py
  - templates/superadmin.html
autonomous: true
requirements:
  - SWAP-RECOGNIZER
  - STORE-EMBEDDINGS
  - KEEP-HAAR
  - PRESERVE-API
user_setup: []

must_haves:
  truths:
    - "Kiosk /api/recognize still recognizes a registered employee and records attendance with the same JSON response keys"
    - "New face captures store a 128-d embedding under data/encodings.json"
    - "Existing employees become recognizable after a one-time re-encode of their stored face JPEGs (migration)"
    - "Unknown faces are rejected when euclidean distance >= face_match_tolerance"
    - "No cv2.face LBPH recognizer code remains in app.py"
    - "API contracts of /api/recognize, /api/detect, /api/register_face and the token capture_face route are unchanged"
  artifacts:
    - path: "app.py"
      provides: "face_recognition-based train/encode/recognize replacing LBPH"
      contains: "face_distance"
    - path: "data/encodings.json"
      provides: "per-employee 128-d embeddings store (created at runtime)"
    - path: "templates/superadmin.html"
      provides: "tolerance (0.30-0.60) settings control replacing the LBPH threshold control"
  key_links:
    - from: "app.py recognize()"
      to: "known_encodings"
      via: "face_recognition.face_distance"
      pattern: "face_distance\\(known_encodings"
    - from: "app.py capture routes"
      to: "data/encodings.json"
      via: "encode_and_store helper"
      pattern: "encodings\\.json"
    - from: "app.py train_recognizer()"
      to: "known_encodings / known_labels globals"
      via: "rebuild from encodings.json"
      pattern: "known_encodings"
---

<objective>
Replace the OpenCV LBPH face recognizer in app.py with dlib `face_recognition` 128-d
embeddings. Swap the LBPH train/predict calls for `face_recognition` encode/compare,
store embeddings in `data/encodings.json`, keep the existing Haar Cascade detector for
cropping and bbox, and preserve the cooldown/confidence logic and every existing API
contract.

Purpose: LBPH is low-accuracy and brittle; dlib ResNet embeddings are far more reliable
for the clinic kiosk while keeping the same request/response shapes.
Output: Updated app.py (embedding-based recognition), data/encodings.json (built at
runtime), and an updated superadmin settings control for the new tolerance value.
</objective>

<execution_context>
@/var/www/sites/face-almgp33/.claude/gsd-core/workflows/execute-plan.md
@/var/www/sites/face-almgp33/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/260627-wje-replace-the-lbph-face-recognizer-in-app-/260627-wje-RESEARCH.md
@app.py

Key existing locations (verified):
- Globals: app.py:81-83 (face_cascade, recognizer = cv2.face.LBPHFaceRecognizer_create(), recognizer_trained)
- CV helpers: app.py:621-636 (decode_image, extract_face — extract_face already returns bbox)
- train_recognizer(): app.py:638-660
- train_recognizer() call sites: app.py:994, 2746, 2844, 3131, 3162, 3533
- recognize(): app.py:3155-3290 (predict at 3174; threshold read 3176-3178; response 3280-3290)
- Token capture: register_token_capture_face app.py:955-995
- Admin capture: register_face app.py:3098-3132
- Settings: init_config app.py:93-102; update_lbph_threshold app.py:2982-3000
- superadmin_page passes lbph_threshold: app.py:1138-1141
- Startup app_context block: app.py:3498-3530; __main__ train: app.py:3533
- superadmin.html threshold card: lines 72-86; saveThreshold JS: lines 183-209
</context>

<tasks>

<task type="auto">
  <name>Task 1: Install dlib + face_recognition into the project venv</name>
  <files>app.py (no edit — install only)</files>
  <action>
Install the recognition dependencies into the project venv at
/var/www/sites/face-almgp33/venv. All three packages (dlib, face_recognition,
face_recognition_models) were verdict-OK / Approved in the RESEARCH.md Package
Legitimacy Audit, so no human legitimacy checkpoint is required.

dlib has NO cp314 wheel and must compile from source, which needs cmake + a C/C++
toolchain (gcc 15.2 is present; cmake is NOT installed). Try the system-cmake path
first: `sudo apt-get install -y cmake build-essential`. If apt/sudo is unavailable or
fails, use the pip fallback so dlib's setup.py finds cmake on PATH: install `cmake` into
the venv first, then install dlib with `--no-build-isolation`. Concretely, attempt in
order: (a) apt install cmake build-essential, then
`/var/www/sites/face-almgp33/venv/bin/pip install dlib face_recognition`; (b) on failure,
`/var/www/sites/face-almgp33/venv/bin/pip install cmake` then
`/var/www/sites/face-almgp33/venv/bin/pip install --no-build-isolation dlib face_recognition`.
The dlib build takes ~2-4 min and ~2 GB RAM — allow a long timeout. `face_recognition_models`
is pulled in automatically by `face_recognition`.

If a `requirements.txt` exists at the repo root, append `dlib` and `face_recognition`
pins matching the installed versions; if it does not exist, do not create one.
  </action>
  <verify>
    <automated>/var/www/sites/face-almgp33/venv/bin/python -c "import dlib, face_recognition; print('dlib', dlib.__version__); print('fr ok')"</automated>
  </verify>
  <done>`import dlib` and `import face_recognition` both succeed in the project venv and print versions.</done>
</task>

<task type="auto">
  <name>Task 2: Replace LBPH train/predict with face_recognition embeddings in app.py</name>
  <files>app.py</files>
  <action>
Swap the recognition core to dlib embeddings while preserving every API contract and the
existing cooldown/confidence control flow (lower-is-better holds for both LBPH and dlib).

1. Imports/globals (app.py:81-83): add `import face_recognition` near the cv2 import.
   Remove the `recognizer = cv2.face.LBPHFaceRecognizer_create()` line. Keep `face_cascade`.
   Add module globals: `known_encodings = None` (an np.ndarray of shape (N,128) or None) and
   `known_labels = []` (a list of int Employee.label values, aligned row-for-row with
   known_encodings). Keep the existing `recognizer_trained` boolean as the "have encodings"
   guard used by recognize(). Add `ENCODINGS_FILE = os.path.join(DATA_DIR, "encodings.json")`.

2. Encodings storage helpers. Add `load_encodings()` returning the JSON dict
   `{ "<emp_id>": [[128 floats], ...one list per stored photo...] }` (empty dict if the file
   is missing). Add `save_encodings(d)` that writes JSON guarded by fcntl.flock LOCK_EX, the
   same single-writer pattern the project uses for other data/ writes (single PM2 worker
   constraint). Add `encode_and_store(emp_id, color_img, bbox)`: convert BGR->RGB with
   cv2.cvtColor, build the dlib location tuple `(y, x+w, y+h, x)` from bbox, call
   `face_recognition.face_encodings(rgb, known_face_locations=[loc])`, guard `if not encs:`
   (return False — no face), append `encs[0].tolist()` to the emp_id list in encodings.json,
   persist, and return True. Always encode from the COLOR frame (not the gray 200x200 crop) —
   dlib needs 8-bit RGB and aligns via landmarks (RESEARCH Pitfall 2).

3. Rewrite train_recognizer() (app.py:638-660) — keep the same function name so all five call
   sites (994, 2746, 2844, 3131, 3162, 3533) stay valid. New behavior: (a) build/sync
   encodings.json from data/faces/<emp_id>/*.jpg — for any employee whose stored encoding count
   does not match its JPEG count, re-encode that employee's JPEGs. The stored JPEGs are gray
   200x200 tight crops, so encode each via `cv2.imread` -> BGR->RGB -> `face_encodings(rgb,
   known_face_locations=[(0, 200, 200, 0)])` (force the whole crop as the face box). This is the
   one-time migration of existing data — there is NO on-disk LBPH model to migrate. (b) Build a
   NEW np.ndarray for known_encodings and a NEW known_labels list from encodings.json (map each
   emp_id to its Employee.label), then atomically reassign the globals (build new, then assign —
   never mutate in place, RESEARCH Pitfall 5). Set `recognizer_trained = True` when at least one
   encoding exists, else False. Return the boolean.

4. Capture paths. In register_token_capture_face (app.py:955-995) and register_face
   (app.py:3098-3132): after `cv2.imwrite` of the cropped jpeg and the face_count commit, call
   `encode_and_store(emp_id, img, bbox)` using the COLOR `img` already returned by decode_image
   and the `bbox` from extract_face, BEFORE the existing `train_recognizer()` call. Keep writing
   the cropped jpeg (audit/preview) and keep the existing train_recognizer() call so the globals
   reload. Preserve the existing JSON responses unchanged.

5. recognize() (app.py:3155-3290). Replace `label, confidence = recognizer.predict(face_roi)`
   (line 3174) with the embedding path: cvtColor the color `img` to RGB, build loc
   `(y, x+w, y+h, x)` from bbox, `q = face_recognition.face_encodings(rgb,
   known_face_locations=[loc])`, guard `if not q: return jsonify({"error": "no_face"}), 400`.
   Compute `dists = face_recognition.face_distance(known_encodings, q[0])`,
   `best_idx = int(np.argmin(dists))`, `confidence = float(dists[best_idx])` (keep the variable
   name `confidence`), `label = known_labels[best_idx]`. Replace the threshold block
   (3176-3178): read a NEW AppSetting key `face_match_tolerance` (float, default 0.6) instead of
   lbph_threshold; `tolerance = float(value)`; `conf_pct = max(0, min(100, round((1 -
   confidence / tolerance) * 100)))`. Keep the reject branch shape but flip to the dlib scale:
   `if confidence > tolerance:` log "unknown" and return the same 400 "unknown" JSON. Leave the
   downstream `Employee.query.filter_by(label=label)` lookup, the org_id filter, device-auth
   check, attendance state machine, append_log call, and the final response dict (keys
   confidence, confidence_pct, bbox, employee, event, record, is_late, dept_name) completely
   unchanged. The lazy-train guard at 3161-3164 stays as-is.

6. Settings. In init_config (app.py:93-102) add a bootstrap row for `face_match_tolerance`
   default `"0.6"` if absent (keep the existing lbph_threshold bootstrap). Add a new route
   `PATCH /api/settings/face_match_tolerance` (mirror update_lbph_threshold at 2982-3000,
   @require_role("superadmin")) validating a float in [0.30, 0.60] and persisting it as a string;
   return `{"status": "updated", "value": <float>}`. Leave the existing
   /api/settings/lbph_threshold route in place (harmless legacy).
  </action>
  <verify>
    <automated>/var/www/sites/face-almgp33/venv/bin/python -c "import py_compile,sys; py_compile.compile('app.py', doraise=True); src=open('app.py').read(); assert 'LBPHFaceRecognizer' not in src, 'LBPH remains'; assert 'face_distance(known_encodings' in src, 'no face_distance'; assert 'encodings.json' in src or 'ENCODINGS_FILE' in src, 'no encodings store'; assert 'face_match_tolerance' in src, 'no tolerance setting'; print('ok')"</automated>
  </verify>
  <done>app.py compiles; no LBPHFaceRecognizer reference remains; recognize() uses face_distance against known_encodings; capture routes call encode_and_store; face_match_tolerance setting and route exist.</done>
</task>

<task type="auto">
  <name>Task 3: Update superadmin tolerance UI and verify end-to-end encoding</name>
  <files>templates/superadmin.html, app.py</files>
  <action>
Point the superadmin settings UI at the new tolerance value and confirm the recognition
pipeline builds embeddings end-to-end.

1. superadmin_page route (app.py:1138-1141): read the `face_match_tolerance` AppSetting
   (float, default 0.6) and pass it to the template as `face_match_tolerance`. You may keep
   passing lbph_threshold too, but the template will no longer use it.

2. templates/superadmin.html threshold card (lines 72-86): change the heading and helper text
   to describe the dlib tolerance (Russian, e.g. "Порог распознавания (точность)"; explain that
   lower = stricter; range 0.30-0.60, default 0.60). Change the input to `step="0.05"`,
   `min="0.30"`, `max="0.60"`, value `{{ face_match_tolerance|default(0.6) }}`. Update the
   saveThreshold JS (lines 183-209): parse the value with parseFloat, validate the 0.30-0.60
   range, and POST to `/api/settings/face_match_tolerance` instead of `/api/settings/lbph_threshold`.
   Keep the existing message/element ids so the rest of the script is untouched.

3. Final verification: importing app triggers the startup app_context (db.create_all on the
   existing data/app.db). Run train_recognizer() inside an app context to encode the existing
   face JPEGs (migration) and confirm data/encodings.json is created and known_encodings is a
   populated np.ndarray. Use the verify command below.
  </action>
  <verify>
    <automated>cd /var/www/sites/face-almgp33 && SECRET_KEY=verify-test /var/www/sites/face-almgp33/venv/bin/python -c "import app, numpy as np, os; \
[app.train_recognizer() for _ in [0]] if app.app else None; \
ctx=app.app.app_context(); ctx.push(); app.train_recognizer(); ctx.pop(); \
assert os.path.isfile('data/encodings.json'), 'encodings.json not created'; \
assert app.known_encodings is not None and getattr(app.known_encodings,'shape',(0,))[0] > 0, 'no embeddings built'; \
print('encodings shape', app.known_encodings.shape)"</automated>
  </verify>
  <done>superadmin.html drives /api/settings/face_match_tolerance with a 0.30-0.60 control; running train_recognizer() builds data/encodings.json and a non-empty known_encodings array from existing face JPEGs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pip install → venv | dlib/face_recognition pulled from PyPI (supply chain) |
| kiosk client → /api/recognize | untrusted base64 image crosses into the encoder |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-wje-SC | Tampering | pip install dlib / face_recognition / face_recognition_models | mitigate | RESEARCH.md Package Legitimacy Audit verdict-OK / Approved for all three (long-established, high-download, known authors); no [ASSUMED]/[SUS] packages so no blocking-human checkpoint required |
| T-wje-01 | Denial of Service | /api/recognize image decode + face_encodings | accept | kiosk route is already public and Haar-gated; encoding cost is bounded per request; existing single-worker + cooldown constraints unchanged |
| T-wje-02 | Spoofing | recognize() match accept threshold | mitigate | face_match_tolerance default 0.6 with distance < tolerance match rule; superadmin can tighten to 0.30 via the settings control |
</threat_model>

<verification>
- `import dlib, face_recognition` succeed in the venv (Task 1).
- `grep`-free assert confirms no LBPHFaceRecognizer remains and face_distance/encodings.json/face_match_tolerance are present (Task 2).
- train_recognizer() builds data/encodings.json and a non-empty known_encodings ndarray from existing face JPEGs (Task 3).
- API response keys of /api/recognize are preserved (confidence, confidence_pct, bbox, employee, event, record, is_late, dept_name) — verified by inspecting the unchanged response dict.
</verification>

<success_criteria>
- LBPH code fully removed; recognition runs on dlib 128-d embeddings.
- New captures append a 128-d embedding to data/encodings.json; existing faces re-encoded once (migration).
- Unknown faces rejected when euclidean distance >= face_match_tolerance.
- All existing kiosk/registration/recognition API contracts unchanged.
- Superadmin settings control drives the new face_match_tolerance value.
- After completion run `pm2 restart face-recognition` to load the new recognizer.
</success_criteria>

<output>
Create `.planning/quick/260627-wje-replace-the-lbph-face-recognizer-in-app-/260627-wje-SUMMARY.md` when done.
</output>
