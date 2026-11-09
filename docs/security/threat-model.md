# Threat model

Method: STRIDE over the data flows in `docs/architecture/system-architecture.md`. Status reflects the
current code; “residual” lists what remains for a public, multi-tenant deployment.

## Assets

User accounts and sessions · scripts, storyboards, generated media (may be unpublished work) · uploaded
files · compute (CPU/GPU time is the scarce, abusable resource) · server secrets (JWT secret, DB and R2
credentials) · local model servers.

## Trust boundaries

1. Browser ↔ API (internet). 2. API ↔ database / storage. 3. API/worker ↔ local AI processes.
4. LLM output ↔ application (model output is untrusted data). 5. Worker ↔ FFmpeg/Kokoro subprocesses.

## Threats and mitigations

| # | Threat (STRIDE) | Scenario | Mitigation | Residual |
|---|---|---|---|---|
| 1 | Spoofing | Credential stuffing / brute force | Argon2id, auth rate limit, generic errors, audit log | Add CAPTCHA/lockout for public hosting |
| 2 | Spoofing | Stolen refresh token replay | Rotation + family revocation on reuse, httpOnly SameSite=Strict cookie | Token binding not implemented |
| 3 | Spoofing | Forged JWT | Server-side secret ≥32 chars enforced in prod; algorithm pinned; Supabase via JWKS | — |
| 4 | Tampering | Editing another user's project/scene by id | `owned()` checks + RLS; ids are UUIDv4 | — |
| 5 | Tampering | Malicious upload (polyglot, SVG script, zip bomb) | Allow-list, sniffing, full decode, re-encode, pixel cap, size cap | AV scanning not included |
| 6 | Tampering | Prompt injection via topic text making the LLM emit harmful structure | Schema validation, enum constraints, narration taken from deterministic split, no tool use, no code execution | The LLM can still write misleading text; fact checker + human review |
| 7 | Repudiation | User denies deleting data | Audit log with IP and timestamps | Log retention policy to define |
| 8 | Information disclosure | Guessing media URLs | HMAC-signed expiring URLs bound to owner; no public bucket | Signed URLs can be shared by their holder until expiry (1 h) |
| 9 | Information disclosure | Error messages leak internals | Global handler returns generic 500; stack traces only in server logs | — |
| 10 | Information disclosure | Model servers exposed | Bind to localhost / internal network | Firewall verification is the operator's job |
| 11 | DoS | Flooding render jobs | Per-user active + hourly limits, one job per project, worker concurrency, timeouts | Per-user CPU-seconds quota for public hosting |
| 12 | DoS | Huge request bodies | 30 MB stream-enforced limit, 25 MB uploads | — |
| 13 | DoS | Disk exhaustion | Clip cache cap, temp cleanup, upload limits | Per-user storage quota not enforced yet |
| 14 | Elevation | Command injection into FFmpeg | Argument arrays, no shell, captions rendered in Python | — |
| 15 | Elevation | SSRF through research or provider URLs | Fixed hosts from config only; no user-controlled URLs | — |
| 16 | Elevation | Path traversal in storage | Key validation + resolved-path containment | — |
| 17 | Supply chain | Malicious dependency/model | Locked dependency versions (uv.lock, package-lock.json), models from official sources, GPL components process-isolated | Hash-pinning model downloads is a recommended next step |

## Security tests

`backend/tests/test_api.py` covers: refresh rotation and reuse detection, CSRF header requirement,
tampered tokens, cross-user isolation on read/update/delete/produce/jobs, request-size limit, upload
spoofing/extension/traversal, signed-URL tampering, security headers.
