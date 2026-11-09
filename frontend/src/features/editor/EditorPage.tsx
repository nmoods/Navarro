import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, Eye, Film } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ErrorNotice, ProviderBanner, StatusDot } from "@/components/common";
import { JobProgress } from "@/components/JobProgress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { keys, useJob } from "@/hooks/queries";
import { isTerminal } from "@/lib/format";
import { projectsApi } from "@/services/endpoints";
import { ApiError, errorMessage } from "@/services/http";
import type { Job } from "@/types/api";
import { useEditor } from "./editorStore";
import { Monitor } from "./Monitor";
import { ProjectSettingsPanel } from "./ProjectSettingsPanel";
import { SceneInspector } from "./SceneInspector";
import { SceneList } from "./SceneList";
import { ScriptPanel } from "./ScriptPanel";
import { Timeline } from "./Timeline";

async function downloadSubtitles(projectId: string, title: string) {
  try {
    const url = await projectsApi.subtitles(projectId, "srt");
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.srt`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  } catch (e) {
    toast.error(errorMessage(e));
  }
}

export default function EditorPage() {
  const { projectId = "" } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { selectedId, select, setMonitor } = useEditor();
  const [jobId, setJobId] = useState<string | null>(null);

  const project = useQuery({ queryKey: keys.project(projectId), queryFn: () => projectsApi.get(projectId) });
  const jobs = useQuery({ queryKey: keys.projectJobs(projectId), queryFn: () => projectsApi.jobs(projectId) });
  const storyboard = useQuery({
    queryKey: keys.storyboard(projectId),
    queryFn: () => projectsApi.storyboard(projectId),
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 2,
  });
  const script = useQuery({ queryKey: keys.script(projectId), queryFn: () => projectsApi.script(projectId), retry: false, enabled: storyboard.isSuccess });
  const exports = useQuery({ queryKey: keys.exports(projectId), queryFn: () => projectsApi.exports(projectId) });

  // Pick up a job already running for this project (e.g. right after creation).
  useEffect(() => {
    const active = jobs.data?.find((j) => !isTerminal(j.status));
    if (active && !jobId) setJobId(active.id);
  }, [jobs.data, jobId]);

  const onDone = useCallback(
    (job: Job) => {
      qc.invalidateQueries({ queryKey: keys.projectJobs(projectId) });
      if (job.status === "completed") {
        if (job.job_type === "production" || job.job_type === "preview") {
          toast.success(job.job_type === "preview" ? "Preview ready" : "Video exported");
          setMonitor("render");
        }
      } else if (job.status === "failed") toast.error(job.error ?? "The job failed");
      setJobId(null);
    },
    [qc, projectId, setMonitor],
  );
  const job = useJob(jobId, onDone).data;
  const busy = Boolean(job && !isTerminal(job.status));

  const scenes = useMemo(() => storyboard.data?.scenes ?? [], [storyboard.data]);
  useEffect(() => {
    if (scenes.length && !scenes.some((s) => s.id === selectedId)) select(scenes[0].id);
  }, [scenes, selectedId, select]);
  useEffect(() => () => { select(null); setMonitor("scene"); }, [select, setMonitor]);

  const produce = useMutation({
    mutationFn: (quality: "draft" | "final") => projectsApi.produce(projectId, quality),
    onSuccess: (j) => setJobId(j.id),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const generate = useMutation({
    mutationFn: () => projectsApi.generateStory(projectId),
    onSuccess: (j) => setJobId(j.id),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const rename = useMutation({
    mutationFn: (title: string) => projectsApi.update(projectId, { title }),
    onSuccess: (p) => qc.setQueryData(keys.project(projectId), p),
  });

  if (project.error) {
    return (
      <div className="p-8">
        <ErrorNotice error={project.error} />
        <Button variant="ghost" className="mt-4" onClick={() => navigate("/projects")}>Back to projects</Button>
      </div>
    );
  }
  const p = project.data;
  const latest = exports.data?.[0];
  const latestTime = latest ? new Date(latest.created_at).getTime() : 0;
  const stale = Boolean(latest && scenes.some((s) => new Date(s.updated_at).getTime() > latestTime));
  const selectedIndex = scenes.findIndex((s) => s.id === selectedId);
  const selected = scenes[selectedIndex];
  const noStoryboard = storyboard.error instanceof ApiError && storyboard.error.status === 404;

  return (
    <div className="flex h-dvh flex-col lg:h-dvh">
      <header className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-2.5">
        <Button asChild variant="ghost" size="icon" aria-label="Back to projects"><Link to="/projects"><ArrowLeft className="size-4" /></Link></Button>
        <div className="min-w-0 flex-1">
          {p && (
            <Input
              key={p.title}
              defaultValue={p.title}
              aria-label="Project title"
              onBlur={(e) => e.target.value.trim() && e.target.value !== p.title && rename.mutate(e.target.value.trim())}
              className="h-8 max-w-xl border-transparent bg-transparent px-1 font-heading text-lg font-semibold focus-visible:border-line"
            />
          )}
        </div>
        {p && <StatusDot status={p.status} />}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={busy || !scenes.length} onClick={() => produce.mutate("draft")}><Eye className="size-4" /> Preview</Button>
          <Button size="sm" disabled={busy || !scenes.length} onClick={() => produce.mutate("final")}><Film className="size-4" /> Export video</Button>
          {latest && latest.quality === "final" && (
            <Button asChild size="sm" variant="outline"><a href={latest.download_url}><Download className="size-4" /> MP4</a></Button>
          )}
          {latest && (
            <Button size="sm" variant="ghost" onClick={() => downloadSubtitles(projectId, p?.title ?? "subtitles")}>SRT</Button>
          )}
        </div>
      </header>

      <div className="px-4 pt-3">
        <ProviderBanner />
        {job && !isTerminal(job.status) && (noStoryboard || !scenes.length) && <div className="mb-3"><JobProgress job={job} /></div>}
        {p?.status === "failed" && p.last_error && !busy && <ErrorNotice error={new Error(p.last_error)} className="mb-3" />}
      </div>

      {noStoryboard && !busy ? (
        <div className="m-4 grid place-items-start gap-3 rounded-xl border border-dashed border-line-strong p-8">
          <h2 className="text-xl font-semibold">No storyboard yet</h2>
          <p className="max-w-md text-sm text-subtle">The Story Director will research “{p?.topic}”, write hooks and a script, then direct each scene.</p>
          <Button onClick={() => generate.mutate()} disabled={generate.isPending}>Write the storyboard</Button>
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[300px_1fr_360px]">
          <aside className="min-h-0 border-r border-line">
            <Tabs defaultValue="scenes" className="flex h-full flex-col">
              <TabsList className="mx-2 mt-2">
                <TabsTrigger value="scenes">Scenes</TabsTrigger>
                <TabsTrigger value="script">Script</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
              </TabsList>
              <ScrollArea className="min-h-0 flex-1">
                <TabsContent value="scenes"><SceneList scenes={scenes} projectId={projectId} /></TabsContent>
                <TabsContent value="script">
                  {script.data ? <ScriptPanel script={script.data} analysis={storyboard.data?.analysis} projectId={projectId} busy={busy} onJob={setJobId} /> : <p className="p-4 text-sm text-faint">The script appears once the Story Director finishes.</p>}
                </TabsContent>
                <TabsContent value="settings">{p?.settings && <ProjectSettingsPanel project={p} />}</TabsContent>
              </ScrollArea>
            </Tabs>
          </aside>
          <section className="relative min-h-[420px] bg-[radial-gradient(70%_60%_at_50%_45%,rgba(91,63,217,0.09),transparent)]" aria-label="Monitor">
            {job && !isTerminal(job.status) && scenes.length > 0 && (
              <div className="absolute inset-x-4 top-3 z-10 shadow-lg shadow-black/40"><JobProgress job={job} compact /></div>
            )}
            {scenes.length > 0 ? (
              <Monitor scenes={scenes} latest={latest} ratio={p?.settings?.aspect_ratio ?? "9:16"} stale={stale} />
            ) : (
              <div className="flex h-full items-center justify-center p-8 text-sm text-faint">{busy ? "Scenes appear here as soon as the storyboard is ready." : "Loading…"}</div>
            )}
          </section>
          <aside className="min-h-0 border-l border-line">
            <ScrollArea className="h-full">
              {selected ? (
                <SceneInspector scene={selected} index={selectedIndex} projectId={projectId} busy={busy} onJob={setJobId} />
              ) : (
                <p className="p-4 text-sm text-faint">Select a scene to edit it.</p>
              )}
            </ScrollArea>
          </aside>
        </div>
      )}
      {scenes.length > 0 && <Timeline scenes={scenes} />}
    </div>
  );
}
