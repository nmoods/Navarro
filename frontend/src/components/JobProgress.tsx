import { Loader2, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { JOB_STAGES, STAGE_LABEL, isTerminal, timecode } from "@/lib/format";
import { cn } from "@/lib/utils";
import { jobsApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Job } from "@/types/api";

const RELEVANT: Record<Job["job_type"], readonly string[]> = {
  story: ["script_generation", "storyboard_generation"],
  production: JOB_STAGES,
  preview: ["image_generation", "voice_generation", "animation", "rendering", "finalizing"],
  scene_regeneration: ["storyboard_generation", "image_generation", "voice_generation"],
  series_plan: ["script_generation"],
  series_production: ["finalizing"],
};

/** Seconds since the job started, ticking while it runs. */
function useElapsed(job: Job): number | null {
  const [now, setNow] = useState(() => Date.now());
  const running = !isTerminal(job.status);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);
  if (!job.started_at) return null;
  const end = job.finished_at ? new Date(job.finished_at).getTime() : now;
  return Math.max(0, (end - new Date(job.started_at).getTime()) / 1000);
}

/** Stage strip + progress beam for a running job, with elapsed time and cancel. */
export function JobProgress({ job, compact = false }: { job: Job; compact?: boolean }) {
  const cancel = useMutation({
    mutationFn: () => jobsApi.cancel(job.id),
    onSuccess: () => toast("Cancelling. The current step finishes first."),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const stages = RELEVANT[job.job_type] ?? JOB_STAGES;
  const current = stages.indexOf(job.status);
  const running = !isTerminal(job.status);
  const elapsed = useElapsed(job);

  return (
    <div className={cn("rounded-lg border border-line bg-surface", compact ? "p-3" : "p-4")} aria-live="polite">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          {running && <Loader2 className="size-4 shrink-0 animate-spin text-beam" aria-hidden />}
          <p className="truncate text-sm text-text">{job.stage_message}</p>
        </div>
        <div className="flex items-center gap-2">
          {elapsed !== null && <span className="timecode text-xs text-faint" title="Elapsed time">{timecode(elapsed, false)}</span>}
          <span className="timecode text-sm">{Math.round(job.progress)}%</span>
          {running && (
            <Button size="sm" variant="ghost" onClick={() => cancel.mutate()} disabled={cancel.isPending} aria-label="Cancel job">
              <X className="size-4" />
            </Button>
          )}
        </div>
      </div>
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-raised" role="progressbar" aria-valuenow={Math.round(job.progress)} aria-valuemin={0} aria-valuemax={100}>
        <div
          className={cn("h-full rounded-full transition-[width] duration-700", job.status === "failed" ? "bg-bad" : "bg-beam")}
          style={{ width: `${Math.max(2, job.progress)}%` }}
        />
      </div>
      {!compact && stages.length > 1 && (
        <ol className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {stages.map((stage, i) => (
            <li
              key={stage}
              className={cn(
                i < current || job.status === "completed" ? "text-subtle" : i === current ? "text-beam" : "text-faint",
              )}
            >
              {STAGE_LABEL[stage]}
            </li>
          ))}
        </ol>
      )}
      {job.status === "failed" && job.error && <p className="mt-3 text-sm text-bad">{job.error}</p>}
    </div>
  );
}
