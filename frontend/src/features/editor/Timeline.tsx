import { useMemo } from "react";
import { label, timecode } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Scene } from "@/types/api";
import { planTimeline, useEditor } from "./editorStore";

const TRACKS = ["Video", "Voice", "Captions", "Music", "SFX"] as const;

/** Multi-track timeline. Widths are proportional to real (or estimated) scene durations. */
export function Timeline({ scenes }: { scenes: Scene[] }) {
  const { selectedId, select, playhead, monitor } = useEditor();
  const { blocks, total } = useMemo(() => planTimeline(scenes), [scenes]);
  const pct = (t: number) => `${(t / Math.max(total, 0.001)) * 100}%`;
  const ticks = useMemo(() => {
    const step = total > 60 ? 10 : 5;
    return Array.from({ length: Math.floor(total / step) + 1 }, (_, i) => i * step);
  }, [total]);

  return (
    <section aria-label="Timeline" className="border-t border-line bg-surface">
      <div className="flex items-center justify-between px-4 py-2 text-xs text-faint">
        <span>Timeline</span>
        <span>
          <span className="timecode">{timecode(total)}</span> total
          {blocks.some((b) => b.estimated) && " · estimated until voiced"}
        </span>
      </div>
      <div className="scrollbar-thin overflow-x-auto px-4 pb-3">
        <div className="relative min-w-[720px]">
          <div className="relative ml-20 h-5 border-b border-line">
            {ticks.map((t) => (
              <span key={t} className="timecode absolute top-0 -translate-x-1/2 text-[10px] opacity-70" style={{ left: pct(t) }}>
                {timecode(t, false)}
              </span>
            ))}
          </div>
          {TRACKS.map((track) => (
            <div key={track} className="flex h-9 items-center border-b border-line/60 last:border-0">
              <span className="w-20 shrink-0 text-xs text-faint">{track}</span>
              <div className="relative h-7 flex-1">
                {blocks.map((b, i) => {
                  const selected = b.scene.id === selectedId;
                  const common = "absolute top-0.5 bottom-0.5 rounded-[5px] text-left text-[11px] leading-6 truncate px-1.5";
                  if (track === "Video")
                    return (
                      <button
                        type="button"
                        key={b.scene.id}
                        onClick={() => select(b.scene.id)}
                        className={cn(common, "border", selected ? "border-uv bg-uv/25 text-text" : "border-line-strong bg-raised text-subtle hover:border-uv/60")}
                        style={{ left: pct(b.start), width: pct(b.duration) }}
                        title={`${b.scene.title} · ${label(b.scene.visual_type)}`}
                      >
                        {i + 1}. {label(b.scene.visual_type)}
                      </button>
                    );
                  if (track === "Voice")
                    return (
                      <div
                        key={b.scene.id}
                        className={cn(common, b.estimated ? "border border-dashed border-line-strong" : "bg-beam/20", selected && "ring-1 ring-uv")}
                        style={{ left: pct(b.narrationStart), width: pct(b.narrationSeconds) }}
                        aria-hidden
                      />
                    );
                  if (track === "Captions")
                    return (
                      <div key={b.scene.id} className="absolute top-0.5 bottom-0.5 truncate text-[11px] leading-6 text-faint" style={{ left: pct(b.narrationStart), width: pct(b.narrationSeconds) }}>
                        {b.scene.emphasis_words.join(" · ") || "—"}
                      </div>
                    );
                  if (track === "Music")
                    return (
                      <div key={b.scene.id} className="absolute top-0.5 bottom-0.5 truncate border-l border-uv/40 pl-1 text-[11px] leading-6 text-faint" style={{ left: pct(b.start), width: pct(b.duration) }}>
                        {b.scene.music_cue}
                      </div>
                    );
                  return (
                    <div key={b.scene.id} className="absolute top-0.5 bottom-0.5 truncate text-[11px] leading-6 text-faint" style={{ left: pct(b.start), width: pct(b.duration) }}>
                      {[b.scene.transition !== "cut" && i > 0 ? "transition" : "", ...b.scene.sound_effects].filter(Boolean).join(", ")}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          {monitor === "render" && (
            <div className="pointer-events-none absolute bottom-0 top-5 w-px bg-beam" style={{ left: `calc(5rem + (100% - 5rem) * ${Math.min(1, playhead / Math.max(total, 0.001))})` }} aria-hidden />
          )}
        </div>
      </div>
    </section>
  );
}
