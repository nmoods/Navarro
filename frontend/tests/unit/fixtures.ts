import type { Scene } from "@/types/api";

export function scene(overrides: Partial<Scene> = {}): Scene {
  return {
    id: crypto.randomUUID(), position: 0, title: "Scene", narration: "one two three four five", duration_override: null,
    visual_type: "cinematic_image", visual_description: "", image_prompt: "", characters: [], camera_movement: "ken_burns",
    effects: [], transition: "crossfade", emphasis_words: [], caption_override: {}, sound_effects: [], music_cue: "steady",
    mood: "", color_palette: [], visual_data: {}, updated_at: new Date().toISOString(), image: null, narration_audio: null,
    narration_seconds: null, caption_timing: null, ...overrides,
  };
}
