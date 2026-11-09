const SPECIAL: Record<string, string> = {
  "9:16": "Vertical 9:16",
  "16:9": "Landscape 16:9",
  "1:1": "Square 1:1",
  tiktok: "TikTok",
  instagram_reels: "Instagram Reels",
  youtube_shorts: "YouTube Shorts",
  youtube: "YouTube",
  animation_3d: "3D animation",
  kinetic_typography: "Kinetic typography",
  historical_map: "Animated map",
  sfx: "SFX",
};

/** "slow_zoom_in" -> "Slow zoom in" */
export function label(value: string | null | undefined): string {
  if (!value) return "";
  if (SPECIAL[value]) return SPECIAL[value];
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** 74.3 -> "01:14.3" */
export function timecode(seconds: number, precise = true): string {
  const s = Math.max(0, seconds);
  const m = Math.floor(s / 60);
  const rest = s - m * 60;
  const sec = precise ? rest.toFixed(1).padStart(4, "0") : String(Math.floor(rest)).padStart(2, "0");
  return `${String(m).padStart(2, "0")}:${sec}`;
}

export function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return new Date(iso).toLocaleDateString();
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

export const JOB_STAGES = [
  "script_generation",
  "storyboard_generation",
  "image_generation",
  "voice_generation",
  "animation",
  "rendering",
  "finalizing",
] as const;

export const STAGE_LABEL: Record<string, string> = {
  pending: "Queued",
  script_generation: "Writing",
  storyboard_generation: "Storyboarding",
  image_generation: "Visuals",
  voice_generation: "Voice",
  animation: "Animating",
  rendering: "Rendering",
  finalizing: "Finishing",
  completed: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

export const PROJECT_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  generating_story: "Writing story",
  storyboard_ready: "Storyboard ready",
  producing: "Producing",
  ready: "Video ready",
  failed: "Needs attention",
};

export const isTerminal = (status: string) => ["completed", "failed", "cancelled"].includes(status);
