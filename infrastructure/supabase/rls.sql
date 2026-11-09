-- ReelForge AI: Row Level Security for Supabase PostgreSQL.
--
-- Apply AFTER `alembic upgrade head` has created the schema:
--   psql "$SUPABASE_DB_URL" -f infrastructure/supabase/rls.sql
--
-- Model:
--  * The ReelForge API connects with a privileged role (table owner / service role) that bypasses RLS and
--    enforces ownership in application code on every query (see backend/app/api/deps.py::owned).
--  * RLS is defence in depth: if anyone reaches the database through Supabase's auto-generated REST/GraphQL
--    APIs with an end-user JWT (or the anon key), they can only ever see their own rows, and never write
--    queue/audit/token tables at all.
--  * In auth_mode=supabase, users.external_id holds the Supabase auth user id (auth.uid()).

begin;

create or replace function public.app_user_id() returns uuid
  language sql stable security definer set search_path = public as $$
    select id from public.users where external_id = auth.uid()::text
  $$;
revoke all on function public.app_user_id() from public;
grant execute on function public.app_user_id() to authenticated;

-- Enable RLS everywhere. Tables without a policy below are therefore closed to anon/authenticated.
do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public' and tablename <> 'alembic_version' loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('revoke all on public.%I from anon', t);
  end loop;
end $$;

-- Tables that carry user_id directly: owner-only read/write.
do $$
declare t text;
begin
  foreach t in array array[
    'projects', 'story_dna_profiles', 'voice_profiles', 'media_assets', 'video_exports',
    'content_series', 'content_ideas'
  ] loop
    execute format('drop policy if exists owner_all on public.%I', t);
    execute format(
      'create policy owner_all on public.%I for all to authenticated using (user_id = public.app_user_id()) with check (user_id = public.app_user_id())', t);
  end loop;
end $$;

-- Read-only to the owner (written only by the API/worker).
drop policy if exists owner_read on public.generation_jobs;
create policy owner_read on public.generation_jobs for select to authenticated using (user_id = public.app_user_id());

drop policy if exists owner_read on public.generation_job_logs;
create policy owner_read on public.generation_job_logs for select to authenticated
  using (exists (select 1 from public.generation_jobs j where j.id = job_id and j.user_id = public.app_user_id()));

-- Children of projects: access follows the parent project.
do $$
declare t text;
begin
  foreach t in array array['project_settings', 'scripts', 'storyboards', 'scenes'] loop
    execute format('drop policy if exists via_project on public.%I', t);
    execute format(
      'create policy via_project on public.%I for all to authenticated
         using (exists (select 1 from public.projects p where p.id = project_id and p.user_id = public.app_user_id()))
         with check (exists (select 1 from public.projects p where p.id = project_id and p.user_id = public.app_user_id()))', t);
  end loop;
end $$;

drop policy if exists via_scene on public.scene_assets;
create policy via_scene on public.scene_assets for all to authenticated
  using (exists (select 1 from public.scenes s join public.projects p on p.id = s.project_id
                 where s.id = scene_id and p.user_id = public.app_user_id()));

drop policy if exists via_series on public.series_episodes;
create policy via_series on public.series_episodes for all to authenticated
  using (exists (select 1 from public.content_series c where c.id = series_id and c.user_id = public.app_user_id()))
  with check (exists (select 1 from public.content_series c where c.id = series_id and c.user_id = public.app_user_id()));

-- Profiles and the user row itself: self only.
drop policy if exists self_read on public.users;
create policy self_read on public.users for select to authenticated using (id = public.app_user_id());
drop policy if exists self_all on public.profiles;
create policy self_all on public.profiles for all to authenticated using (user_id = public.app_user_id()) with check (user_id = public.app_user_id());

-- Shared catalogues: built-in/public rows readable by any signed-in user; own rows fully editable.
drop policy if exists catalogue_read on public.templates;
create policy catalogue_read on public.templates for select to authenticated using (is_public or is_builtin or user_id = public.app_user_id());
drop policy if exists owner_write on public.templates;
create policy owner_write on public.templates for all to authenticated using (user_id = public.app_user_id()) with check (user_id = public.app_user_id() and not is_builtin);

do $$
declare t text;
begin
  foreach t in array array['music_tracks', 'sound_effects'] loop
    execute format('drop policy if exists catalogue_read on public.%I', t);
    execute format('create policy catalogue_read on public.%I for select to authenticated using (user_id is null or user_id = public.app_user_id())', t);
    execute format('drop policy if exists owner_write on public.%I', t);
    execute format('create policy owner_write on public.%I for all to authenticated using (user_id = public.app_user_id()) with check (user_id = public.app_user_id())', t);
  end loop;
end $$;

-- refresh_tokens and audit_logs: RLS enabled with no policy => inaccessible to anon/authenticated.

commit;
