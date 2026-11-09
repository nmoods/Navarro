# Database schema

PostgreSQL in production (Supabase or Neon), SQLite for local development and tests. Models live in
`backend/app/infrastructure/database/models/`; migrations in `backend/alembic/versions/`
(`alembic upgrade head`, run automatically at API start outside tests). JSON columns are `JSONB` on
PostgreSQL. All primary keys are UUIDs; timestamps are timezone-aware.

## Entity overview

```
users ─1─1─ profiles
  │
  ├─< projects ─1─1─ project_settings
  │      ├─< scripts (versioned: brief, hooks, script, claims)
  │      ├─< storyboards (versioned, one is_current) ─< scenes ─< scene_assets >─ media_assets
  │      ├─< video_exports ─> media_assets (video, thumbnail)
  │      └─< generation_jobs ─< generation_job_logs
  ├─< story_dna_profiles      ├─< voice_profiles      ├─< media_assets
  ├─< content_series ─< series_episodes ─> projects
  ├─< content_ideas            ├─< templates (user or built-in/public)
  ├─< music_tracks / sound_effects (user uploads; NULL user = built-in)
  ├─< refresh_tokens           └─< audit_logs
```

## Tables

| Table | Purpose | Ownership | Notable constraints / indexes |
|---|---|---|---|
| `users` | account | self | `email` unique, `external_id` unique (Supabase `sub`) |
| `profiles` | display name, default Story DNA, preferences | `user_id` PK/FK cascade | |
| `refresh_tokens` | hashed rotating refresh tokens | `user_id` cascade | `token_hash` unique, `family_id` index (reuse detection) |
| `audit_logs` | security-relevant events | `user_id` SET NULL | `(user_id, created_at)` |
| `projects` | a video | `user_id` cascade | `(user_id, updated_at)`, `series_id` |
| `project_settings` | format, style, voice, captions, music, brand | `project_id` PK cascade | |
| `scripts` | versioned brief/hooks/script/claims | via project | unique `(project_id, version)` |
| `storyboards` | versioned scene sets + pacing analysis | via project | unique `(project_id, version)`, `(project_id, is_current)` |
| `scenes` | one scene of a storyboard | via project (denormalised `project_id`) | `(storyboard_id, position)` |
| `scene_assets` | links image/narration/transcript to a scene with `input_hash` | via scene | `(scene_id, role, is_current)` |
| `media_assets` | every stored file | `user_id` cascade | `storage_key` unique, `(user_id, kind, created_at)`, `(user_id, sha256)` |
| `video_exports` | rendered MP4s | `user_id` cascade | `(project_id, created_at)`, `(user_id, created_at)` |
| `generation_jobs` | queue | `user_id` cascade | claim index `(status, run_after, priority)`; `parent_job_id` |
| `generation_job_logs` | per-job log lines | via job | `(job_id, created_at)` |
| `story_dna_profiles` | reusable creative identity | `user_id` cascade | unique `(user_id, name)` |
| `voice_profiles` | saved voices/blends | `user_id` cascade | unique `(user_id, name)` |
| `content_series` | series + bible | `user_id` cascade | `(user_id, created_at)` |
| `series_episodes` | planned episodes | via series | unique `(series_id, position)` |
| `content_ideas` | planner ideas + schedule | `user_id` cascade | `(user_id, scheduled_for)` |
| `templates` | settings presets (community-ready, no payments) | user or built-in | `(is_public, category)` |
| `music_tracks`, `sound_effects` | uploaded/built-in audio | user or NULL | |

## Cascade behaviour

* Deleting a **user** deletes everything they own (DB cascade) and the API removes their stored files.
* Deleting a **project** deletes scripts, storyboards, scenes, scene asset links, exports and jobs. Media
  files remain in the library until deleted there (a project can share images with others).
* Deleting a **series** deletes its episodes; episode projects are kept (`series_id` set NULL).
* Deleting a **Story DNA** sets `story_dna_id` NULL on projects and series.

## Authorization

The API enforces ownership on every query (`owned()` returns 404 for other users' rows). For Supabase
deployments, `infrastructure/supabase/rls.sql` enables and forces Row Level Security on every table as
defence in depth: owner-only policies for user tables, parent-based policies for child tables, read-only
policies for jobs/logs, and no access at all to `refresh_tokens` and `audit_logs`.
