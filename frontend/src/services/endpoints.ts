import type {
  CaptionStyle,
  Dashboard,
  Episode,
  Export,
  Idea,
  Job,
  JobLog,
  MediaAsset,
  MusicSettings,
  MusicTrack,
  Options,
  Page,
  Project,
  ProjectSettings,
  ProviderHealth,
  Scene,
  SceneAsset,
  Script,
  Series,
  StoryDna,
  Storyboard,
  Template,
  User,
  Voice,
  VoiceProfile,
} from "@/types/api";
import { api, blobUrl } from "./http";

export type ProjectCreateInput = {
  topic: string;
  title?: string;
  language: string;
  duration_seconds: number;
  aspect_ratio: string;
  platform: string;
  visual_style?: string;
  story_tone?: string;
  voice_id?: string;
  voice_speed?: number;
  caption_style?: CaptionStyle;
  music?: MusicSettings;
  sfx_enabled?: boolean;
  fact_check_enabled?: boolean;
  story_dna_id?: string | null;
  auto_produce?: boolean;
  hook_style?: string | null;
};

export type ProjectUpdate = Partial<Omit<ProjectSettings, "brand">> & {
  title?: string;
  story_dna_id?: string | null;
  brand_handle?: string;
};

export type SceneUpdate = Partial<
  Pick<
    Scene,
    | "title"
    | "narration"
    | "duration_override"
    | "visual_type"
    | "visual_description"
    | "image_prompt"
    | "characters"
    | "camera_movement"
    | "effects"
    | "transition"
    | "emphasis_words"
    | "caption_override"
    | "sound_effects"
    | "music_cue"
    | "mood"
    | "color_palette"
    | "visual_data"
  >
>;

export type StoryDnaInput = Omit<StoryDna, "id" | "created_at" | "updated_at">;

export const authApi = {
  register: (body: { email: string; password: string; display_name: string }) =>
    api<{ access_token: string; expires_in: number }>("/auth/register", { method: "POST", body, auth: false }),
  login: (body: { email: string; password: string }) =>
    api<{ access_token: string; expires_in: number }>("/auth/login", { method: "POST", body, auth: false }),
  refresh: () => api<{ access_token: string }>("/auth/refresh", { method: "POST", auth: false }),
  logout: () => api<void>("/auth/logout", { method: "POST", auth: false }),
  me: () => api<User>("/auth/me"),
};

export const projectsApi = {
  list: (params: { q?: string; status?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]));
    return api<Page<Project>>(`/projects?${qs}`);
  },
  get: (id: string) => api<Project>(`/projects/${id}`),
  create: (body: ProjectCreateInput) => api<Project>("/projects", { method: "POST", body }),
  update: (id: string, body: ProjectUpdate) => api<Project>(`/projects/${id}`, { method: "PATCH", body }),
  remove: (id: string) => api<void>(`/projects/${id}`, { method: "DELETE" }),
  script: (id: string) => api<Script>(`/projects/${id}/script`),
  storyboard: (id: string) => api<Storyboard>(`/projects/${id}/storyboard`),
  generateStory: (id: string) => api<Job>(`/projects/${id}/generate-story`, { method: "POST" }),
  selectHook: (id: string, hook_index: number) => api<Job>(`/projects/${id}/hooks/select`, { method: "POST", body: { hook_index } }),
  produce: (id: string, quality: "draft" | "final") => api<Job>(`/projects/${id}/produce`, { method: "POST", body: { quality } }),
  exports: (id: string) => api<Export[]>(`/projects/${id}/exports`),
  jobs: (id: string) => api<Job[]>(`/projects/${id}/jobs`),
};

export const scenesApi = {
  update: (id: string, body: SceneUpdate) => api<Scene>(`/scenes/${id}`, { method: "PATCH", body }),
  add: (projectId: string, body: SceneUpdate & { narration: string; position?: number }) =>
    api<Scene>(`/projects/${projectId}/scenes`, { method: "POST", body }),
  remove: (id: string) => api<void>(`/scenes/${id}`, { method: "DELETE" }),
  reorder: (projectId: string, scene_ids: string[]) =>
    api<Scene[]>(`/projects/${projectId}/scenes/reorder`, { method: "POST", body: { scene_ids } }),
  regenerate: (id: string, parts: ("visual_plan" | "narration" | "image")[], instruction = "") =>
    api<Job>(`/scenes/${id}/regenerate`, { method: "POST", body: { parts, instruction } }),
  uploadImage: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api<Scene>(`/scenes/${id}/image`, { method: "POST", form });
  },
  history: (id: string, role: "image" | "narration" = "image") => api<SceneAsset[]>(`/scenes/${id}/assets?role=${role}`),
  restore: (id: string, linkId: string) => api<Scene>(`/scenes/${id}/assets/${linkId}/restore`, { method: "POST" }),
};

export const jobsApi = {
  list: (active = false) => api<Job[]>(`/jobs?active=${active}`),
  get: (id: string) => api<Job>(`/jobs/${id}`),
  logs: (id: string) => api<JobLog[]>(`/jobs/${id}/logs`),
  cancel: (id: string) => api<Job>(`/jobs/${id}/cancel`, { method: "POST" }),
  exports: () => api<Export[]>("/exports"),
  removeExport: (id: string) => api<void>(`/exports/${id}`, { method: "DELETE" }),
};

export const mediaApi = {
  list: (params: { kind?: string; limit?: number; offset?: number } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]));
    return api<Page<MediaAsset>>(`/media?${qs}`);
  },
  upload: (file: File, purpose: "image" | "music", name = "") => {
    const form = new FormData();
    form.append("file", file);
    form.append("purpose", purpose);
    form.append("name", name);
    return api<MediaAsset>("/media/upload", { method: "POST", form });
  },
  remove: (id: string) => api<void>(`/media/${id}`, { method: "DELETE" }),
};

export const creativeApi = {
  dna: () => api<StoryDna[]>("/story-dna"),
  createDna: (body: StoryDnaInput) => api<StoryDna>("/story-dna", { method: "POST", body }),
  updateDna: (id: string, body: StoryDnaInput) => api<StoryDna>(`/story-dna/${id}`, { method: "PUT", body }),
  removeDna: (id: string) => api<void>(`/story-dna/${id}`, { method: "DELETE" }),
  voices: () => api<Voice[]>("/voices"),
  previewVoice: (body: { voice_id: string; text: string; speed: number; language: string }) =>
    blobUrl("/voices/preview", { method: "POST", body }),
  voiceProfiles: () => api<VoiceProfile[]>("/voice-profiles"),
  createVoiceProfile: (body: { name: string; voice_id: string; speed: number }) =>
    api<VoiceProfile>("/voice-profiles", { method: "POST", body }),
  removeVoiceProfile: (id: string) => api<void>(`/voice-profiles/${id}`, { method: "DELETE" }),
  templates: () => api<Template[]>("/templates"),
  createTemplate: (body: { name: string; description?: string; category?: string; is_public?: boolean; project_id?: string }) =>
    api<Template>("/templates", { method: "POST", body }),
  removeTemplate: (id: string) => api<void>(`/templates/${id}`, { method: "DELETE" }),
  music: () => api<MusicTrack[]>("/music"),
  musicPreview: (mood: string) => blobUrl(`/music/moods/${mood}/preview`),
  sfxPreview: (kind: string) => blobUrl(`/sfx/${kind}/preview`),
};

export const planningApi = {
  series: () => api<Series[]>("/series"),
  getSeries: (id: string) => api<Series>(`/series/${id}`),
  createSeries: (body: Record<string, unknown>) => api<Series>("/series", { method: "POST", body }),
  removeSeries: (id: string) => api<void>(`/series/${id}`, { method: "DELETE" }),
  replan: (id: string) => api<Job>(`/series/${id}/replan`, { method: "POST" }),
  produceSeries: (id: string, body: { episode_ids?: string[]; quality: "draft" | "final" }) =>
    api<Job>(`/series/${id}/produce`, { method: "POST", body }),
  updateEpisode: (seriesId: string, id: string, body: Partial<Pick<Episode, "title" | "premise" | "hook">>) =>
    api<Episode>(`/series/${seriesId}/episodes/${id}`, { method: "PATCH", body }),
  ideas: (params: { start?: string; end?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
    return api<Idea[]>(`/ideas?${qs}`);
  },
  createIdea: (body: Partial<Idea>) => api<Idea>("/ideas", { method: "POST", body }),
  updateIdea: (id: string, body: Partial<Idea> & { clear_schedule?: boolean }) => api<Idea>(`/ideas/${id}`, { method: "PATCH", body }),
  removeIdea: (id: string) => api<void>(`/ideas/${id}`, { method: "DELETE" }),
  ideaToProject: (id: string) => api<Project>(`/ideas/${id}/create-project`, { method: "POST" }),
  suggest: (theme: string, count = 6) => api<Pick<Idea, "title" | "notes" | "tags">[]>("/ideas/suggest", { method: "POST", body: { theme, count } }),
};

export const accountApi = {
  dashboard: () => api<Dashboard>("/dashboard"),
  updateProfile: (body: { display_name?: string; default_story_dna_id?: string | null }) =>
    api<User>("/account/profile", { method: "PATCH", body }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api<void>("/account/password", { method: "POST", body }),
  deleteAccount: (email: string) => api<void>(`/account?confirm=${encodeURIComponent(email)}`, { method: "DELETE" }),
  providers: () => api<ProviderHealth[]>("/system/providers"),
  options: () => api<Options>("/system/options", { auth: false }),
};
