# Deployment

Recommended topology (details and quotas in `docs/research/free-infrastructure.md`):

```
 Cloudflare Pages (SPA, free)  ──HTTPS──►  API (self-hosted box / Oracle Always Free A1)
                                              │  PostgreSQL: Supabase Free (or Neon Free)
                                              │  Media: Cloudflare R2 (10 GB free, no egress fees)
                                              └─ Worker + Ollama + ComfyUI + Kokoro on your own machine
                                                 (private network / Tailscale / WireGuard)
```

GPU-heavy generation never runs on Cloudflare Pages/Workers. Free tiers have limits: Supabase Free pauses
after 7 days of inactivity and has a 500 MB database; R2 Free covers 10 GB storage and 1M Class A ops per
month; Oracle Always Free capacity is not guaranteed. A free API quota is not unlimited inference — that is
why every model here runs on hardware you control.

## 1. Database (Supabase)

1. Create a project; copy the **direct** connection string (port 5432).
2. `REELFORGE_DATABASE_URL=postgresql+psycopg://postgres:<pw>@db.<ref>.supabase.co:5432/postgres`
3. Run `uv run alembic upgrade head` from `backend/`.
4. Apply Row Level Security: `psql "$DB_URL" -f infrastructure/supabase/rls.sql`.
5. Optional Supabase Auth: set `REELFORGE_AUTH_MODE=supabase`, `REELFORGE_SUPABASE_URL`, and in the
   frontend `VITE_AUTH_MODE=supabase`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (public key only).
   The API verifies tokens with the project's JWKS; the service-role key is never needed by ReelForge.

## 2. Media (Cloudflare R2)

Create a private bucket and an API token scoped to it (Object Read & Write), then set
`REELFORGE_STORAGE_BACKEND=r2`, `REELFORGE_R2_ACCOUNT_ID`, `REELFORGE_R2_BUCKET`,
`REELFORGE_R2_ACCESS_KEY_ID`, `REELFORGE_R2_SECRET_ACCESS_KEY`, and `uv add boto3` in `backend/`. Media is
served through short-lived presigned URLs; never make the bucket public.

## 3. API and worker

```bash
REELFORGE_APP_ENV=production
REELFORGE_JWT_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))")
REELFORGE_PUBLIC_API_URL=https://api.example.com
REELFORGE_CORS_ORIGINS=https://reelforge.pages.dev
REELFORGE_EMBEDDED_WORKER=false
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers   # behind Caddy/nginx with TLS
uv run python -m app.workers.runner                                      # on the AI machine
```

Production start-up refuses default secrets, wildcard CORS and test providers. OpenAPI docs are disabled
in production.

## 4. Frontend (Cloudflare Pages)

Build command `npm ci && npm run build`, output `dist`, root `frontend`. Set `VITE_API_URL` (and the
Supabase variables if used). Add a `_redirects` file containing `/* /index.html 200` for client-side routes.

## 5. Checklist

- [ ] HTTPS everywhere; HSTS is sent automatically in production
- [ ] Ollama/ComfyUI ports not reachable from the internet
- [ ] Backups for PostgreSQL and the R2 bucket
- [ ] Terms of service include the CreativeML OpenRAIL-M use restrictions for generated images
- [ ] Monitoring of the worker process and disk usage of `work_root`
