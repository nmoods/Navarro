import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { isTerminal } from "@/lib/format";
import { accountApi, jobsApi } from "@/services/endpoints";
import type { Job } from "@/types/api";

export const keys = {
  options: ["options"] as const,
  dashboard: ["dashboard"] as const,
  providers: ["providers"] as const,
  projects: (params?: object) => ["projects", params ?? {}] as const,
  project: (id: string) => ["project", id] as const,
  storyboard: (id: string) => ["project", id, "storyboard"] as const,
  script: (id: string) => ["project", id, "script"] as const,
  exports: (id: string) => ["project", id, "exports"] as const,
  projectJobs: (id: string) => ["project", id, "jobs"] as const,
  job: (id: string) => ["job", id] as const,
  activeJobs: ["jobs", "active"] as const,
  media: (params?: object) => ["media", params ?? {}] as const,
  dna: ["story-dna"] as const,
  voices: ["voices"] as const,
  voiceProfiles: ["voice-profiles"] as const,
  templates: ["templates"] as const,
  music: ["music"] as const,
  series: ["series"] as const,
  seriesOne: (id: string) => ["series", id] as const,
  ideas: (params?: object) => ["ideas", params ?? {}] as const,
  allExports: ["exports"] as const,
};

export function useOptions() {
  return useQuery({ queryKey: keys.options, queryFn: accountApi.options, staleTime: Infinity });
}

export function useProviders() {
  return useQuery({ queryKey: keys.providers, queryFn: accountApi.providers, staleTime: 30_000, refetchInterval: 60_000 });
}

/**
 * Poll a job until it reaches a terminal state, then invalidate whatever it affected.
 * `onDone` fires exactly once per job id.
 */
export function useJob(jobId: string | null | undefined, onDone?: (job: Job) => void) {
  const client = useQueryClient();
  const fired = useRef<string | null>(null);
  const query = useQuery({
    queryKey: keys.job(jobId ?? "none"),
    queryFn: () => jobsApi.get(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (q) => (q.state.data && isTerminal(q.state.data.status) ? false : 1500),
  });
  const job = query.data;
  useEffect(() => {
    if (!job || !isTerminal(job.status) || fired.current === job.id) return;
    fired.current = job.id;
    if (job.project_id) client.invalidateQueries({ queryKey: ["project", job.project_id] });
    if (job.series_id) client.invalidateQueries({ queryKey: keys.series });
    client.invalidateQueries({ queryKey: keys.dashboard });
    client.invalidateQueries({ queryKey: ["projects"] });
    onDone?.(job);
  }, [job, client, onDone]);
  return query;
}
