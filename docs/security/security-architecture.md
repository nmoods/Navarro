# Security architecture

Controls are listed with the code that implements them so they can be audited and tested.

## Identity and sessions

| Control | Implementation |
|---|---|
| Password hashing | Argon2id (`argon2-cffi`), automatic rehash on login — `core/security.py` |
| Password policy | ≥10 chars, 3 of 4 character classes — `schemas/core.py::RegisterIn` (mirrored client-side) |
| Account enumeration | Constant-time dummy hash verify for unknown emails; generic “Invalid email or password” |
| Access tokens | HS256 JWT, 15 min, `iss`/`typ`/`exp` required, kept **in memory** in the SPA (never localStorage) |
| Refresh tokens | 48-byte random, stored as SHA-256, httpOnly + SameSite=Strict + Secure (prod) cookie scoped to `/api/v1/auth` |
| Rotation & theft detection | Each refresh revokes the old token; reuse of a revoked token revokes the whole family — tested |
| CSRF | Cookie endpoints require `X-Requested-With: narravo` (not sendable cross-site without a CORS preflight, which CORS rejects for unknown origins) + SameSite=Strict |
| Supabase mode | JWTs verified with the project JWKS (RS256/ES256), audience and issuer checked; users mapped by `sub` |
| Production guard | Startup refuses weak/default `JWT_SECRET`, wildcard CORS and test-double providers |

## Authorization and tenancy

* Every user-owned row is loaded through `owned(session, Model, id, user)` which returns **404** for rows
  of other users (no existence leak). Child objects (scenes, jobs, exports) are checked through their
  parent. Covered by `tests/test_api.py::test_users_cannot_access_each_others_data`.
* Media is served only through **HMAC-signed, expiring capability URLs** bound to asset id + owner id
  (`sign_media_path`), or R2 presigned URLs. Tampered signatures return 403 (tested).
* Supabase RLS (`infrastructure/supabase/rls.sql`) enforces the same rules in the database.

## Input and output handling

| Risk | Mitigation |
|---|---|
| Injection (SQL) | SQLAlchemy parameterised queries only; no string-built SQL. Search uses `ilike` with bound params and wildcard stripping |
| Mass assignment | Pydantic models with `extra="forbid"` for updates; explicit field mapping |
| XSS | React escapes output; no `dangerouslySetInnerHTML`; API sends `X-Content-Type-Options: nosniff`; media responses send `Content-Security-Policy: default-src 'none'; sandbox`; nginx CSP for the SPA |
| LLM output | Validated against Pydantic schemas (lengths, enums, hex colours); invalid output is repaired or rejected; narration is never taken from the storyboard model |
| Uploads | 25 MB limit, extension allow-list, magic-byte sniffing, full decode, decompression-bomb guard (40 MP), re-encode to PNG (strips metadata and polyglots); audio must decode with libsndfile; server-generated storage keys |
| Path traversal | Storage keys match `^[a-z0-9][a-z0-9/_\-.]{0,200}$`, no `..`, resolved paths must stay under the storage root; download filenames sanitised |
| Request size | 30 MB cap enforced on `Content-Length` and streamed bodies (`core/middleware.py`) |

## Process and resource safety

* FFmpeg is always invoked with argument arrays (`subprocess.Popen([...])`, never `shell=True`), with
  timeouts and cancellation (`media/ffmpeg.py`). No user text ever reaches a command line; captions are
  rasterised by Pillow, not FFmpeg `drawtext`.
* The Kokoro worker receives JSON on stdin; text is length-limited and output paths are server-generated.
* Rendering abuse: per-user active-job cap (3), hourly generation cap (30), one active job per project,
  scene count cap (30), duration presets only, global worker concurrency, process-pool size cap, job and
  FFmpeg timeouts, clip cache size cap, temp-file cleanup.
* Rate limiting: 120 requests/min per IP, 20 auth POSTs/min per IP (`SlidingWindowLimiter`; swap for Redis
  with several API replicas).

## Network exposure and SSRF

* Ollama, ComfyUI, PostgreSQL bind to `127.0.0.1` (scripts) or an internal Docker network (compose); only
  the SPA and API are published, and only on localhost by default.
* Provider URLs come from server configuration only. The research provider talks to a fixed host
  (`en.wikipedia.org`) with a descriptive User-Agent and client-side throttling. Users can never make the
  server fetch an arbitrary URL.

## Secrets

* `.env` is git-ignored; `.env.example` documents every variable and marks secrets.
* The frontend only ever receives the API URL and (optionally) Supabase's public anon key.
* Logs are JSON; keys containing password/secret/token/authorization are redacted.

## Audit logging

`audit_logs` records registration, logins (success/failure), refresh-token reuse, project creation and
deletion, uploads, job cancellation, template publication, password changes and account deletion, with
IP and user id.

## Licence obligations (security-adjacent)

Stable Diffusion 1.5 is CreativeML OpenRAIL-M: its use restrictions must be passed on to users in the
terms of service of any hosted deployment (see `docs/research/license-audit.md`).
