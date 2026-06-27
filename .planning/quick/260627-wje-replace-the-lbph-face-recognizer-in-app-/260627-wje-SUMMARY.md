---
phase: 260627-wje
plan: 01
subsystem: face-recognition
tags: [dlib, face_recognition, embeddings, lbph-replacement, opencv, flask]

requires:
  - phase: face-recognition-core
    provides: Haar Cascade face detection, extract_face(), decode_image(), app.py structure

provides:
  - dlib 128-d ResNet face embeddings replacing LBPH recognizer
  - data/encodings.json per-employee embedding store
  - encode_and_store(), load_encodings(), save_encodings() helpers
  - train_recognizer() rewritten with migration of existing JPEG crops
  - PATCH /api/settings/face_match_tolerance superadmin route
  - Updated superadmin.html tolerance control (0.30-0.60)

affects: [face-recognition, kiosk, registration, superadmin-settings]

tech-stack:
  added: [dlib==20.0.1, face_recognition==1.3.0, cmake==4.3.4, Pillow==12.2.0]
  patterns:
    - Atomic numpy array rebuild for known_encodings (never mutate in place)
    - fcntl.flock LOCK_EX for encodings.json writes (single PM2 worker)
    - dlib location tuple format (top, right, bottom, left) from Haar bbox
    - Migration on train_recognizer() — re-encode stale employee JPEG counts

key-files:
  created: []
  modified:
    - app.py
    - templates/superadmin.html
    - requirements.txt
    - .gitignore

key-decisions:
  - "dlib 128-d embeddings replace LBPH; lower euclidean distance = better match (same lower-is-better semantics retained)"
  - "face_recognition_models/__init__.py patched in venv to replace pkg_resources with os.path (Python 3.14 compat)"
  - "known_encodings rebuilt atomically on each train_recognizer() call — never mutated in place to avoid race conditions"
  - "Existing JPEG crops (gray 200x200) re-encoded by treating entire image as face bbox (0, w, h, 0)"
  - "data/encodings.json and data/faces/ added to .gitignore as runtime-generated artifacts"

patterns-established:
  - "Pattern: encode_and_store(emp_id, color_img, bbox) — encode from full COLOR frame, dlib location from Haar bbox"
  - "Pattern: train_recognizer() performs migration + global rebuild atomically"

requirements-completed: [SWAP-RECOGNIZER, STORE-EMBEDDINGS, KEEP-HAAR, PRESERVE-API]

duration: 12min
completed: 2026-06-27
---

# Quick Task 260627-wje: Replace LBPH Face Recognizer Summary

**dlib 128-d ResNet embeddings replace OpenCV LBPH in app.py with automated JPEG migration, fcntl-guarded encodings.json store, and updated superadmin tolerance control (0.30-0.60)**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-27T18:37:10Z
- **Completed:** 2026-06-27T18:49:39Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Installed dlib 20.0.1 + face_recognition 1.3.0 into the project venv (built from source via pip cmake)
- Replaced cv2.face.LBPHFaceRecognizer entirely; recognize() now uses face_recognition.face_distance against known_encodings
- train_recognizer() migrates existing JPEG crops to 128-d embeddings on first run; subsequent runs sync stale entries
- New PATCH /api/settings/face_match_tolerance route (superadmin, validates 0.30-0.60); superadmin.html updated
- With production DB: (33, 128) known_encodings array built from 3 employees' stored face photos

## Task Commits

1. **Task 1: Install dlib + face_recognition** - `117cfa8` (chore)
2. **Task 2: Replace LBPH train/predict** - `35051a2` (feat)
3. **Task 3: Update superadmin tolerance UI** - `e693ad6` (feat)
4. **Gitignore runtime data** - `1bdff5d` (chore)

## Files Created/Modified
- `app.py` - Remove LBPH recognizer; add face_recognition + fcntl imports; new globals (known_encodings, known_labels, ENCODINGS_FILE); load_encodings/save_encodings/encode_and_store helpers; rewritten train_recognizer(); updated recognize(); new PATCH route; face_match_tolerance in init_config + superadmin_page
- `templates/superadmin.html` - Threshold card updated to tolerance range 0.30-0.60; JS saves to /api/settings/face_match_tolerance
- `requirements.txt` - Added dlib==20.0.1 and face_recognition==1.3.0
- `.gitignore` - Added data/encodings.json and data/faces/ as runtime artifacts

## Decisions Made
- face_recognition_models/__init__.py patched in-venv to use os.path instead of pkg_resources — the package uses pkg_resources which was removed from Python 3.14; patch uses __file__ to locate model .dat files
- Existing stored JPEGs are gray 200x200 crops; during migration the entire image is used as the face bbox `(0, w, h, 0)` since the crop already contains just the face
- known_encodings is rebuilt as a new np.ndarray on every train_recognizer() call (atomic swap of the global) to prevent partial reads during recognition
- Legacy /api/settings/lbph_threshold route left in place (harmless, backward-compatible)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] face_recognition_models pkg_resources incompatibility with Python 3.14**
- **Found during:** Task 1 (dlib + face_recognition install)
- **Issue:** face_recognition_models/__init__.py imports `from pkg_resources import resource_filename` but pkg_resources is not available in Python 3.14's stdlib; `import face_recognition` failed at runtime
- **Fix:** Patched the installed venv file to use `os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", filename)` instead
- **Files modified:** /var/www/sites/face-almgp33/venv/lib/python3.14/site-packages/face_recognition_models/__init__.py (venv file, not tracked in git)
- **Verification:** `import dlib, face_recognition; print('dlib', dlib.__version__); print('fr ok')` succeeds
- **Committed in:** 117cfa8 (Task 1 — requirements.txt change only; venv patch not in repo)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking)
**Impact on plan:** Necessary fix for Python 3.14 compatibility; no scope creep.

## Issues Encountered
- sudo unavailable for `apt-get install cmake`; used pip cmake package as fallback (plan's fallback path B) — worked correctly
- setuptools+wheel not pre-installed in venv, needed for dlib build backend; installed before dlib

## Known Stubs
None — all new code paths are fully wired.

## Threat Flags
None — no new network endpoints or auth paths beyond the PATCH /api/settings/face_match_tolerance route which mirrors the existing lbph_threshold route pattern with the same @require_role("superadmin") guard.

## User Setup Required
After merging: run `pm2 restart face-recognition` to load the new recognizer. On first startup, train_recognizer() will automatically migrate existing face JPEGs to embeddings and create data/encodings.json.

## Next Phase Readiness
- Recognition pipeline is production-ready; kiosk /api/recognize now uses dlib embeddings
- Existing employees with stored face photos will be auto-migrated on first pm2 restart
- New registrations will immediately encode to 128-d vectors via encode_and_store()

## Self-Check: PASSED
- app.py: modified and committed (35051a2, e693ad6)
- templates/superadmin.html: modified and committed (e693ad6)
- requirements.txt: modified and committed (117cfa8)
- .gitignore: modified and committed (1bdff5d)
- Compile check: py_compile.compile passes, no LBPHFaceRecognizer, face_distance present
- Embeddings verification: (33, 128) ndarray built from production DB face JPEGs

---
*Phase: 260627-wje*
*Completed: 2026-06-27*
