# Quick Task: Replace LBPH with dlib face_recognition - Research

**Researched:** 2026-06-27
**Domain:** Face recognition (dlib 128-d embeddings) on Flask + Python 3.14
**Confidence:** MEDIUM-HIGH (install path is the main risk; swap pattern is HIGH)

## Summary

The swap is mechanically straightforward but has **one real blocker: dlib must compile from source on this box** (Python 3.14, x86_64). No prebuilt `dlib`/`dlib-bin` wheel exists for cp314 on PyPI, and **cmake is not installed** here (`gcc 15.2` is present). The build needs cmake + a C/C++ toolchain and ~2-4 min + ~2 GB RAM.

The recognition logic maps cleanly: LBPH `predict() -> (label, distance)` becomes `face_recognition.face_distance(known, query) -> distances`, both lower-is-better, so the existing cooldown/confidence/threshold structure is preserved with only the threshold *value* and the `conf_pct` formula changing. Embeddings should be stored as a JSON dict (`data/encodings.json`) to fit the project's JSON-first `data/` pattern.

**Primary recommendation:** Install via `apt install -y cmake build-essential` then `pip install dlib face_recognition`. Keep the existing Haar detector for cropping/preview (fast, low-power), feed its bbox to `face_encodings(..., known_face_locations=[...])` to skip dlib's slower HOG detection. Store one averaged or per-photo 128-d embedding per employee in `data/encodings.json`. Re-encode existing `data/faces/<emp_id>/*.jpg` once at deploy (the LBPH in-memory model becomes stale — there is no on-disk model file to migrate).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TASK | Swap LBPH train/predict for face_recognition encode/compare | Swap pattern + threshold mapping below |
| TASK | Store embeddings (JSON or numpy) | `data/encodings.json` list-of-lists — Embedding Storage section |
| TASK | Keep Haar or upgrade to DNN SSD | Keep Haar — Detector Choice section |
| TASK | Preserve cooldown/confidence logic + API contracts | `confidence`/`confidence_pct`/`bbox` fields preserved — Swap section |

## Standard Stack

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `dlib` | 20.0.1 (latest) [VERIFIED: pip index versions] | C++ ML lib providing the ResNet face encoder | **No cp314 wheel — builds from source, needs cmake** |
| `face_recognition` | 1.3.0 [VERIFIED: pip index versions] | Thin Python API over dlib (`face_encodings`, `face_distance`, `face_locations`) | **Unmaintained since 2020** — stable but no fixes [CITED: github.com/ageitgey/face_recognition] |
| `face_recognition_models` | 0.3.0 [VERIFIED: pip index versions] | Pretrained dlib model files (auto-pulled by face_recognition) | Now on PyPI (was git-only historically) |

Already present and reused: `opencv-contrib-python 4.13.0.92`, `numpy 2.4.6` [VERIFIED: pip list].

**Installation (recommended — system cmake):**
```bash
sudo apt-get install -y cmake build-essential
/var/www/sites/face-almgp33/venv/bin/pip install dlib face_recognition
```

**Fallback (no apt/sudo — pip cmake, non-isolated build so dlib's setup.py finds it on PATH):**
```bash
/var/www/sites/face-almgp33/venv/bin/pip install cmake
/var/www/sites/face-almgp33/venv/bin/pip install --no-build-isolation dlib face_recognition
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| dlib | PyPI | ~13 yrs | very high | github.com/davisking/dlib | OK | Approved |
| face_recognition | PyPI | ~9 yrs | very high | github.com/ageitgey/face_recognition | OK (unmaintained) | Approved — note staleness |
| face_recognition_models | PyPI | ~8 yrs | high | github.com/ageitgey/face_recognition_models | OK | Approved |

All three are long-established, widely-used packages from known authors. `face_recognition` is unmaintained (last release 2020) but functionally stable and pinned-compatible with dlib 20.

## Embedding Storage Format

**Recommendation: JSON dict `data/encodings.json`** — fits the JSON-first `data/` convention and is human-inspectable.

```json
{ "<emp_id>": [[0.123, -0.045, ...128 floats...], ...one list per stored photo...] }
```

- A 128-d `numpy` array converts via `enc.tolist()` and back via `np.array(list, dtype=np.float64)`.
- Per-photo lists (not a single average) preserve accuracy; `face_distance` compares against all and you take the min per employee. ~1 KB per photo — trivial for a clinic dataset.
- Avoid `pickle` (opaque, version-fragile) and `.npy` (binary, breaks the JSON-first audit pattern). [ASSUMED — based on project's documented JSON-first constraint]
- Guard writes the same way other `data/` writes are guarded (single PM2 worker + advisory locking is already a project constraint).

## Drop-in Swap Pattern

Lower-is-better holds for **both** LBPH and dlib, so the control flow barely changes.

### `train_recognizer()` (app.py:638)
Replace "load JPEGs + `recognizer.train()`" with "load/build `data/encodings.json` into an in-memory structure":
- Build two parallel module globals: `known_encodings` (a single `np.ndarray` of shape `(N,128)`) and `known_labels` (list of `emp_id` aligned by row). Replaces the `recognizer` global + `recognizer_trained` flag (keep a `recognizer_trained`-equivalent "have encodings" boolean for the lazy-train guard in `recognize()`).
- On a fresh box with no `encodings.json`, build it by encoding every `data/faces/<emp_id>/*.jpg` (migration, below).

### Capture path (`register_token_capture_face` :955, `register_face` :3100)
You already have the **color** `img` from `decode_image()` *before* `extract_face()` greyscales it. Encode from color for best quality:
```python
# Source: github.com/ageitgey/face_recognition (face_encodings API)
import face_recognition
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)          # face_recognition needs 8-bit RGB
x, y, w, h = bbox                                    # bbox already returned by extract_face()
loc = (y, x + w, y + h, x)                           # (top, right, bottom, left)
encs = face_recognition.face_encodings(rgb, known_face_locations=[loc])
if encs:
    # append encs[0].tolist() to data/encodings.json under emp_id, then persist
    ...
```
Keep writing the cropped JPEG too (audit/preview). Then refresh the in-memory arrays (call the new `train_recognizer()` equivalent, as the code does today).

### `recognize()` (app.py:3155-3187)
```python
# Replaces:  label, confidence = recognizer.predict(face_roi)
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
x, y, w, h = bbox
loc = (y, x + w, y + h, x)
q = face_recognition.face_encodings(rgb, known_face_locations=[loc])
if not q:
    return jsonify({"error": "no_face"}), 400
dists = face_recognition.face_distance(known_encodings, q[0])  # np array, lower=better
best_idx = int(np.argmin(dists))
confidence = float(dists[best_idx])      # keep the variable name 'confidence'
emp_id = known_labels[best_idx]          # map straight to emp_id (skip the label->Employee lookup,
                                         # or keep label parity by storing label instead)
```
Then keep the existing branch `if confidence > threshold: ... "unknown"` unchanged in shape. The JSON response keys `confidence`, `confidence_pct`, `bbox`, `employee`, `event`, `record`, `is_late`, `dept_name` are all preserved — **API contract intact**.

## Confidence / Threshold Mapping

| | LBPH (current) | dlib face_recognition (new) |
|---|---|---|
| Raw value | distance ~0-150+ | euclidean distance, typically 0.0-1.0 |
| Direction | lower = better | lower = better (same) |
| Match cutoff | `lbph_threshold` default **80** | tolerance default **0.6** [CITED: face-recognition.readthedocs.io] |
| `conf_pct` now | `100 - (confidence/threshold*100)` | `(1 - distance/tolerance)*100`, clamped 0-100 |

- Default tolerance **0.6** is the library's documented match cutoff; `< 0.6` = match. Lower = stricter. [CITED: github.com/ageitgey/face_recognition]
- The `AppSetting` key is currently `lbph_threshold` storing int `"80"`. **Add a new key** `face_match_tolerance` default `"0.6"` (float string) rather than reusing the int key — `superadmin.html` renders `lbph_threshold` as an int and `/api/settings/lbph_threshold` (app.py:2982) validates an int range. Leave the old key/route or repurpose the settings UI to a 0.30-0.60 slider. [ASSUMED — exact UI treatment is the implementer's call]
- `conf_pct` clamp formula: `max(0, min(100, round((1 - distance/tolerance) * 100)))`.

## Detector Choice: keep Haar

| Option | Speed on CPU | Verdict for low-power clinic server |
|--------|-------------|-------------------------------------|
| Haar (current, OpenCV) | fast | **Keep** — already works, powers `/api/detect` live preview |
| `face_locations(model="hog")` | slower than Haar, CPU-only | Optional; not worth the change |
| `face_locations(model="cnn")` | very slow without GPU | **Avoid** — no GPU here |

Keep Haar for both the live preview (`/api/detect` :3134 — unchanged) and for producing the bbox you pass into `face_encodings(known_face_locations=...)`. This avoids running a second detector and keeps `extract_face()` largely intact. Note: pass the **color** image (not the 200x200 gray ROI) to `face_encodings`; dlib's encoder aligns via landmarks and wants real RGB.

## Migration of Existing Face Data

**Yes — re-encoding is required, but there is no on-disk LBPH model to migrate.** LBPH was trained in-memory at startup (`train_recognizer()` at app.py:3533) and never persisted, so "the model" simply ceases to exist when you delete the LBPH code. The persistent assets are the per-employee JPEGs in `data/faces/<emp_id>/`.

Migration flow (one-time, e.g. a `if __name__` startup step or a small script):
1. For each `data/faces/<emp_id>/*.jpg`: `cv2.imread` (returns 200x200x3, grayscale content), `cv2.cvtColor(..., BGR2RGB)`, then `face_recognition.face_encodings(rgb, known_face_locations=[(0, 200, 200, 0)])` (force the whole crop as the face box — these are already tight crops).
2. Write all encodings to `data/encodings.json`.
3. Going forward, new captures encode from the color frame at capture time (higher quality than re-encoding old gray crops).

**Caveat (Pitfall below):** encoding from the existing *grayscale, tightly-cropped* JPEGs yields lower-quality embeddings than encoding from original color frames. Accuracy will be acceptable but not optimal; a re-capture campaign would improve it but is **not required** for the swap. [ASSUMED — quality degradation is expected behavior, not measured here]

## Common Pitfalls

1. **dlib build fails: no cmake.** `cmake` is absent on this host; gcc 15.2 is present. Without cmake the source build aborts. Install cmake first (apt or pip — see Installation). This is the single most likely failure.
2. **Feeding the gray 200x200 ROI to `face_encodings`.** dlib needs 8-bit **RGB** and performs landmark alignment; pass the *color* image + bbox, not the resized gray `face_roi`. Encoding a bare gray crop with no margin often yields empty results or poor vectors.
3. **`face_encodings` returns `[]` when it finds no face.** Always guard `if not encs:` before indexing `encs[0]` — both in capture and recognize. Passing `known_face_locations` makes this far less likely.
4. **Threshold direction confusion.** Both are lower-is-better, but the *scale* changes (80 -> 0.6). Don't reuse the int `lbph_threshold` value; add a float tolerance setting or recognition silently rejects everyone (0.6 is never `> 80`... actually every distance `< 0.6` so all-match if you forget to change the cutoff — equally wrong).
5. **Thread-safety under Flask dev server (`debug=True`, threaded).** `face_distance` against a read-only `known_encodings` array is reentrant/safe; the risk is **rebuilding** the global arrays during a concurrent read. The existing code already mutates the `recognizer` global without locks and relies on the single-PM2-worker constraint — keep that same assumption, and rebuild encodings into a *new* array then atomically reassign the global (don't mutate in place).
6. **Memory/cold-start.** dlib model load adds a few hundred MB RSS and the first `face_encodings` call is slow (model load). Pre-warm at startup (the existing `train_recognizer()` startup call is a natural spot). Per-encoding RAM and the 128-float vectors are negligible.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| C++ compiler | dlib build | ✓ | gcc 15.2.0 | — |
| cmake | dlib build | ✗ | — | `pip install cmake` then `--no-build-isolation` |
| Python | runtime | ✓ | 3.14.4 | — (no cp314 wheel; source build mandatory) |
| numpy | encodings | ✓ | 2.4.6 | — |
| opencv-contrib | detector/crop | ✓ | 4.13.0.92 | — |
| network access | pip install + model download | unknown (sandbox blocked `pip download`) | — | mirror wheels/models offline if blocked |

**Blocking with fallback:** cmake missing — install before building dlib.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `data/encodings.json` (JSON dict) is the right store vs numpy/pickle | Embedding Storage | Low — any of the three works; JSON matches project convention |
| A2 | Add new `face_match_tolerance` setting rather than reuse `lbph_threshold` | Threshold Mapping | Low — reuse is possible but conflicts with int UI/route |
| A3 | Re-encoding old gray crops gives acceptable (not optimal) accuracy | Migration | Medium — if accuracy is poor, a re-capture campaign is needed |
| A4 | Single-PM2-worker assumption makes lockless global swap safe | Pitfall 5 | Low — already a documented project constraint |
| A5 | dlib needs system cmake on cp314 (no wheel) | Install | Low — confirmed no cp314 wheel + no local cmake; build-from-source is dlib's documented path |

## Sources

### Primary (HIGH)
- `pip index versions` on the project venv — dlib 20.0.1, face_recognition 1.3.0, face_recognition_models 0.3.0 [VERIFIED]
- Local probes — no system cmake, gcc 15.2, sample face JPEG `(200,200,3)`, Python 3.14.4 [VERIFIED]
- app.py read — train_recognizer (638), recognize (3155), extract_face (628), settings (2982), capture paths (955/3100) [VERIFIED]

### Secondary (MEDIUM)
- github.com/ageitgey/face_recognition — face_encodings/face_distance API, 0.6 tolerance, unmaintained status [CITED]
- face-recognition.readthedocs.io — default tolerance 0.6 [CITED]
- github.com/comethrusws/Dlib_linux_python_3.x, pypi.org/project/dlib-bin — confirms no official cp313/cp314 manylinux wheel [CITED]

## Metadata

**Confidence breakdown:**
- Swap pattern & threshold mapping: HIGH — verified against actual app.py code
- Install path: MEDIUM — cmake-from-source confirmed needed; couldn't run the full build in sandbox (network-limited)
- Migration accuracy: MEDIUM — re-encoding gray crops is sound but quality not empirically measured

**Research date:** 2026-06-27
**Valid until:** ~2026-07-27 (stable libs; dlib/face_recognition move slowly)
