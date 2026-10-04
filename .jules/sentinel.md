## 2024-10-04 - [Fix SQLite Arbitrary File Open & Add Security Headers]
**Vulnerability:** The `/api/backups` endpoint in `server/app.py` passed backup file paths directly into `sqlite3.connect()` without enforcing read-only access.
**Learning:** Even when files are generated from a safe `glob` restricted to a predefined directory, missing `?mode=ro` leaves databases vulnerable to unexpected lock issues or accidental state alterations by the read query (e.g. SQLite auto-creating missing files or journaling). Additionally, passing a raw path string (instead of a resolved URI) could be unsafe on different platforms.
**Prevention:** Always use `f.resolve().as_uri() + "?mode=ro"` with `uri=True` when making read-only SQLite connections to explicitly restrict write access.

## 2024-10-04 - [Added HTTP Security Headers]
**Vulnerability:** Missing HTTP Security Headers (X-Content-Type-Options, X-Frame-Options) allowed for MIME-type sniffing and clickjacking on the API responses.
**Learning:** Security headers should be configured globally on the main middleware level to act as a defense-in-depth mechanism.
**Prevention:** Apply a middleware in FastAPI/Starlette specifically dedicated to injecting robust security headers on all valid routes.
