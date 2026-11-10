import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronDown, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Page } from "@/app/AppShell";
import { AudioButton, ErrorNotice, Field, PageHeader, ProviderBanner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { keys, useOptions } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { creativeApi, projectsApi } from "@/services/endpoints";

export const createSchema = z.object({
  topic: z.string().trim().min(3, "Describe the subject in a few words").max(500),
  language: z.string().length(2),
  duration_seconds: z.number().int(),
  aspect_ratio: z.enum(["9:16", "16:9", "1:1"]),
  platform: z.string(),
  visual_style: z.string(),
  story_tone: z.string(),
  voice_id: z.string().min(2),
  voice_speed: z.number().min(0.5).max(2),
  caption_animation: z.string(),
  story_dna_id: z.string().nullable(),
  music_mood: z.string(),
  sfx_enabled: z.boolean(),
  fact_check_enabled: z.boolean(),
});
export type CreateForm = z.infer<typeof createSchema>;

/** Real, documented subjects: one click fills the idea box. */
export const EXAMPLE_TOPICS = [
  "The lost colony of Roanoke",
  "Why the Mary Celeste was found empty",
  "The Tunguska explosion of 1908",
  "How Venice was built on water",
  "The Great Emu War of 1932",
] as const;

const FORMATS: { value: CreateForm["aspect_ratio"]; name: string; where: string; platform: string }[] = [
  { value: "9:16", name: "Vertical", where: "TikTok, Reels, Shorts", platform: "generic" },
  { value: "16:9", name: "Landscape", where: "YouTube", platform: "youtube" },
  { value: "1:1", name: "Square", where: "Feeds", platform: "generic" },
];

function Choice({ value, current, onSelect, children }: { value: string | number; current: string | number; onSelect: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={value === current}
      className={cn(
        "rounded-lg border px-3 py-2 text-left text-sm",
        value === current ? "border-uv bg-uv/10 text-text" : "border-line text-subtle hover:border-line-strong hover:text-text",
      )}
    >
      {children}
    </button>
  );
}

function SelectField({ value, onChange, items, id }: { value: string; onChange: (v: string) => void; items: { value: string; label: string }[]; id: string }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
    </Select>
  );
}

export default function CreateVideoPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [moreOpen, setMoreOpen] = useState(false);
  const options = useOptions();
  const voices = useQuery({ queryKey: keys.voices, queryFn: creativeApi.voices, enabled: moreOpen });
  const dna = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const templates = useQuery({ queryKey: keys.templates, queryFn: creativeApi.templates, enabled: params.has("template") });

  const form = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      topic: params.get("topic") ?? "", language: "en", duration_seconds: 45, aspect_ratio: "9:16", platform: "generic",
      visual_style: "cinematic_documentary", story_tone: "documentary", voice_id: "am_michael", voice_speed: 1,
      caption_animation: "karaoke", story_dna_id: null, music_mood: "auto", sfx_enabled: true, fact_check_enabled: true,
    },
  });
  const v = form.watch();

  useEffect(() => {
    const t = templates.data?.find((x) => x.id === params.get("template"));
    if (!t) return;
    const c = t.config as Record<string, unknown>;
    if (typeof c.visual_style === "string") form.setValue("visual_style", c.visual_style);
    if (typeof c.story_tone === "string") form.setValue("story_tone", c.story_tone);
    if (typeof c.voice_id === "string") form.setValue("voice_id", c.voice_id);
    const caption = c.caption_style as { animation?: string } | undefined;
    if (caption?.animation) form.setValue("caption_animation", caption.animation);
    const music = c.music as { mood?: string } | undefined;
    if (music?.mood) form.setValue("music_mood", music.mood);
    toast(`Using the “${t.name}” template`);
  }, [templates.data, params, form]);

  const applyDna = (id: string | null) => {
    form.setValue("story_dna_id", id);
    const profile = dna.data?.find((d) => d.id === id);
    if (!profile) return;
    form.setValue("visual_style", profile.visual_style);
    form.setValue("story_tone", profile.tone);
    form.setValue("voice_id", profile.voice_id);
    form.setValue("voice_speed", profile.voice_speed);
    if (profile.caption_style.animation) form.setValue("caption_animation", profile.caption_style.animation);
    if (profile.music_preferences.mood) form.setValue("music_mood", profile.music_preferences.mood);
  };

  const create = useMutation({
    mutationFn: (autoProduce: boolean) =>
      projectsApi.create({
        topic: v.topic.trim(), language: v.language, duration_seconds: v.duration_seconds, aspect_ratio: v.aspect_ratio,
        platform: v.platform, visual_style: v.visual_style, story_tone: v.story_tone, voice_id: v.voice_id,
        voice_speed: v.voice_speed, caption_style: { animation: v.caption_animation as never },
        music: v.music_mood === "auto" ? { enabled: true } : v.music_mood === "none" ? { enabled: false } : { enabled: true, mood: v.music_mood },
        sfx_enabled: v.sfx_enabled, fact_check_enabled: v.fact_check_enabled, story_dna_id: v.story_dna_id, auto_produce: autoProduce,
      }),
    onSuccess: (project) => navigate(`/projects/${project.id}`),
  });

  const start = async (autoProduce: boolean) => {
    if (!(await form.trigger("topic"))) return;
    create.mutate(autoProduce);
  };
  const o = options.data;
  const opts = (values: string[] | undefined) => (values ?? []).map((x) => ({ value: x, label: label(x) }));

  return (
    <Page>
      <PageHeader title="New video" description="Describe your idea. NaRRAVO writes the narration, draws every scene, records the voice and edits the video. You can change anything afterwards." />
      <ProviderBanner />

      <form onSubmit={(e) => { e.preventDefault(); void start(true); }} className="grid max-w-3xl gap-8">
        <Field label="What is the video about?" htmlFor="topic" error={form.formState.errors.topic?.message}>
          <Textarea
            id="topic"
            rows={3}
            autoFocus
            placeholder="The mysterious disappearance of the Roanoke colony"
            aria-invalid={!!form.formState.errors.topic}
            className="text-base"
            {...form.register("topic")}
          />
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-faint">Try:</span>
            {EXAMPLE_TOPICS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => form.setValue("topic", t, { shouldValidate: true })}
                className="rounded-full border border-line px-3 py-1 text-subtle hover:border-line-strong hover:text-text"
              >
                {t}
              </button>
            ))}
          </div>
        </Field>

        <div className="grid gap-8 sm:grid-cols-2">
          <Field label="Length">
            <div className="flex flex-wrap gap-2">
              {(o?.durations ?? [30, 45, 60, 90]).map((d) => (
                <Choice key={d} value={d} current={v.duration_seconds} onSelect={() => form.setValue("duration_seconds", d)}>{d} s</Choice>
              ))}
            </div>
          </Field>
          <Field label="Format">
            <div className="flex flex-wrap gap-2">
              {FORMATS.map((f) => (
                <Choice key={f.value} value={f.value} current={v.aspect_ratio} onSelect={() => { form.setValue("aspect_ratio", f.value); form.setValue("platform", f.platform); }}>
                  <span className="block text-text">{f.name}</span>
                  <span className="block text-xs text-faint">{f.where}</span>
                </Choice>
              ))}
            </div>
          </Field>
        </div>

        <Field label="Look">
          <div className="flex flex-wrap gap-2">
            {(o?.visual_styles ?? [v.visual_style]).map((s) => (
              <Choice key={s} value={s} current={v.visual_style} onSelect={() => form.setValue("visual_style", s)}>{label(s)}</Choice>
            ))}
          </div>
        </Field>

        {create.error ? <ErrorNotice error={create.error} /> : null}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Button type="submit" size="lg" disabled={create.isPending}>
            <Sparkles className="size-4" /> {create.isPending ? "Starting…" : "Make my video"}
          </Button>
          <button type="button" disabled={create.isPending} onClick={() => void start(false)} className="text-sm text-subtle underline-offset-4 hover:text-text hover:underline disabled:opacity-50">
            Review the storyboard before rendering
          </button>
        </div>
        <p className="-mt-4 text-sm text-faint">You can leave this page while it works. The finished video appears in the editor.</p>

        <section className="rounded-xl border border-line">
          <button
            type="button"
            onClick={() => setMoreOpen((x) => !x)}
            aria-expanded={moreOpen}
            aria-controls="more-options"
            className="flex w-full items-center justify-between px-5 py-4 text-left text-sm"
          >
            <span>
              <span className="text-text">More options</span>
              <span className="ml-2 text-faint">Voice, tone, captions, music, language, fact checking</span>
            </span>
            <ChevronDown className={cn("size-4 text-subtle transition-transform", moreOpen && "rotate-180")} aria-hidden />
          </button>
          {moreOpen && (
            <div id="more-options" className="grid gap-6 border-t border-line p-5">
              {dna.data && dna.data.length > 0 && (
                <Field label="Story DNA" hint="Applies a saved channel identity: style, voice, captions and music.">
                  <div className="flex flex-wrap gap-2">
                    <Choice value="none" current={v.story_dna_id ?? "none"} onSelect={() => applyDna(null)}>None</Choice>
                    {dna.data.map((d) => <Choice key={d.id} value={d.id} current={v.story_dna_id ?? "none"} onSelect={() => applyDna(d.id)}>{d.name}</Choice>)}
                  </div>
                </Field>
              )}
              <Field label="Narrator voice" htmlFor="voice" hint={voices.error ? "Voices are unavailable until Kokoro is installed." : undefined}>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <SelectField
                      id="voice"
                      value={v.voice_id}
                      onChange={(x) => form.setValue("voice_id", x)}
                      items={(voices.data ?? [{ id: v.voice_id, name: v.voice_id, accent: "", gender: "", language: "" }])
                        .filter((x) => !x.language || x.language === v.language)
                        .map((x) => ({ value: x.id, label: x.accent ? `${x.name}, ${x.accent} ${x.gender}` : x.name }))}
                    />
                  </div>
                  <AudioButton
                    label="voice sample"
                    load={() => creativeApi.previewVoice({ voice_id: v.voice_id, speed: v.voice_speed, language: v.language, text: v.topic || "Every story starts with a single question." })}
                  />
                </div>
              </Field>
              <Field label={`Speaking speed: ${v.voice_speed.toFixed(2)}×`}>
                <Slider min={0.7} max={1.4} step={0.05} value={[v.voice_speed]} onValueChange={([x]) => form.setValue("voice_speed", x)} aria-label="Speaking speed" />
              </Field>
              <div className="grid gap-6 sm:grid-cols-2">
                <Field label="Story tone" htmlFor="tone">
                  <SelectField id="tone" value={v.story_tone} onChange={(x) => form.setValue("story_tone", x)} items={opts(o?.story_tones)} />
                </Field>
                <Field label="Language" htmlFor="language" hint="Narration language. Voices are matched to it.">
                  <SelectField id="language" value={v.language} onChange={(x) => form.setValue("language", x)} items={(o?.languages ?? []).map((l) => ({ value: l.code, label: l.name }))} />
                </Field>
                <Field label="Caption animation" htmlFor="captions">
                  <SelectField id="captions" value={v.caption_animation} onChange={(x) => form.setValue("caption_animation", x)} items={opts(o?.caption_animations)} />
                </Field>
                <Field label="Platform" htmlFor="platform" hint="Used for pacing and the safe area for captions.">
                  <SelectField id="platform" value={v.platform} onChange={(x) => form.setValue("platform", x)} items={opts(o?.platforms)} />
                </Field>
              </div>
              <Field label="Music" hint="Scores are composed locally for each video and are royalty-free.">
                <div className="flex flex-wrap gap-2">
                  <Choice value="auto" current={v.music_mood} onSelect={() => form.setValue("music_mood", "auto")}>Match the story</Choice>
                  {(o?.music_moods ?? []).map((m) => <Choice key={m} value={m} current={v.music_mood} onSelect={() => form.setValue("music_mood", m)}>{label(m)}</Choice>)}
                </div>
              </Field>
              <label className="flex items-center gap-3 text-sm">
                <Controller control={form.control} name="sfx_enabled" render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Sound effects" />} />
                Add sound effects for transitions and atmosphere
              </label>
              <label className="flex items-start gap-3 text-sm">
                <Controller control={form.control} name="fact_check_enabled" render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Fact check" />} />
                <span><span className="text-text">Check facts against sources</span><br /><span className="text-faint">Uses Wikipedia to verify claims in educational and historical scripts.</span></span>
              </label>
            </div>
          )}
        </section>
      </form>
    </Page>
  );
}
