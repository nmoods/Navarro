import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, CircleHelp, ExternalLink, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { projectsApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Claim, Script, StoryboardAnalysis } from "@/types/api";

const VERDICT = {
  supported: { icon: CheckCircle2, tone: "text-ok", text: "Supported by source" },
  contradicted: { icon: XCircle, tone: "text-bad", text: "Contradicted by source" },
  not_found: { icon: CircleHelp, tone: "text-warn", text: "Not found in sources" },
  unverified: { icon: CircleHelp, tone: "text-faint", text: "Not checked" },
} as const;

function ClaimRow({ claim }: { claim: Claim }) {
  const v = VERDICT[claim.verdict] ?? VERDICT.unverified;
  const Icon = v.icon;
  return (
    <li className="grid grid-cols-[1rem_1fr] gap-2 py-3">
      <Icon className={cn("mt-0.5 size-4", v.tone)} aria-hidden />
      <div className="min-w-0 text-sm">
        <p className="text-text">{claim.text}</p>
        <p className="mt-1 text-xs text-faint">
          <span className={v.tone}>{v.text}</span> · {label(claim.confidence)}
          {claim.note && ` · ${claim.note}`}
        </p>
        {claim.sources.map((s) => (
          <a key={s} href={s} target="_blank" rel="noreferrer noopener" className="mt-1 inline-flex items-center gap-1 text-xs text-uv hover:underline">
            Source <ExternalLink className="size-3" />
          </a>
        ))}
      </div>
    </li>
  );
}

export function ScriptPanel({ script, analysis, projectId, busy, onJob }: { script: Script; analysis?: StoryboardAnalysis; projectId: string; busy: boolean; onJob: (id: string) => void }) {
  const pick = useMutation({
    mutationFn: (i: number) => projectsApi.selectHook(projectId, i),
    onSuccess: (job) => { onJob(job.id); toast("Rebuilding the script and storyboard around this hook."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const flagged = script.claims.filter((c) => c.verdict === "contradicted" || c.verdict === "not_found" || c.confidence === "uncertain");

  return (
    <div className="grid gap-8 p-4">
      <section>
        <h3 className="text-sm font-semibold">Hook Lab</h3>
        <p className="mt-1 text-xs text-faint">The first two seconds decide whether people stay. Choosing a different hook rewrites the script around it.</p>
        <ul className="mt-3 grid gap-2">
          {script.hooks.map((h, i) => {
            const active = i === script.selected_hook_index;
            return (
              <li key={i} className={cn("rounded-lg border p-3", active ? "border-uv bg-uv/10" : "border-line")}>
                <p className="text-xs text-faint">{label(h.style)}{active && " · in use"}</p>
                <p className="mt-1 text-sm">{h.text}</p>
                {!active && (
                  <Button size="sm" variant="ghost" className="mt-1 h-7 px-2 text-uv" disabled={busy || pick.isPending} onClick={() => pick.mutate(i)}>
                    Build around this hook
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-semibold">Fact check</h3>
        <p className="mt-1 text-xs text-faint">
          {flagged.length ? `${flagged.length} claim${flagged.length > 1 ? "s" : ""} need your attention before publishing.` : "No flagged claims. Still read the script once before publishing."}
        </p>
        <ul className="mt-2 divide-y divide-line">{script.claims.map((c, i) => <ClaimRow key={i} claim={c} />)}</ul>
        {script.brief.sources?.length ? (
          <p className="mt-2 text-xs text-faint">
            Research: {script.brief.sources.map((s, i) => (
              <a key={s.url} href={s.url} target="_blank" rel="noreferrer noopener" className="text-uv hover:underline">{s.title}{i < (script.brief.sources?.length ?? 0) - 1 ? ", " : ""}</a>
            ))}
          </p>
        ) : null}
      </section>

      {analysis && (
        <section>
          <h3 className="text-sm font-semibold">Pacing</h3>
          <p className="mt-1 text-xs text-faint">{analysis.total_words} words, about {Math.round(analysis.estimated_seconds)} seconds of narration.</p>
          <div className="mt-3 flex h-10 items-end gap-1" aria-label="Words per scene">
            {analysis.words_per_scene.map((n, i) => (
              <div key={i} className={cn("flex-1 rounded-t-sm", n > 40 ? "bg-warn/70" : "bg-uv/50")} style={{ height: `${Math.min(100, (n / 45) * 100)}%` }} title={`Scene ${i + 1}: ${n} words`} />
            ))}
          </div>
          {analysis.warnings.length > 0 && (
            <ul className="mt-3 grid gap-1 text-xs text-warn">{analysis.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
          )}
        </section>
      )}

      <section>
        <h3 className="text-sm font-semibold">Brief</h3>
        <dl className="mt-2 grid gap-2 text-sm">
          {script.brief.angle && <div><dt className="text-xs text-faint">Angle</dt><dd>{script.brief.angle}</dd></div>}
          {script.brief.target_audience && <div><dt className="text-xs text-faint">Audience</dt><dd>{script.brief.target_audience}</dd></div>}
          {script.brief.emotional_arc && <div><dt className="text-xs text-faint">Arc</dt><dd>{script.brief.emotional_arc}</dd></div>}
        </dl>
        <p className="mt-3 text-xs text-faint">Written by {script.model ?? "the Story Director"} · version {script.version}</p>
      </section>
    </div>
  );
}
