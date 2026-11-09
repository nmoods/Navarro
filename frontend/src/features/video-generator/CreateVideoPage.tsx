import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
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

const STEPS = ["Story", "Look", "Voice and sound", "Review"] as const;
const PLATFORM_RATIO: Record<string, CreateForm["aspect_ratio"]> = {
  tiktok: "9:16", instagram_reels: "9:16", youtube_shorts: "9:16", youtube: "16:9", generic: "9:16",
};

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
  const [step, setStep] = useState(0);
  const options = useOptions();
  const voices = useQuery({ queryKey: keys.voices, queryFn: creativeApi.voices });
  const dna = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const templates = useQuery({ queryKey: keys.templates, queryFn: creativeApi.templates });

  const form = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      topic: params.get("topic") ?? "", language: "en", duration_seconds: 60, aspect_ratio: "9:16", platform: "tiktok",
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
        topic: v.topic, language: v.language, duration_seconds: v.duration_seconds, aspect_ratio: v.aspect_ratio,
        platform: v.platform, visual_style: v.visual_style, story_tone: v.story_tone, voice_id: v.voice_id,
        voice_speed: v.voice_speed, caption_style: { animation: v.caption_animation as never },
        music: v.music_mood === "auto" ? { enabled: true } : v.music_mood === "none" ? { enabled: false } : { enabled: true, mood: v.music_mood },
        sfx_enabled: v.sfx_enabled, fact_check_enabled: v.fact_check_enabled, story_dna_id: v.story_dna_id, auto_produce: autoProduce,
      }),
    onSuccess: (project) => navigate(`/projects/${project.id}`),
  });

  const next = async () => {
    if (step === 0 && !(await form.trigger("topic"))) return;
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };
  const o = options.data;
  const opts = (values: string[] | undefined) => (values ?? []).map((x) => ({ value: x, label: label(x) }));

  return (
    <Page>
      <PageHeader title="New video" description="Describe a subject. You review the storyboard before anything is rendered." />
      <ProviderBanner />
      <ol className="mb-8 flex flex-wrap gap-2" aria-label="Steps">
        {STEPS.map((name, i) => (
          <li key={name}>
            <button
              type="button"
              onClick={() => i <= step && setStep(i)}
              className={cn("rounded-full border px-3 py-1 text-sm", i === step ? "border-uv text-text" : i < step ? "border-line text-subtle" : "border-line text-faint")}
              aria-current={i === step ? "step" : undefined}
            >
              {i + 1}. {name}
            </button>
          </li>
        ))}
      </ol>

      <form onSubmit={(e) => e.preventDefault()} className="grid max-w-3xl gap-8">
        {step === 0 && (
          <>
            <Field label="What is the video about?" htmlFor="topic" error={form.formState.errors.topic?.message} hint="Be specific. “Why the Mary Celeste was found abandoned” beats “ships”.">
              <Textarea id="topic" rows={3} placeholder="The mysterious disappearance of the Roanoke colony" aria-invalid={!!form.formState.errors.topic} {...form.register("topic")} />
            </Field>
            <Field label="Length">
              <div className="flex flex-wrap gap-2">
                {(o?.durations ?? [30, 45, 60, 90]).map((d) => (
                  <Choice key={d} value={d} current={v.duration_seconds} onSelect={() => form.setValue("duration_seconds", d)}>{d} seconds</Choice>
                ))}
              </div>
            </Field>
            <div className="grid gap-6 sm:grid-cols-2">
              <Field label="Story tone" htmlFor="tone">
                <SelectField id="tone" value={v.story_tone} onChange={(x) => form.setValue("story_tone", x)} items={opts(o?.story_tones)} />
              </Field>
              <Field label="Language" htmlFor="language" hint="Narration language. Voices are matched to it.">
                <SelectField id="language" value={v.language} onChange={(x) => form.setValue("language", x)} items={(o?.languages ?? []).map((l) => ({ value: l.code, label: l.name }))} />
              </Field>
            </div>
            <label className="flex items-start gap-3 text-sm">
              <Controller control={form.control} name="fact_check_enabled" render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Fact check" />} />
              <span><span className="text-text">Check facts against sources</span><br /><span className="text-faint">Uses Wikipedia to verify claims in educational and historical scripts.</span></span>
            </label>
          </>
        )}

        {step === 1 && (
          <>
            {dna.data && dna.data.length > 0 && (
              <Field label="Story DNA" hint="Applies a saved channel identity: style, voice, captions and music.">
                <div className="flex flex-wrap gap-2">
                  <Choice value="none" current={v.story_dna_id ?? "none"} onSelect={() => applyDna(null)}>None</Choice>
                  {dna.data.map((d) => <Choice key={d.id} value={d.id} current={v.story_dna_id ?? "none"} onSelect={() => applyDna(d.id)}>{d.name}</Choice>)}
                </div>
              </Field>
            )}
            <Field label="Where will it be posted?">
              <div className="flex flex-wrap gap-2">
                {(o?.platforms ?? []).map((p) => (
                  <Choice key={p} value={p} current={v.platform} onSelect={() => { form.setValue("platform", p); form.setValue("aspect_ratio", PLATFORM_RATIO[p] ?? "9:16"); }}>{label(p)}</Choice>
                ))}
              </div>
            </Field>
            <Field label="Format">
              <div className="flex flex-wrap gap-2">
                {(["9:16", "16:9", "1:1"] as const).map((r) => <Choice key={r} value={r} current={v.aspect_ratio} onSelect={() => form.setValue("aspect_ratio", r)}>{label(r)}</Choice>)}
              </div>
            </Field>
            <div className="grid gap-6 sm:grid-cols-2">
              <Field label="Visual style" htmlFor="style">
                <SelectField id="style" value={v.visual_style} onChange={(x) => form.setValue("visual_style", x)} items={opts(o?.visual_styles)} />
              </Field>
              <Field label="Caption animation" htmlFor="captions">
                <SelectField id="captions" value={v.caption_animation} onChange={(x) => form.setValue("caption_animation", x)} items={opts(o?.caption_animations)} />
              </Field>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <Field label="Narrator voice" htmlFor="voice" hint={voices.error ? "Voices are unavailable until Kokoro is installed." : undefined}>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <SelectField
                    id="voice"
                    value={v.voice_id}
                    onChange={(x) => form.setValue("voice_id", x)}
                    items={(voices.data ?? [{ id: v.voice_id, name: v.voice_id, accent: "", gender: "", language: "" }])
                      .filter((x) => !x.language || x.language === v.language)
                      .map((x) => ({ value: x.id, label: x.accent ? `${x.name} · ${x.accent} ${x.gender}` : x.name }))}
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
          </>
        )}

        {step === 3 && (
          <div className="grid gap-6">
            <dl className="grid gap-x-8 gap-y-3 rounded-xl border border-line p-5 text-sm sm:grid-cols-2">
              {[
                ["Subject", v.topic],
                ["Length", `${v.duration_seconds} seconds`],
                ["Format", `${label(v.aspect_ratio)} for ${label(v.platform)}`],
                ["Style", label(v.visual_style)],
                ["Tone", label(v.story_tone)],
                ["Voice", `${v.voice_id} at ${v.voice_speed.toFixed(2)}×`],
                ["Captions", label(v.caption_animation)],
                ["Music", v.music_mood === "auto" ? "Match the story" : label(v.music_mood)],
              ].map(([k, val]) => (
                <div key={k} className="min-w-0">
                  <dt className="text-faint">{k}</dt>
                  <dd className="mt-0.5 break-words text-text">{val}</dd>
                </div>
              ))}
            </dl>
            {create.error ? <ErrorNotice error={create.error} /> : null}
            <div className="grid gap-3 sm:grid-cols-2">
              <button type="button" disabled={create.isPending} onClick={() => create.mutate(false)} className="rounded-xl border border-uv bg-uv/10 p-5 text-left hover:bg-uv/15 disabled:opacity-50">
                <p className="font-semibold">Write the storyboard</p>
                <p className="mt-1 text-sm text-subtle">Pick a hook, review the script and scenes, then render. Recommended.</p>
              </button>
              <button type="button" disabled={create.isPending} onClick={() => create.mutate(true)} className="rounded-xl border border-line p-5 text-left hover:border-line-strong disabled:opacity-50">
                <p className="font-semibold">Produce the whole video</p>
                <p className="mt-1 text-sm text-subtle">Write, illustrate, voice and render in one go. You can still edit afterwards.</p>
              </button>
            </div>
          </div>
        )}

        {step < 3 && (
          <div className="flex gap-2">
            {step > 0 && <Button type="button" variant="outline" onClick={() => setStep(step - 1)}>Back</Button>}
            <Button type="button" onClick={next}>Continue</Button>
          </div>
        )}
      </form>
    </Page>
  );
}
