import { useQuery } from "@tanstack/react-query";
import { Film, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { Page } from "@/app/AppShell";
import { EmptyState, ErrorNotice, PageHeader, ProviderBanner, StatusDot } from "@/components/common";
import { JobProgress } from "@/components/JobProgress";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { keys } from "@/hooks/queries";
import { STAGE_LABEL, isTerminal, label, relativeTime, timecode } from "@/lib/format";
import { accountApi } from "@/services/endpoints";
import { useAuth } from "@/stores/auth";
import type { Project } from "@/types/api";

export function ProjectTile({ project }: { project: Project }) {
  return (
    <Link to={`/projects/${project.id}`} className="group block">
      <div className="frame-916 overflow-hidden rounded-lg border border-line bg-raised group-hover:border-uv/60">
        {project.thumbnail_url ? (
          <img src={project.thumbnail_url} alt="" className="size-full object-cover" loading="lazy" />
        ) : (
          <div className="flex size-full items-end p-3 text-xs text-faint">No render yet</div>
        )}
      </div>
      <p className="mt-2 line-clamp-2 text-sm font-medium group-hover:text-uv">{project.title}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <StatusDot status={project.status} />
        <span className="text-xs text-faint">{relativeTime(project.updated_at)}</span>
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const user = useAuth((s) => s.user);
  const { data, isLoading, error } = useQuery({ queryKey: keys.dashboard, queryFn: accountApi.dashboard, refetchInterval: 5000 });
  const running = data?.activity.filter((j) => !isTerminal(j.status) && !j.parent_job_id) ?? [];

  return (
    <Page>
      <PageHeader
        title={`Welcome back${user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""}`}
        actions={
          <>
            <Button asChild variant="outline"><Link to="/series"><Film className="size-4" /> Plan a series</Link></Button>
            <Button asChild><Link to="/create"><Plus className="size-4" /> New video</Link></Button>
          </>
        }
      />
      <ProviderBanner />
      {error ? <ErrorNotice error={error} /> : null}

      {running.length > 0 && (
        <section className="mb-10 grid gap-3" aria-label="In production">
          <h2 className="text-lg font-semibold">In production</h2>
          {running.map((job) => (
            <Link key={job.id} to={job.project_id ? `/projects/${job.project_id}` : `/series/${job.series_id}`}>
              <JobProgress job={job} compact />
            </Link>
          ))}
        </section>
      )}

      {data && (
        <dl className="mb-10 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
          {[
            ["Projects", data.stats.projects],
            ["Exports", data.stats.exports],
            ["Series", data.stats.series],
            ["Minutes rendered", data.stats.minutes_rendered],
          ].map(([name, value]) => (
            <div key={name} className="bg-surface p-4">
              <dt className="text-xs text-faint">{name}</dt>
              <dd className="mt-1 font-heading text-2xl font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      )}

      <section className="mb-12">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Recent projects</h2>
          <Link to="/projects" className="text-sm text-uv hover:underline">All projects</Link>
        </div>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="frame-916 w-full" />)}
          </div>
        ) : data?.recent_projects.length ? (
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">
            {data.recent_projects.map((p) => <ProjectTile key={p.id} project={p} />)}
          </div>
        ) : (
          <EmptyState
            title="No projects yet"
            body="Start with a subject you find fascinating. The Story Director drafts the script and storyboard for you to review."
            action={<Button asChild><Link to="/create">Create your first video</Link></Button>}
          />
        )}
      </section>

      <div className="grid gap-10 lg:grid-cols-2">
        <section>
          <h2 className="mb-4 text-lg font-semibold">Recent exports</h2>
          {data?.recent_exports.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {data.recent_exports.map((e) => (
                <li key={e.id} className="flex items-center gap-3 p-3">
                  {e.thumbnail_url && <img src={e.thumbnail_url} alt="" className="h-12 w-[27px] rounded object-cover" />}
                  <div className="min-w-0 flex-1">
                    <Link to={`/projects/${e.project_id}`} className="block truncate text-sm hover:text-uv">{e.project_title}</Link>
                    <p className="text-xs text-faint">
                      {e.quality === "draft" ? "Draft preview" : "Final"} · {e.width}×{e.height} · <span className="timecode">{timecode(e.duration_seconds, false)}</span>
                    </p>
                  </div>
                  <Button asChild size="sm" variant="outline"><a href={e.download_url}>Download</a></Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-subtle">Finished videos appear here.</p>
          )}
        </section>
        <section>
          <h2 className="mb-4 text-lg font-semibold">Generation activity</h2>
          {data?.activity.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line text-sm">
              {data.activity.map((j) => (
                <li key={j.id} className="flex items-center justify-between gap-3 p-3">
                  <span className="truncate">{label(j.job_type)}</span>
                  <span className="flex shrink-0 items-center gap-3 text-xs text-faint">
                    <StatusDot status={j.status} label={STAGE_LABEL[j.status]} />
                    {relativeTime(j.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-subtle">Jobs you start appear here with their progress.</p>
          )}
          {data?.templates.length ? (
            <div className="mt-8">
              <h2 className="mb-3 text-lg font-semibold">Start from a template</h2>
              <div className="flex flex-wrap gap-2">
                {data.templates.map((t) => (
                  <Button key={t.id} asChild variant="outline" size="sm"><Link to={`/create?template=${t.id}`}>{t.name}</Link></Button>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </Page>
  );
}
