# External Integrations

**Analysis Date:** 2026-06-11

## APIs & External Services

**QR Code Generation:**
- QR Server API - Generates registration link QR codes at startup
  - SDK/Client: Direct HTTPS URL fetch in browser JavaScript
  - Usage: `https://api.qrserver.com/v1/create-qr-code/` (kiosk.html lines 197-205)
  - Endpoint: Used only when no employees exist, to display registration link
  - No authentication required

**WebRTC/Camera Access:**
- Browser MediaDevices API - Webcam access for live face detection and recognition
  - SDK/Client: `navigator.mediaDevices.getUserMedia()`
  - Usage: `kiosk.html` line 230, `register.html` - real-time video stream capture
  - Requires HTTPS or localhost, user permission grant
  - No external service - local browser API

## Data Storage

**Databases:**
- None - No relational or NoSQL database
- Local JSON files only: `data/employees.json`, `data/attendance.json`, `data/config.json`, `data/logs.json`
- File I/O operations: `app.py` lines 26-84 (load/save helpers)

**File Storage:**
- Local filesystem only
  - Training face images: `data/faces/{emp_id}/face_{n}.jpg` (app.py lines 234-237)
  - Employee metadata: `data/employees.json` (app.py line 14)
  - Attendance records: `data/attendance.json` (app.py line 15)
  - Configuration: `data/config.json` (app.py line 16)
  - Logs: `data/logs.json` (app.py line 17)
- No cloud storage, no S3, no CDN

**Caching:**
- None - No Redis, Memcached, or in-memory cache
- Face recognizer model loaded into memory at startup (app.py lines 21-22, 418)
- Recognizer training happens in-process (app.py lines 105-127)

## Authentication & Identity

**Auth Provider:**
- Custom authentication
  - Implementation: Basic username/password with bcrypt hashing (app.py lines 42-48)
  - Password storage: bcrypt hash in `data/config.json` (app.py lines 39-40)
  - Session management: Flask session with `SECRET_KEY` (app.py line 10)
  - Login page: `/login` route (app.py lines 136-152)
  - Protected routes: `/register`, `/admin` (login_required decorator, app.py lines 42-48, 160-167)
  - No external OAuth, SAML, or identity provider

**Face Recognition:**
- OpenCV LBPH (Local Binary Pattern Histograms) recognizer
  - No cloud API - all processing local
  - Confidence threshold: 80 (app.py line 286)
  - Training: Minimum 2 face samples per employee (app.py line 122)

## Monitoring & Observability

**Error Tracking:**
- None - No Sentry, Rollbar, or error tracking service

**Logs:**
- Local JSON file: `data/logs.json` (app.py lines 72-84)
- Log entries: Recognition events with timestamp, employee ID, name, event type, confidence scores (app.py lines 315-316)
- Rotation: In-memory limit of 10,000 entries (app.py line 81-82)
- Accessible via logs displayed on kiosk UI (kiosk.html lines 80-90)

**Debugging:**
- Flask debug mode enabled in development (app.py line 422)
- No APM or performance monitoring tools

## CI/CD & Deployment

**Hosting:**
- Self-hosted Linux server (Port 5050)
- PM2 process manager (reference: project memory notes pm2 name "face-recognition")
- Nginx reverse proxy recommended (README.md line 76)

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, Jenkins, or CI/CD configuration

**Process Management:**
- PM2 (mentioned in project memory) - manages Flask app lifecycle on port 5051 (per memory)
- Production server: gunicorn WSGI server (README.md lines 80-84)
- Manual startup available: `python app.py` for development

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` - Flask session encryption key (app.py line 10)
  - Default fallback: "medkontrol-secret-2026-xK9mP3qR7v" (not recommended for production)
  - Should be set for production deployments

**Secrets location:**
- `.env` file - Not committed to repository, manage separately
- Default hardcoded fallback in code (app.py line 10) - For development only

**Application Configuration:**
- Face detection threshold: `scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)` (app.py lines 97, 252, 256)
- Recognition confidence threshold: 80 (app.py line 286) - Lower confidence = better match
- Check-in deadline: 09:00:00 for "on-time" vs "late" logic (app.py line 303)
- Log rotation limit: 10,000 entries (app.py line 81)

## Webhooks & Callbacks

**Incoming:**
- None - No webhook endpoints for external services

**Outgoing:**
- None - No webhooks sent to external systems
- Application is self-contained, no integrations with external attendance/HR systems

## Data Export

**Formats:**
- CSV export available (referenced in README.md line 50, admin.html)
- JSON format for internal storage (employees, attendance, logs, config)

**API Response Format:**
- JSON (application/json) - All API endpoints return JSON (app.py lines 171-414)

---

*Integration audit: 2026-06-11*
