import { useEffect, useMemo, useRef } from "react";
import { AudioButton } from "@/components/common";
import { label, timecode } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Export, Scene } from "@/types/api";
import { planTimeline, useEditor } from "./editorStore";

const SOURCE_NOTE: Record<string, string> = {
  procedural: "Procedural art. ComfyUI was offline when this was made.",
  uploaded: "Your image, pinned to this scene.",
  fixture: "Test-mode image.",
};

/** Program monitor: shows the selected scene's frame or plays the latest render, with timecode. */
export function Monitor({ scenes, latest, ratio, stale }: { scenes: Scene[]; latest?: Export; ratio: string; stale: boolean }) {
  const { selectedId, monitor, setMonitor, setPlayhead, playhead, select } = useEditor();
  const video = useRef<HTMLVideoElement>(null);
  const scene = scenes.find((s) => s.id === selectedId) ?? scenes[0];
  const { blocks } = useMemo(() => planTimeline(scenes), [scenes]);
  const aspect = ratio === "16:9" ? "aspect-video" : ratio === "1:1" ? "aspect-square" : "frame-916";

  useEffect(() => {
    if (monitor !== "render") return;
    const current = blocks.find((b) => playhead >= b.start && playhead < b.start + b.duration);
    if (current && current.scene.id !== selectedId) select(current.scene.id);
  }, [playhead, monitor, blocks, select, selectedId]);

  const sceneStart = blocks.find((b) => b.scene.id === scene?.id)?.start ?? 0;

  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-4">
      <div className="flex gap-1 rounded-md border border-line p-0.5 text-xs" role="tablist" aria-label="Monitor source">
        {(["scene", "render"] as const).map((m) => (
          <button
            key={m}
            role="tab"
            aria-selected={monitor === m}
            disabled={m === "render" && !latest}
            onClick={() => setMonitor(m)}
            className={cn("rounded px-3 py-1", monitor === m ? "bg-raised text-text" : "text-faint hover:text-text disabled:opacity-40")}
          >
            {m === "scene" ? "Scene" : "Last render"}
          </button>
        ))}
      </div>
      <div className={cn("relative w-full overflow-hidden rounded-xl border border-line-strong bg-ink", aspect, ratio === "16:9" ? "max-w-[720px]" : "max-w-[300px] xl:max-w-[340px]")}>
        {monitor === "render" && latest ? (
          <video
            ref={video}
            key={latest.id}
            src={latest.video_url}
            poster={latest.thumbnail_url ?? undefined}
            controls
            playsInline
            className="size-full object-contain"
            onTimeUpdate={(e) => setPlayhead(e.currentTarget.currentTime)}
          />
        ) : scene?.image ? (
          <img src={scene.image.url} alt={scene.visual_description || scene.title} className="size-full object-cover" />
        ) : (
          <div className="flex size-full flex-col items-center justify-center gap-2 p-6 text-center">
            <p className="font-heading text-lg">{label(scene?.visual_type)}</p>
            <p className="text-xs text-faint">
              {["historical_map", "timeline", "infographic", "kinetic_typography"].includes(scene?.visual_type ?? "")
                ? "Drawn by the engine at render time. Preview the video to see it move."
                : "No image yet. It is generated when you preview or export."}
            </p>
          </div>
        )}
      </div>
      <div className="flex w-full max-w-[340px] items-center justify-between gap-3 text-xs text-faint">
        {monitor === "render" && latest ? (
          <>
            <span className="timecode">{timecode(playhead)} / {timecode(latest.duration_seconds)}</span>
            <span>{latest.quality === "draft" ? "Draft" : "Final"} · {latest.width}×{latest.height}</span>
          </>
        ) : scene ? (
          <>
            <span className="timecode">{timecode(sceneStart)}</span>
            <span className="truncate">{scene.image ? SOURCE_NOTE[scene.image.source] ?? label(scene.camera_movement) : label(scene.camera_movement)}</span>
            {scene.narration_audio && <AudioButton label="scene narration" load={async () => scene.narration_audio!.url} />}
          </>
        ) : null}
      </div>
      {stale && latest && <p className="text-xs text-warn">You’ve made changes since this render.</p>}
    </div>
  );
}
