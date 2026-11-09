# ReelForge AI — Free Infrastructure Evaluation

- Research date: 2026-11-09. Quotas come from official pricing and limits pages fetched on that date. Free tiers change often, so re-check before launch.
- Principle: **no billing features and no paid AI APIs**. The free tiers host the *web app, metadata and media*. **AI inference runs on the operator's own machine (local worker).**

> **Important**
> - **Free API quota is not unlimited inference.** No free tier listed here provides GPU or meaningful CPU for LLM, diffusion, TTS or Whisper workloads.
> - **No GPU work on Cloudflare Pages/Workers.** Workers Free has **10 ms CPU per request** and **128 MB memory**. Pages is static hosting.
> - Cloudflare Workers AI and similar hosted-inference products are **paid AI APIs in disguise** once past tiny daily allowances. They are excluded by policy.

---

## 1. Frontend hosting

| Service | Free quotas | Inactivity policy | Commercial use | Notes / source |
|---|---|---|---|---|
| **Cloudflare Pages** | 500 builds/month, 1 concurrent build, 20-min build timeout, 20,000 files/site, 25 MiB max file, 100 custom domains/project, 100 projects/account. **Static asset requests "free and unlimited"** on free and paid plans. Pages Functions count against the Workers Free 100k req/day. | None | ✅ standard Cloudflare ToS | https://developers.cloudflare.com/pages/platform/limits/, https://developers.cloudflare.com/pages/functions/pricing/. Free subdomain `*.pages.dev`. Cloudflare also steers new projects to Workers Static Assets (same economics; **UNVERIFIED** whether Pages is formally deprecated). |
| Netlify Free | **300 credits/month, hard limit, no top-up on Free**. Credits reset monthly. Consumption: production deploy = 15 credits, bandwidth = 20 credits/GB, compute = 10 credits/GB-hour, 2 credits per 10k requests. So about 20 deploys or about 15 GB bandwidth per month. | Projects may be paused at the limit (docs mention "Resume paused projects"; exact behaviour **UNVERIFIED**) | Not addressed on the pricing docs (**UNVERIFIED**, see https://www.netlify.com/legal/terms-of-use/) | https://www.netlify.com/pricing/, https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/. Much tighter than Cloudflare. |
| GitHub Pages | 1 GB site, 100 GB/month soft bandwidth, 10 builds/hour soft | None | **❌ "not intended for or allowed to be used as a free web-hosting service to run your online business ... or ... commercial software as a service (SaaS)"** | https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits. **Use for project docs/landing only, not the app.** |

**Choice: Cloudflare Pages** (or Workers Static Assets) for the React/Vite SPA.

## 2. Object storage (generated media)

| Service | Free quotas | Egress | Notes |
|---|---|---|---|
| **Cloudflare R2** | **10 GB-month storage, 1M Class A ops (writes/lists), 10M Class B ops (reads) per month** (Standard storage only; free tier does not apply to Infrequent Access) | **Free** | Paid beyond the free tier: $0.015/GB-month, $4.50/M Class A, $0.36/M Class B. A payment method is required to enable R2 (**UNVERIFIED** in current onboarding). Source: https://developers.cloudflare.com/r2/pricing/ |
| Supabase Storage (Free) | 1 GB storage, 5 GB egress (+5 GB cached), 50 MB max upload | Counted | https://supabase.com/pricing. Too small for video. |
| Neon object storage | 5 GB/project (Free) | — | https://neon.com/pricing. New, less proven. |
| Oracle Object Storage (Always Free) | 20 GB combined (Always-Free-only accounts), 50k API requests/month | 10 TB/month egress | https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm |

Capacity math: a 45 s 1080x1920 H.264 reel at about 6 Mbps is about 35 MB, so **10 GB holds about 280 reels**. Enforce **lifecycle deletion** (for example 14–30 days for renders, keep source JSON forever) and per-user quotas. R2 egress is free, so share links don't cost bandwidth.

**Choice: Cloudflare R2**, accessed with presigned URLs. The browser uploads and downloads directly. The local worker uploads finished MP4s through the S3 API.

## 3. Database + Auth

| Service | DB | Auth | Other | Inactivity | Projects | Source |
|---|---|---|---|---|---|---|
| **Supabase Free** | **500 MB per project** | **50,000 MAU** | 1 GB storage, 5 GB egress, 500k Edge Function invocations, Realtime 200 concurrent / 2M msgs, 1-day logs, **no automatic backups** | **Paused after 1 week of inactivity** | **2 active projects** | https://supabase.com/pricing |
| Neon Free | **1 GB per project / 20 GB total**, 100 CU-hours per project per month, autoscale to 2 CU, **scale-to-zero after 5 min (always on)**, 5 GB egress/project, 10 branches, 6 h history | Neon Auth up to 60,000 MAU/project | Compute suspends at limit. No data deleted. | Scale-to-zero (cold start), no project deletion stated | 100 projects | https://neon.com/pricing |
| Cloudflare D1 Free | **500 MB max per DB**, 10 DBs, 5 GB total, 5M rows read/day, 100k rows written/day | none (bring your own) | SQLite semantics | none | — | https://developers.cloudflare.com/d1/platform/pricing/, https://developers.cloudflare.com/d1/platform/limits/ |
| Render Free Postgres | 1 GB | — | **Expires 30 days after creation** (+14-day grace, then deleted) | — | 1 | https://render.com/docs/free |
| Koyeb Free Postgres | 0.25 vCPU, 1 GB RAM, 1 GB storage, "Free 5h" (meaning **UNVERIFIED**) | — | scale-to-zero | — | — | https://www.koyeb.com/pricing |

**Choice: Supabase Free** (Postgres + Auth in one, 50k MAU). Mitigations:
- **Pausing:** the self-hosted backend/worker sends a lightweight authenticated DB query on a schedule (for example daily), which keeps the project active. Legitimate keep-alive is common practice, but fair-use review is **UNVERIFIED**. Document how to restore a paused project.
- **No backups on Free:** nightly `pg_dump` from the local worker to R2 (encrypted).
- **500 MB:** store only metadata and storyboard JSON in Postgres. All media goes in R2.
- **Fallback:** Neon Free (DB) plus Supabase Auth, or Neon Auth.

## 4. Backend (FastAPI) hosting

| Option | Free offer (2026-11) | Sleep / limits | Commercial | Fit |
|---|---|---|---|---|
| **Self-hosted on the dev/operator machine** (Windows service or `uv run`) exposed via **Cloudflare Tunnel** | Free | Up while the machine is on | ✅ | **Recommended for v1**: the AI worker is local anyway. Cloudflare Tunnel free availability per Cloudflare Zero Trust free plan is **UNVERIFIED** in current terms. |
| **Oracle Cloud Always Free** | Ampere A1: **1,500 OCPU-h + 9,000 GB-h/month = 2 OCPU / 12 GB RAM** (reduced from the older 4 OCPU/24 GB), 2x AMD micro (1/8 OCPU, 1 GB), 200 GB block, 10 TB egress | **Idle reclamation:** over 7 days, CPU p95 <20% **and** network <20% **and** memory <20% (A1). A1 capacity is often unavailable in popular regions (anecdotal, **UNVERIFIED**). | ✅ | Best free always-on API host. Too weak for AI inference (2 ARM cores). |
| Render Free web service | 750 instance-hours/workspace/month | **Spins down after 15 min without traffic** (~1 min cold start). Ephemeral FS. May restart anytime. "**Do not use them for production applications.**" | Not stated | Demo/staging only. https://render.com/docs/free |
| Railway | **Trial: one-time $5, 30 days.** **Free plan: $1/month credit**, 1 vCPU / 0.5 GB per service, 500 MB volume | Credit exhaustion stops services | — | Too small. https://railway.com/pricing |
| Fly.io | **"New organizations don't have a free tier"**. $1 trial credit for 7 days. Legacy (pre-Oct-2024) orgs keep allowances. | — | — | ❌ https://docs.fly.io/about/pricing |
| Koyeb | **No free web-service instance listed** (only free Postgres). Pro $29/mo. | — | — | ❌ https://www.koyeb.com/pricing |
| Cloudflare Workers (Python Workers) | 100k req/day, **10 ms CPU/request**, 128 MB, 50 subrequests | — | ✅ | ❌ for FastAPI + SQLAlchemy. Fine for tiny edge glue (signed-URL minting, webhooks). https://developers.cloudflare.com/workers/platform/limits/ |

## 5. Free domains

| Option | Terms | Fit |
|---|---|---|
| `*.pages.dev` (Cloudflare Pages) and `*.workers.dev` | Included with the account | **Default** |
| Cloudflare Tunnel `*.trycloudflare.com` (quick tunnels) | Random ephemeral hostname, no uptime guarantee (**UNVERIFIED** current terms) | Dev only |
| eu.org | Free subdomains, "mainly to provide free subdomain registration to users or non-profit organizations". Manual review, historically slow (weeks or more, **UNVERIFIED**). Needs your own DNS (Cloudflare DNS works). https://nic.eu.org/ | OK for an open-source community instance |
| is-a.dev | "for **personal websites**" of developers. Registered by PR. Abuse/ToS reports via GitHub. https://github.com/is-a-dev/register | **❌ not for a product/SaaS** (personal-site purpose) |
| Paid domain (~US$10/yr at cost via Cloudflare Registrar) | — | Recommended before any public launch (outside the "free" scope; a one-time operator choice, not a product billing feature) |

## 6. Supabase Auth JWT verification from FastAPI, and RLS coexistence (section F)

### 6.1 Verification (2026 state)
- Supabase now supports **asymmetric JWT signing keys**. **ES256 (P-256) is recommended over RS256**, and EdDSA is "coming soon". The **legacy HS256 JWT secret is "No longer recommended. Available for backward compatibility."** Source: https://supabase.com/docs/guides/auth/signing-keys
- **JWKS endpoint:** `GET https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`. Verifiers fetch public keys there, so rotation does not require redeploying the backend.
- **Caching:** Supabase's edge caches JWKS for 10 min, and clients may cache another 10 min. Always add a new key as **standby** first, then rotate, and revoke the old key only after access tokens expire (docs suggest waiting **≥1 h 15 min** with 1 h tokens).
- **API keys:** new `sb_publishable_...` (browser) and `sb_secret_...` (server) keys replace `anon`/`service_role`. They are **not JWTs** and can be rotated independently.

Recommended FastAPI approach (design only, no code):
1. Use **PyJWT 2.15.1** (MIT, `PyJWKClient` with built-in key caching) or **joserfc 1.8.0** (BSD-3). Avoid `python-jose` (last release 2025-05).
2. On each request, read `Authorization: Bearer <access_token>`. Select the key by `kid` from the cached JWKS, refreshing once on an unknown `kid`. Then verify:
   - `alg` ∈ {ES256, RS256}. Never accept `none` or HS256 once migrated.
   - `iss == https://<ref>.supabase.co/auth/v1`
   - `aud == "authenticated"`
   - `exp`/`nbf` with ≤60 s leeway
   - `role == "authenticated"`
3. Map `sub` to `user_id`. Read authorisation data **only from `app_metadata`**. `user_metadata` is user-editable, and Supabase warns it "is not a good place to store authorization data".
4. Do **not** call the Supabase Auth server on every request. Local JWKS verification is enough. For sensitive actions (account deletion, quota resets), also check the session is not revoked via `GET /auth/v1/user` (JWTs stay valid until `exp`).

### 6.2 RLS when the backend uses a privileged connection
Facts (https://supabase.com/docs/guides/database/postgres/row-level-security):
- "Enable RLS on every table in an exposed schema. A table in an exposed schema without RLS is readable and writable by any role with a grant on it."
- `service_role` (used by secret keys) has **`bypassrls`**, and `postgres` also bypasses RLS. A secret key bypasses RLS only when the request carries no user token.

Recommended pattern for ReelForge:
1. **Enable RLS on every table in `public`** and **write owner policies** (`user_id = (select auth.uid())`, the cached initPlan form). This keeps the database safe if the browser ever uses supabase-js or the Data API directly. Also **revoke default grants from `anon`** on tables that should never be public. If the frontend never uses the Data API, **remove the app schema from the exposed schemas** (Securing your API) as defence in depth.
2. Put app tables in a **non-exposed schema** (for example `app`) accessed only by the backend.
3. The backend connects with a **dedicated least-privilege role** (for example `reelforge_api`, `NOINHERIT`, no `BYPASSRLS`, grants only on `app.*`), not `postgres` or `service_role`. It always filters by the verified `user_id` in SQLAlchemy queries (repository layer enforces tenant scoping).
4. Optional belt-and-braces: per transaction, `SET LOCAL role authenticated; SELECT set_config('request.jwt.claims', '<verified claims json>', true);` so that the **same RLS policies apply to backend queries**. This works with Supavisor in transaction mode because `SET LOCAL` is transaction-scoped.
5. Background workers (render jobs) that legitimately act across users use a **separate** role with `BYPASSRLS` (or `SECURITY DEFINER` functions in a **non-exposed** schema). Its credentials never leave the worker host. Supabase warns: "Never share login credentials for any Postgres Role with this privilege."
6. Never put `SECURITY DEFINER` functions in an exposed schema, because they are callable over the Data API with the creator's privileges.

## 7. Recommended deployment topology (v1, all free tiers)

```
 Browser (React SPA)
   │  HTTPS
   ├──► Cloudflare Pages  (static SPA, *.pages.dev)               [free, unlimited static]
   ├──► Supabase Auth     (login; ES256 JWT, JWKS)                [Free: 50k MAU]
   ├──► FastAPI backend   (self-hosted on operator PC via Cloudflare Tunnel,
   │                       or Oracle Always Free A1 2 OCPU/12 GB)
   │        │ verifies JWT via JWKS; least-privilege PG role
   │        ├──► Supabase Postgres (metadata, storyboards, jobs)  [Free: 500 MB, pauses after 7 d idle]
   │        ├──► Cloudflare R2 (presigned PUT/GET for media)      [Free: 10 GB, 1M A / 10M B ops, $0 egress]
   │        └──► Job queue table in Postgres (SKIP LOCKED polling)
   │
   └──► R2 presigned GET (download/preview MP4)

 Local AI worker (operator machine: i7-10700, 32 GB, CPU-only; Python 3.12)
   polls jobs ─► Ollama (qwen3.5:4b, format=JSON schema)
              ─► OpenVINO GenAI (SD1.5-LCM / FLUX.2-klein-4B)
              ─► Kokoro-82M (TTS, isolated GPL-3 G2P worker)
              ─► faster-whisper small.en (word timestamps)
              ─► Python compositor → FFmpeg (subprocess) → MP4
              ─► upload to R2, update job row, pg_dump nightly → R2
```

Why this topology:
- The only always-on public components are static hosting (Pages), managed Auth/DB (Supabase) and object storage (R2). All three have generous free tiers with no inactivity deletion (Supabase only *pauses*).
- **All inference is local**. Throughput is bounded by the operator's CPU (about 4–7 min per reel in the default preset, see [ai-model-comparison.md](./ai-model-comparison.md)), so the UI must show queue position and ETA. A free-tier SaaS cannot promise "unlimited" generation.
- Swappable: Neon instead of Supabase DB, Oracle A1 instead of the self-hosted API, and GPU workers (ComfyUI/OpenVINO) can join the same job queue later.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Supabase pauses after 7 days idle | Scheduled keep-alive from the worker. Documented restore. Neon fallback. |
| Supabase Free has no backups | Nightly `pg_dump` to R2 |
| R2 10 GB fills | TTL lifecycle rules, per-user quotas, re-render on demand from stored JSON |
| Operator PC offline means the API is down (if self-hosted) | Host the API on Oracle A1 (always on) and keep only the worker local. The UI shows "worker offline, job queued". |
| Oracle reclaims an idle A1 VM | The API's real traffic plus scheduled jobs usually exceed thresholds. Monitor, with an automated rebuild script (IaC). |
| Free-tier terms change | Re-verify quarterly. Abstract providers behind config (S3-compatible storage, standard Postgres, OIDC/JWKS auth). |
