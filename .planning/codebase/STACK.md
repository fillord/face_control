# Technology Stack

**Analysis Date:** 2026-06-11

## Languages

**Primary:**
- Python 3.14.4 - Server-side application logic, face recognition, and API
- JavaScript (Vanilla) - Frontend interactivity, WebRTC camera access, real-time UI
- HTML5 - Page structure with Jinja2 templating
- CSS3 - Styling with CSS Grid and Flexbox

**Secondary:**
- JSON - Configuration and data storage format

## Runtime

**Environment:**
- Python 3.14.4 (from `/var/www/sites/face-almgp33/venv/bin/python`)

**Package Manager:**
- pip 25.1.1
- Lockfile: Not detected (using venv with installed packages list available)

## Frameworks

**Core:**
- Flask 3.1.3 - Web framework for HTTP routing, request handling, and session management (`app.py`)
- Jinja2 3.1.6 - Template engine for rendering HTML with dynamic data (`templates/`)

**Computer Vision:**
- OpenCV (opencv-contrib-python 4.13.0.92) - Face detection using Haar Cascades and LBPH face recognition (`app.py` lines 20-22, 105-127)

**Testing:**
- Not detected

**Build/Dev:**
- gunicorn 26.0.0 - Production WSGI application server (referenced in README.md)

## Key Dependencies

**Critical:**
- opencv-contrib-python 4.13.0.92 - Face detection and recognition using Cascade Classifier and LBPH (Local Binary Pattern Histograms) algorithm
- numpy 2.4.6 - Array operations for image processing
- Flask 3.1.3 - Web server and routing
- bcrypt 5.0.0 - Password hashing for admin authentication

**Infrastructure:**
- Werkzeug 3.1.8 - WSGI utilities (Flask dependency)
- Jinja2 3.1.6 - Template rendering
- click 8.4.1 - CLI framework (Flask dependency)
- blinker 1.9.0 - Signal support (Flask dependency)
- itsdangerous 2.2.0 - Data signing for session management
- MarkupSafe 3.0.3 - Safe string handling

## Configuration

**Environment:**
- Flask secret key: Configured via `SECRET_KEY` environment variable or hardcoded default in `app.py` line 10
- File-based storage: No database - all data persists in JSON files in `data/` directory
- Application port: 5050 (default) or configurable at runtime

**Build:**
- No build configuration needed - pure Python/HTML/CSS/JavaScript stack
- Development: Flask built-in server with `debug=True`
- Production: gunicorn WSGI server (see README.md lines 80-84)

## Platform Requirements

**Development:**
- Python 3.8+ (official requirement per README.md)
- Webcam with browser MediaDevices API support
- Modern browser with WebRTC support (Chrome, Firefox, Edge)

**Production:**
- Linux/Unix server (PM2 process manager referenced in project memory)
- Port 5050 exposed for HTTP traffic
- Nginx reverse proxy recommended (see README.md line 76)
- File system with read/write permissions for `data/` and `data/faces/` directories

---

*Stack analysis: 2026-06-11*
