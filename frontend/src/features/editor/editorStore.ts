import { create } from "zustand";
import type { Scene } from "@/types/api";

type EditorState = {
  selectedId: string | null;
  playhead: number; // seconds on the last-render timeline
  monitor: "scene" | "render";
  select: (id: string | null) => void;
  setPlayhead: (t: number) => void;
  setMonitor: (m: "scene" | "render") => void;
};

export const useEditor = create<EditorState>((set) => ({
  selectedId: null,
  playhead: 0,
  monitor: "scene",
  select: (selectedId) => set({ selectedId }),
  setPlayhead: (playhead) => set({ playhead }),
  setMonitor: (monitor) => set({ monitor }),
}));

const TRANSITION_SECONDS: Record<string, number> = { cut: 0, fade_black: 0.7, fade_white: 0.6, zoom: 0.45, pixelize: 0.5 };
const WORDS_PER_SECOND = 2.45;

export type TimelineBlock = { scene: Scene; start: number; duration: number; narrationStart: number; narrationSeconds: number; estimated: boolean };

/** Mirrors backend media/assembler.plan_timeline so the timeline matches the render. */
export function planTimeline(scenes: Scene[]): { blocks: TimelineBlock[]; total: number } {
  let cursor = 0;
  const blocks = scenes.map((scene, i) => {
    const estimated = scene.narration_seconds == null;
    const narrationSeconds = scene.narration_seconds ?? scene.narration.split(/\s+/).filter(Boolean).length / WORDS_PER_SECOND;
    const trans = i === 0 ? 0 : (TRANSITION_SECONDS[scene.transition] ?? 0.55);
    const offset = trans + 0.18;
    const duration = Math.max(2, offset + narrationSeconds + 0.3, scene.duration_override ?? 0);
    const start = Math.max(0, cursor - trans);
    cursor = start + duration;
    return { scene, start, duration, narrationStart: start + offset, narrationSeconds, estimated };
  });
  return { blocks, total: cursor };
}
