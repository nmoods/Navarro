import { describe, expect, it } from "vitest";
import { registerSchema } from "@/features/auth/AuthPages";
import { planTimeline } from "@/features/editor/editorStore";
import { createSchema } from "@/features/video-generator/CreateVideoPage";
import { isTerminal, label, timecode } from "@/lib/format";
import { scene } from "./fixtures";

describe("format helpers", () => {
  it("humanises enum values", () => {
    expect(label("slow_zoom_in")).toBe("Slow zoom in");
    expect(label("9:16")).toBe("Vertical 9:16");
    expect(label("historical_map")).toBe("Animated map");
  });
  it("formats timecode", () => {
    expect(timecode(74.34)).toBe("01:14.3");
    expect(timecode(5, false)).toBe("00:05");
  });
  it("knows terminal job states", () => {
    expect(isTerminal("completed")).toBe(true);
    expect(isTerminal("rendering")).toBe(false);
  });
});

describe("planTimeline mirrors the backend renderer", () => {
  it("overlaps transitions and keeps narration from colliding", () => {
    const scenes = [
      scene({ transition: "cut", narration_seconds: 4 }),
      scene({ transition: "crossfade", narration_seconds: 3 }),
      scene({ transition: "cut", narration_seconds: 2 }),
    ];
    const { blocks, total } = planTimeline(scenes);
    // scene 1: 0.18 + 4 + 0.3 = 4.48
    expect(blocks[0].duration).toBeCloseTo(4.48);
    // scene 2 starts 0.55s early (crossfade overlap)
    expect(blocks[1].start).toBeCloseTo(4.48 - 0.55);
    // its narration starts after the previous narration ended
    expect(blocks[1].narrationStart).toBeGreaterThan(blocks[0].narrationStart + 4);
    expect(total).toBeCloseTo(blocks[2].start + blocks[2].duration);
  });
  it("respects minimum durations and estimates unvoiced scenes", () => {
    const { blocks } = planTimeline([scene({ narration: "short", duration_override: 6 })]);
    expect(blocks[0].duration).toBe(6);
    expect(blocks[0].estimated).toBe(true);
  });
});

describe("form validation", () => {
  it("requires strong passwords", () => {
    expect(registerSchema.safeParse({ display_name: "A", email: "a@b.co", password: "short" }).success).toBe(false);
    expect(registerSchema.safeParse({ display_name: "A", email: "a@b.co", password: "alllowercaseletters" }).success).toBe(false);
    expect(registerSchema.safeParse({ display_name: "A", email: "a@b.co", password: "Good-Password-1" }).success).toBe(true);
  });
  it("requires a meaningful topic", () => {
    const base = {
      language: "en", duration_seconds: 60, aspect_ratio: "9:16", platform: "tiktok", visual_style: "anime", story_tone: "documentary",
      voice_id: "am_michael", voice_speed: 1, caption_animation: "karaoke", story_dna_id: null, music_mood: "auto", sfx_enabled: true,
      fact_check_enabled: true,
    };
    expect(createSchema.safeParse({ ...base, topic: "x" }).success).toBe(false);
    expect(createSchema.safeParse({ ...base, topic: "The Roanoke colony" }).success).toBe(true);
  });
});
