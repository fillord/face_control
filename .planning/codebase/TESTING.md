# Testing

**Mapped:** 2026-06-11

---

## Current State

**Zero automated tests.** No test framework is configured. All verification is manual via Flask dev server and browser interaction.

---

## Test Framework

| Component | Status |
|-----------|--------|
| Backend test runner | None configured |
| Frontend test runner | None configured |
| CI pipeline | None |
| Coverage reporting | None |

---

## Critical Test Gaps

| Gap | Risk |
|-----|------|
| No tests for `extract_face()` / `train_recognizer()` | Core CV logic untested |
| No API endpoint tests (`/api/recognize`, `/api/employees`, etc.) | All routes untested |
| No attendance state machine tests | check-in/check-out logic untested |
| No input validation tests | Security boundary untested |
| No concurrent access tests | Race conditions invisible |

---

## Recommended Test Stack

**Backend:**
- `pytest` — test runner
- `pytest-cov` — coverage reporting
- `pytest-mock` — mocking OpenCV calls
- Flask test client (built-in) — route testing

**Frontend:**
- Manual browser testing is the current practice
- Playwright could cover kiosk/registration flows if automated testing is desired

---

## Priority Test Scenarios

1. **Face Recognition Flow** (`/api/recognize`)
   - Valid face → correct employee returned
   - No face in frame → appropriate response
   - Unknown face → not-found response

2. **Attendance State Machine**
   - First recognition → check-in recorded
   - Second recognition same day → check-out recorded
   - Third recognition same day → behavior defined

3. **Employee CRUD** (`/api/employees`)
   - Create employee → appears in list
   - Delete employee → removed from list, faces cleaned up

4. **Face Registration** (`/api/register_face`)
   - 10 samples captured → model trains successfully
   - Fewer than 10 samples → model not trained

5. **Auth** (`/login`)
   - Correct credentials → session created
   - Wrong credentials → rejected

---

## Notes

- OpenCV calls (`cv2.*`) will need to be mocked in unit tests — the Haar cascade and LBPH model are not available in headless CI
- JSON file I/O should be abstracted behind interfaces before unit testing becomes practical
- Integration tests against the live Flask app are the most pragmatic starting point

---
*Last mapped: 2026-06-11*
