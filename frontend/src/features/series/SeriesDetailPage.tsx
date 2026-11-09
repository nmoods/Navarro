import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { ErrorNotice, PageHeader, StatusDot } from "@/components/common";
import { JobProgress } from "@/components/JobProgress";
import { Button } from "@/components/ui/button";
import { keys, useJob } from "@/hooks/queries";
import { isTerminal, label } from "@/lib/format";
import { jobsApi, planningApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";

const EP_STATUS: Record<string, string> = { planned: "draft", producing: "producing", completed: "ready", failed: "failed" };

export default function SeriesDetailPage() {
  const { seriesId = "" } = useParams();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [jobId, setJobId] = useState<string | null>(null);
  const series = useQuery({
    queryKey: keys.seriesOne(seriesId),
    queryFn: () => planningApi.getSeries(seriesId),
    refetchInterval: (q) => (q.state.data && ["planning", "producing"].includes(q.state.data.status) ? 3000 : false),
  });
  const active = useQuery({ queryKey: keys.activeJobs, queryFn: () => jobsApi.list(true), refetchInterval: 4000 });
  const planJob = active.data?.find((j) => j.series_id === seriesId && !j.parent_job_id);
  const job = useJob(jobId ?? planJob?.id, () => { setJobId(null); qc.invalidateQueries({ queryKey: keys.seriesOne(seriesId) }); }).data;

  const produce = useMutation({
    mutationFn: (quality: "draft" | "final") => planningApi.produceSeries(seriesId, { quality }),
    onSuccess: (j) => { setJobId(j.id); toast("Episodes queued. They render one after another."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const replan = useMutation({ mutationFn: () => planningApi.replan(seriesId), onSuccess: (j) => setJobId(j.id), onError: (e) => toast.error(errorMessage(e)) });
  const remove = useMutation({ mutationFn: () => planningApi.removeSeries(seriesId), onSuccess: () => navigate("/series") });

  if (series.error) return <Page><ErrorNotice error={series.error} /></Page>;
  const s = series.data;
  if (!s) return <Page><p className="text-sm text-faint">Loading…</p></Page>;
  const bible = s.bible;
  const childJobs = active.data?.filter((j) => j.series_id === seriesId && j.parent_job_id) ?? [];

  return (
    <Page>
      <PageHeader
        title={s.title}
        description={bible.logline ?? s.theme}
        actions={
          <>
            <Button variant="outline" onClick={() => replan.mutate()} disabled={s.status === "planning" || s.status === "producing"}>Replan unstarted episodes</Button>
            <Button variant="outline" onClick={() => produce.mutate("draft")} disabled={!s.episodes.length || s.status === "producing"}>Produce drafts</Button>
            <Button onClick={() => produce.mutate("final")} disabled={!s.episodes.length || s.status === "producing"}>Produce all episodes</Button>
          </>
        }
      />
      {job && !isTerminal(job.status) && <div className="mb-6"><JobProgress job={job} /></div>}
      {s.status === "planning" && !job && <p className="mb-6 text-sm text-beam">The Story Director is planning the episodes and the series bible…</p>}

      <div className="grid gap-10 lg:grid-cols-[1.5fr_1fr]">
        <section>
          <h2 className="mb-3 text-lg font-semibold">Episodes</h2>
          <ol className="divide-y divide-line rounded-xl border border-line">
            {s.episodes.map((ep) => {
              const running = childJobs.find((j) => j.project_id === ep.project_id);
              return (
                <li key={ep.id} className="grid gap-1 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-medium"><span className="timecode mr-2 text-sm">{String(ep.position + 1).padStart(2, "0")}</span>{ep.title}</p>
                    <StatusDot status={EP_STATUS[ep.status] ?? ep.status} label={running ? `${Math.round(running.progress)}%` : label(ep.status)} />
                  </div>
                  <p className="text-sm text-subtle">{ep.premise}</p>
                  {ep.hook && <p className="text-sm text-faint">Hook: {ep.hook}</p>}
                  {ep.error && <p className="text-sm text-bad">{ep.error}</p>}
                  {ep.project_id && <Link to={`/projects/${ep.project_id}`} className="text-sm text-uv hover:underline">Open in editor</Link>}
                </li>
              );
            })}
            {!s.episodes.length && <li className="p-4 text-sm text-faint">Episodes appear here once planning finishes.</li>}
          </ol>
        </section>
        <aside className="grid content-start gap-6">
          <h2 className="text-lg font-semibold">Series bible</h2>
          <p className="-mt-4 text-sm text-faint">Reused in every episode so characters and places stay consistent. Characters keep the same image seed across episodes.</p>
          {bible.visual_style_notes && <div><p className="text-xs text-faint">Visual style</p><p className="mt-1 text-sm">{bible.visual_style_notes}</p></div>}
          {bible.recurring_characters?.length ? (
            <div>
              <p className="text-xs text-faint">Recurring characters</p>
              <ul className="mt-1 grid gap-2 text-sm">{bible.recurring_characters.map((c) => <li key={c.name}><span className="text-text">{c.name}</span> <span className="text-subtle">— {c.visual_description}</span></li>)}</ul>
            </div>
          ) : null}
          {bible.recurring_locations?.length ? (
            <div><p className="text-xs text-faint">Locations</p><p className="mt-1 text-sm">{bible.recurring_locations.join(", ")}</p></div>
          ) : null}
          <Button variant="ghost" className="justify-self-start text-bad hover:text-bad" onClick={() => confirm("Delete this series? Episode projects are kept.") && remove.mutate()}>Delete series</Button>
        </aside>
      </div>
    </Page>
  );
}
