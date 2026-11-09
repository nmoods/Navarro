// Mirrors backend/app/schemas/core.py. Keep in sync when the API changes.

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export type User = {
  id: string;
  email: string;
  display_name: string;
  auth_provider: string;
  default_story_dna_id: string | null;
  created_at: string;
};

export type CaptionStyle = Partial<{
  animation: "word_pop" | "karaoke" | "bounce" | "typewriter" | "sentence";
  font: string;
  font_weight: number;
  size: number;
  color: string;
  highlight_color: string;
  emphasis_color: string;
  stroke_color: string;
  stroke_width: number;
  background: "none" | "box" | "shadow";
  background_color: string;
  position: "top" | "middle" | "bottom";
  vertical_offset: number;
  uppercase: boolean;
  max_words: number;
  enabled: boolean;
  offset_ms: number;
}>;

export type MusicSettings = { enabled?: boolean; mood?: string | null; volume_db?: number; track_id?: string | null };

export type ProjectSettings = {
  language: string;
  duration_seconds: number;
  aspect_ratio: "9:16" | "16:9" | "1:1";
  fps: number;
  platform: string;
  visual_style: string;
  story_tone: string;
  voice_id: string;
  voice_speed: number;
  caption_style: CaptionStyle;
  music: MusicSettings;
  sfx_enabled: boolean;
  fact_check_enabled: boolean;
  brand: { handle?: string };
};

export type ProjectStatus = "draft" | "generating_story" | "storyboard_ready" | "producing" | "ready" | "failed";

export type Project = {
  id: string;
  title: string;
  topic: string;
  status: ProjectStatus;
  series_id: string | null;
  story_dna_id: string | null;
  thumbnail_url: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  settings: ProjectSettings | null;
};

export type SceneAsset = {
  id: string;
  role: string;
  media_asset_id: string;
  provider: string;
  source: "generated" | "procedural" | "uploaded" | "fixture";
  url: string;
  is_current: boolean;
  locked: boolean;
  created_at: string;
  details: Record<string, unknown>;
};

export type VisualData = {
  places?: { name: string; latitude?: number | null; longitude?: number | null }[];
  draw_route?: boolean;
  events?: { date: string; label: string }[];
  stats?: { label: string; value: number; unit?: string }[];
  left?: { label: string; points: string[] } | null;
  right?: { label: string; points: string[] } | null;
  headline?: string;
  dateline?: string;
  kinetic_lines?: string[];
};

export type Scene = {
  id: string;
  position: number;
  title: string;
  narration: string;
  duration_override: number | null;
  visual_type: string;
  visual_description: string;
  image_prompt: string;
  characters: string[];
  camera_movement: string;
  effects: string[];
  transition: string;
  emphasis_words: string[];
  caption_override: CaptionStyle;
  sound_effects: string[];
  music_cue: string;
  mood: string;
  color_palette: string[];
  visual_data: VisualData;
  updated_at: string;
  image: SceneAsset | null;
  narration_audio: SceneAsset | null;
  narration_seconds: number | null;
  caption_timing: string | null;
};

export type StoryboardAnalysis = {
  total_words: number;
  estimated_seconds: number;
  words_per_scene: number[];
  estimated_scene_seconds: number[];
  repeated_words: string[];
  repeated_phrases: string[];
  hook_words: number;
  warnings: string[];
};

export type Storyboard = { id: string; version: number; analysis: StoryboardAnalysis; scenes: Scene[] };

export type Claim = {
  text: string;
  confidence: "well_established" | "debated" | "uncertain";
  note: string;
  verdict: "unverified" | "supported" | "contradicted" | "not_found";
  sources: string[];
};

export type Hook = { style: string; text: string; rationale?: string };

export type Script = {
  id: string;
  version: number;
  title: string;
  brief: {
    subject_summary?: string;
    target_audience?: string;
    angle?: string;
    emotional_arc?: string;
    open_questions?: string[];
    sources?: { title: string; url: string }[];
  };
  hooks: Hook[];
  selected_hook_index: number | null;
  content: { hook?: string; beginning?: string; middle?: string; conclusion?: string; title?: string };
  full_text: string;
  claims: Claim[];
  model: string | null;
  created_at: string;
};

export type JobStatus =
  | "pending"
  | "script_generation"
  | "storyboard_generation"
  | "image_generation"
  | "voice_generation"
  | "animation"
  | "rendering"
  | "finalizing"
  | "completed"
  | "failed"
  | "cancelled";

export type Job = {
  id: string;
  job_type: "story" | "production" | "preview" | "scene_regeneration" | "series_plan" | "series_production";
  status: JobStatus;
  progress: number;
  stage_message: string;
  project_id: string | null;
  series_id: string | null;
  scene_id: string | null;
  parent_job_id: string | null;
  error: string | null;
  attempts: number;
  result: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type JobLog = { level: string; stage: string; message: string; created_at: string };

export type Export = {
  id: string;
  project_id: string;
  project_title: string | null;
  quality: "draft" | "final";
  aspect_ratio: string;
  width: number;
  height: number;
  fps: number;
  duration_seconds: number;
  video_url: string;
  download_url: string;
  thumbnail_url: string | null;
  created_at: string;
  details: { scenes?: number; image_sources?: string[] };
};

export type MediaAsset = {
  id: string;
  kind: string;
  source: string;
  mime_type: string;
  size_bytes: number;
  original_name: string | null;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  url: string;
  created_at: string;
};

export type StoryDna = {
  id: string;
  name: string;
  description: string;
  visual_style: string;
  style_prompt: string;
  color_palette: string[];
  typography: Record<string, string>;
  voice_id: string;
  voice_speed: number;
  caption_style: CaptionStyle;
  animation_preferences: { camera?: string[]; effects_intensity?: string };
  music_preferences: MusicSettings;
  brand: { handle?: string; name?: string };
  visual_references: string[];
  tone: string;
  created_at: string;
  updated_at: string;
};

export type Voice = { id: string; name: string; language: string; gender: string; accent: string };
export type VoiceProfile = { id: string; name: string; provider: string; voice_id: string; speed: number; settings: Record<string, unknown>; created_at: string };

export type Template = {
  id: string;
  name: string;
  description: string;
  category: string;
  is_public: boolean;
  is_builtin: boolean;
  version: string;
  config: Record<string, unknown>;
  owned: boolean;
  created_at: string;
};

export type MusicTrack = { id: string | null; name: string; mood: string; source: string; license_note: string; preview_url: string | null };

export type Episode = {
  id: string;
  position: number;
  title: string;
  premise: string;
  hook: string;
  continuity_note: string;
  project_id: string | null;
  status: "planned" | "producing" | "completed" | "failed";
  error: string | null;
};

export type Series = {
  id: string;
  title: string;
  theme: string;
  episode_count: number;
  status: "planning" | "planned" | "producing" | "completed" | "partial" | "failed";
  bible: {
    logline?: string;
    visual_style_notes?: string;
    recurring_characters?: { name: string; visual_description: string }[];
    recurring_locations?: string[];
  };
  settings: Record<string, unknown>;
  story_dna_id: string | null;
  created_at: string;
  episodes: Episode[];
};

export type Idea = {
  id: string;
  title: string;
  notes: string;
  tags: string[];
  status: "idea" | "planned" | "in_production" | "published" | "archived";
  scheduled_for: string | null;
  project_id: string | null;
  series_id: string | null;
  created_at: string;
};

export type ProviderHealth = {
  name: string;
  kind: "llm" | "image" | "tts" | "stt" | "research" | "unknown";
  available: boolean;
  detail: string;
  capabilities: Record<string, unknown>;
  is_test_double: boolean;
};

export type Options = {
  visual_styles: string[];
  visual_types: string[];
  camera_moves: string[];
  effects: string[];
  transitions: string[];
  caption_animations: string[];
  caption_positions: string[];
  sound_effects: string[];
  music_moods: string[];
  story_tones: string[];
  platforms: string[];
  aspect_ratios: string[];
  hook_styles: string[];
  fonts: string[];
  durations: number[];
  languages: { code: string; name: string }[];
};

export type Dashboard = {
  recent_projects: Project[];
  recent_exports: Export[];
  activity: Job[];
  stats: { projects: number; exports: number; series: number; story_dna: number; minutes_rendered: number };
  templates: { id: string; name: string; category: string }[];
};
