# API reference

Base path `/api/v1`. Interactive OpenAPI docs: `http://127.0.0.1:8010/api/docs` (disabled in production).
All endpoints except `/health`, `/system/options`, `/auth/*` and signed media URLs require
`Authorization: Bearer <access token>`.

Errors always have the shape `{"error": {"code": "...", "message": "...", "details": {}}}` with codes
`unauthenticated` 401, `forbidden` 403, `not_found` 404, `conflict` 409, `payload_too_large` 413,
`validation_failed` 422, `rate_limited` 429, `provider_error` 502, `provider_unavailable` 503,
`internal_error` 500.

| Area | Method & path | Notes |
|---|---|---|
| Auth | `POST /auth/register` `POST /auth/login` | returns access token, sets refresh cookie |
| | `POST /auth/refresh` `POST /auth/logout` | cookie + `X-Requested-With: reelforge` |
| | `GET /auth/me` | |
| Projects | `GET /projects?q&status&limit&offset` `POST /projects` | create enqueues a `story` (or `production` with `auto_produce`) job |
| | `GET/PATCH/DELETE /projects/{id}` | PATCH merges caption/music settings |
| | `GET /projects/{id}/script` `GET /projects/{id}/storyboard` | storyboard includes scenes with signed asset URLs and pacing analysis |
| | `POST /projects/{id}/generate-story` `POST /projects/{id}/hooks/select` | 202 + job |
| | `POST /projects/{id}/produce {quality: draft|final}` | 202 + job; 409 if a job is running |
| | `GET /projects/{id}/exports` `GET /projects/{id}/jobs` | |
| Scenes | `PATCH /scenes/{id}` `DELETE /scenes/{id}` | |
| | `POST /projects/{id}/scenes` `POST /projects/{id}/scenes/reorder` | |
| | `POST /scenes/{id}/regenerate {parts, instruction}` | parts ⊂ visual_plan, narration, image |
| | `POST /scenes/{id}/image` (multipart) | upload replaces and pins the image |
| | `GET /scenes/{id}/assets?role=image` `POST /scenes/{id}/assets/{link}/restore` | variant history |
| Jobs | `GET /jobs?active` `GET /jobs/{id}` `GET /jobs/{id}/logs` `POST /jobs/{id}/cancel` | |
| Exports | `GET /exports` `DELETE /exports/{id}` | |
| Media | `GET /media?kind&source` `POST /media/upload` (multipart, purpose=image|music) `DELETE /media/{id}` | |
| | `GET /media/{id}/content?u&exp&sig` `GET /media/{id}/download?u&exp&sig` | HMAC-signed, expiring; supports HTTP range requests |
| Story DNA | `GET/POST /story-dna` `PUT/DELETE /story-dna/{id}` | |
| Voice | `GET /voices` `POST /voices/preview` (returns WAV) | voice ids may be blends: `af_bella:0.6,am_adam:0.4` |
| | `GET/POST /voice-profiles` `DELETE /voice-profiles/{id}` | |
| Templates | `GET/POST /templates` `DELETE /templates/{id}` | create from a project with `project_id` |
| Audio | `GET /music` `GET /music/moods/{mood}/preview` `GET /sfx` `GET /sfx/{kind}/preview` | |
| Series | `GET/POST /series` `GET/DELETE /series/{id}` | create enqueues `series_plan` |
| | `POST /series/{id}/replan` `POST /series/{id}/produce` `PATCH /series/{id}/episodes/{ep}` | |
| Planner | `GET /ideas?start&end&status` `POST /ideas` `PATCH/DELETE /ideas/{id}` | |
| | `POST /ideas/{id}/create-project` `POST /ideas/suggest` | suggest is synchronous (LLM) |
| Account | `PATCH /account/profile` `POST /account/password` `DELETE /account?confirm=<email>` | |
| System | `GET /dashboard` `GET /system/providers` `GET /system/options` `GET /health` | |
