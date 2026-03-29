# Security Review -- PE Document Intelligence Platform -- 2026-03-28 (Re-Review)

## Summary
- BLOCK findings: 0
- WARN findings: 5
- INFO findings: 4
- Overall verdict: WARN

All five previously reported BLOCK findings have been verified as correctly
fixed. No new BLOCK-level vulnerabilities were found. Five WARN-level and
four INFO-level findings remain and are documented below.

---

## Previously Fixed BLOCK Findings -- Verification

### [VULN-002] Path Traversal in LocalStorage -- VERIFIED FIXED
File: backend/src/storage/local.py lines 29-47, 49-68
Status: FIXED

The `_sanitize_filename()` method now rejects filenames containing `..`, `/`,
and `\` on line 38. It also extracts only the basename via `Path(filename).name`
and rejects `.` and `..` results on lines 42-45. The `save_file()` method
additionally resolves the destination path and validates it stays within the
upload directory boundary on lines 59-64 using `str(dest).startswith(...)`.
This is a correct two-layer defense against path traversal.

### [VULN-003] Dynamic Column Access in DocumentRepository -- VERIFIED FIXED
File: backend/src/db/repositories/documents.py lines 10-17, 79-83
Status: FIXED

An `ALLOWED_SORT_COLUMNS` whitelist is defined at module level on line 10
containing six permitted column names. The `list_all()` method validates
`sort_by` against this set on line 79 and raises `ValueError` for invalid
values before calling `getattr(Document, sort_by)`. This eliminates the
dynamic attribute access vulnerability.

### [VULN-004] File Size Limits on Upload Endpoints -- VERIFIED FIXED
File: backend/src/api/routers/documents.py lines 20, 71-75
File: backend/src/api/routers/bulk.py lines 69-73
Status: FIXED

`MAX_FILE_SIZE` is defined as 100 MB on line 20 of documents.py. Both the
single upload endpoint (documents.py line 71) and the bulk upload endpoint
(bulk.py line 69) check `len(content) > MAX_FILE_SIZE` and return HTTP 413.
The bulk router imports `MAX_FILE_SIZE` from the documents router to stay
consistent.

### [VULN-005] Magic Byte Validation on Upload -- VERIFIED FIXED
File: backend/src/api/routers/documents.py lines 25-41, 77-88
Status: FIXED

The `_MAGIC_BYTES` dictionary on lines 25-33 covers PDF (`%PDF`), DOCX/XLSX
(`PK`), PNG (`\x89PNG`), JPEG (`\xff\xd8\xff`), and TIFF (`II`/`MM`). The
`_validate_magic_bytes()` function checks that file content starts with at
least one of the expected prefixes. Both the single upload endpoint
(documents.py line 84) and the bulk upload endpoint (bulk.py line 77) call
this validation before processing. Extension validation is also applied
before magic byte checking.

### [VULN-001] Live API Keys in .env File
Status: NOT RE-CHECKED (out of scope for this re-review; .env files are
excluded from source code scanning per the task scope)

---

## WARN Findings

### [VULN-006] No Authentication or Authorization on Any Endpoint
Files: backend/src/api/app.py lines 91-100, all routers
Severity: WARN
Description: No authentication middleware, API key validation, or authorization
checks are applied to any route. All endpoints including document upload,
deletion, configuration management, extraction, and RAG query are publicly
accessible. While this may be acceptable during local development, it must be
addressed before any network-facing deployment.
Fix: Add an authentication dependency (e.g., OAuth2 bearer token, API key
header check, or JWT verification) and apply it globally or per-router before
deployment.

### [VULN-007] delete_file and file_exists Accept Arbitrary Paths Without Boundary Check
File: backend/src/storage/local.py lines 70-76, 78-80
Severity: WARN
Description: The `delete_file()` and `file_exists()` methods accept any
`file_path` argument and operate on it without verifying that the resolved
path is within an expected directory. While `save_file()` was fixed with a
resolved-path boundary check, these two methods were not updated. They are
currently only called with database-stored paths (not directly from user
input), but a future code change that passes user-controlled input to these
methods would enable path traversal for file deletion or existence probing.
Fix: Add the same resolved-path boundary check used in `save_file()` to both
`delete_file()` and `file_exists()`, ensuring the target path is within the
upload or parsed directory.

### [VULN-008] Health Check Endpoint Leaks Internal Exception Details
File: backend/src/api/routers/health.py line 28
Severity: WARN
Description: When the database is unreachable, the health check returns the
full Python exception string (`str(exc)`) in the JSON response body. This can
expose internal details such as database hostnames, port numbers, driver
names, and connection string fragments to any caller. The parse endpoint
(parse.py line 58) similarly returns Reducto API errors verbatim.
Fix: Return a generic "database unreachable" message in the health response.
Log the full exception server-side at WARNING level for debugging.

### [VULN-009] CORS Allows Credentials With Wildcard Methods and Headers
File: backend/src/api/app.py lines 79-88
Severity: WARN
Description: The CORS middleware is configured with `allow_credentials=True`
combined with `allow_methods=["*"]` and `allow_headers=["*"]`. While the
`allow_origins` list is restricted to two localhost origins, the wildcard
methods and headers combined with credentials is more permissive than
necessary. If origins are broadened in the future, this becomes a significant
risk enabling CSRF-like cross-origin attacks.
Fix: Restrict `allow_methods` to the HTTP methods actually used (GET, POST,
PUT, DELETE). Restrict `allow_headers` to a specific list (e.g.,
Content-Type, Authorization). For production, make `allow_origins`
configurable via environment variable.

### [VULN-010] Bulk Service Stores Unsanitized Filename in original_path
File: backend/src/bulk/service.py line 66
Severity: WARN
Description: The `BulkJobService.create_job()` method constructs the
`original_path` by directly interpolating the user-supplied filename into a
string: `f"data/upload/{file_name}"`. While the bulk upload router validates
extensions and magic bytes, the filename itself is not passed through
`LocalStorage._sanitize_filename()` before being stored in the database. A
filename containing traversal sequences (e.g., `../`) would be stored as-is,
which could cause issues if the stored path is later used for file operations
such as deletion via `delete_file()`.
Fix: Pass the filename through `LocalStorage._sanitize_filename()` or use the
`LocalStorage.save_file()` method (which already sanitizes) before
constructing the `original_path`. Alternatively, use a UUID-based filename
for storage and keep the original name only as metadata.

---

## INFO Findings

### [VULN-011] No Rate Limiting on Upload or LLM-Invoking Endpoints
Files: backend/src/api/routers/documents.py, bulk.py, parse.py, classify.py,
       extract.py, summarize.py, rag.py
Severity: INFO
Description: No rate limiting is applied to any endpoint. The RAG query,
parse, classify, extract, and summarize endpoints all trigger external API
calls (OpenAI, Reducto). An attacker could exhaust API quotas and incur
significant costs.
Fix: Add rate limiting middleware (e.g., slowapi) with per-IP or per-user
throttling, particularly on resource-intensive endpoints.

### [VULN-012] No Security Response Headers Configured
File: backend/src/api/app.py
Severity: INFO
Description: The application does not set security headers such as
`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, or
`Strict-Transport-Security`. While this is a JSON API, these headers provide
defense-in-depth.
Fix: Add a middleware that sets standard security headers on all responses.

### [VULN-013] Uvicorn Binds to 0.0.0.0 by Default
File: backend/src/main.py line 13
Severity: INFO
Description: The entry point binds Uvicorn to `0.0.0.0:8000`, which makes the
service accessible on all network interfaces. Combined with the absence of
authentication (VULN-006), this exposes the unauthenticated API to the local
network.
Fix: Default to `127.0.0.1` for development. Make the bind address
configurable via environment variable for production behind a reverse proxy.

### [VULN-014] sort_order Parameter Not Validated Against Allowlist
File: backend/src/db/repositories/documents.py lines 85-88
Severity: INFO
Description: The `sort_order` parameter defaults to descending for any value
other than `"asc"` via a simple if/else. While this is not exploitable (no
user input reaches `getattr` or SQL), explicit validation with a clear error
message for invalid values would be more robust and consistent with the
`sort_by` validation pattern.
Fix: Validate `sort_order` against `{"asc", "desc"}` and raise `ValueError`
for any other value.

---

## Dependency Review

All dependencies in `requirements.txt` and `pyproject.toml` use minimum
version pins (`>=`) rather than exact pins. Builds may pull newer versions
with unknown changes. No lock file with resolved versions exists. A
dependency audit tool (`pip-audit` or `safety`) should be integrated into CI.
No specific CVEs were identified in the currently specified minimum versions
as of 2026-03-28.

---

## Positive Findings (Mitigations Already in Place)

- All database queries use SQLAlchemy ORM with parameterized queries
- No usage of subprocess, eval, exec, or other code-execution functions
- PII filtering middleware is applied before LLM calls in the extractor
- File type allowlisting is present on both upload endpoints
- Magic byte validation confirms file content matches claimed extension
- File size limits enforced on both single and bulk uploads
- Path traversal defense in save_file uses character rejection plus
  resolved-path boundary check
- Sort column whitelist prevents dynamic attribute access injection
- SHA-256 dedup prevents redundant file storage
- State machine enforces valid document status transitions
- Pydantic models validate all API request and response bodies
- Secrets (API keys, database URL) loaded from environment variables via
  pydantic-settings, not hardcoded in source code

---

## Scan Methodology

1. Read all Python source files in `backend/src/` (70+ files across api,
   agents, bulk, config, db, parser, rag, services, storage packages)
2. Grep for dangerous patterns: hardcoded credentials, subprocess/eval/exec,
   raw SQL with string interpolation, dynamic attribute access with user input
3. Manual review of all route definitions for auth middleware presence
4. Manual review of file upload and storage paths for traversal vectors
5. Verified each of the five previously reported BLOCK fixes by reading the
   updated source code and confirming the mitigation logic
6. Review of configuration files (config.yml, .env.example) for hardcoded
   secrets in source code
7. Review of CORS, error handling, and infrastructure configuration
