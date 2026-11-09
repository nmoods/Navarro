import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AudioButton, Field } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { keys, useOptions } from "@/hooks/queries";
import { label } from "@/lib/format";
import { creativeApi, projectsApi, type ProjectUpdate } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Project } from "@/types/api";

function Pick({ id, value, items, onChange }: { id: string; value: string; items: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
    </Select>
  );
}

export function ProjectSettingsPanel({ project }: { project: Project }) {
  const qc = useQueryClient();
  const { data: o } = useOptions();
  const voices = useQuery({ queryKey: keys.voices, queryFn: creativeApi.voices });
  const music = useQuery({ queryKey: keys.music, queryFn: creativeApi.music });
  const dna = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const s = project.settings!;
  const update = useMutation({
    mutationFn: (body: ProjectUpdate) => projectsApi.update(project.id, body),
    onSuccess: (p) => qc.setQueryData(keys.project(project.id), p),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const opts = (xs?: string[]) => (xs ?? []).map((x) => ({ value: x, label: label(x) }));
  const cap = s.caption_style;
  const tracks = music.data ?? [];

  return (
    <div className="grid gap-6 p-4">
      <p className="text-xs text-faint">Changes apply on the next render. Images and voice are only regenerated when their inputs change.</p>
      <Field label="Story DNA" htmlFor="dna">
        <Pick id="dna" value={project.story_dna_id ?? "none"} items={[{ value: "none", label: "None" }, ...(dna.data ?? []).map((d) => ({ value: d.id, label: d.name }))]} onChange={(v) => update.mutate({ story_dna_id: v === "none" ? null : v })} />
      </Field>
      <Field label="Visual style" htmlFor="ps-style" hint="Changing the style regenerates AI images on the next render.">
        <Pick id="ps-style" value={s.visual_style} items={opts(o?.visual_styles)} onChange={(v) => update.mutate({ visual_style: v })} />
      </Field>
      <Field label="Format" htmlFor="ps-ratio">
        <Pick id="ps-ratio" value={s.aspect_ratio} items={opts(o?.aspect_ratios)} onChange={(v) => update.mutate({ aspect_ratio: v as never })} />
      </Field>
      <Field label="Frame rate" htmlFor="ps-fps">
        <Pick id="ps-fps" value={String(s.fps)} items={["24", "25", "30", "60"].map((x) => ({ value: x, label: `${x} fps` }))} onChange={(v) => update.mutate({ fps: Number(v) })} />
      </Field>

      <section className="grid gap-4 border-t border-line pt-5">
        <h3 className="text-sm font-semibold">Voice</h3>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <Field label="Narrator" htmlFor="ps-voice">
              <Pick id="ps-voice" value={s.voice_id} items={(voices.data ?? [{ id: s.voice_id, name: s.voice_id, accent: "", gender: "", language: "" }]).map((v) => ({ value: v.id, label: v.accent ? `${v.name} · ${v.accent} ${v.gender}` : v.name }))} onChange={(v) => update.mutate({ voice_id: v })} />
            </Field>
          </div>
          <AudioButton label="narrator sample" load={() => creativeApi.previewVoice({ voice_id: s.voice_id, speed: s.voice_speed, language: s.language, text: project.title })} />
        </div>
        <Field label={`Speed: ${s.voice_speed.toFixed(2)}×`}>
          <Slider min={0.7} max={1.4} step={0.05} defaultValue={[s.voice_speed]} onValueCommit={([v]) => update.mutate({ voice_speed: v })} aria-label="Voice speed" />
        </Field>
      </section>

      <section className="grid gap-4 border-t border-line pt-5">
        <h3 className="text-sm font-semibold">Captions</h3>
        <label className="flex items-center gap-3 text-sm">
          <Switch checked={cap.enabled !== false} onCheckedChange={(v) => update.mutate({ caption_style: { enabled: v } })} aria-label="Show captions" /> Show captions
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Animation" htmlFor="ps-anim"><Pick id="ps-anim" value={cap.animation ?? "karaoke"} items={opts(o?.caption_animations)} onChange={(v) => update.mutate({ caption_style: { animation: v as never } })} /></Field>
          <Field label="Font" htmlFor="ps-font"><Pick id="ps-font" value={cap.font ?? "Montserrat"} items={(o?.fonts ?? []).map((f) => ({ value: f, label: f }))} onChange={(v) => update.mutate({ caption_style: { font: v } })} /></Field>
          <Field label="Position" htmlFor="ps-pos"><Pick id="ps-pos" value={cap.position ?? "bottom"} items={opts(o?.caption_positions)} onChange={(v) => update.mutate({ caption_style: { position: v as never } })} /></Field>
          <Field label="Background" htmlFor="ps-bg"><Pick id="ps-bg" value={cap.background ?? "none"} items={[{ value: "none", label: "Outline" }, { value: "box", label: "Box" }, { value: "shadow", label: "Shadow" }]} onChange={(v) => update.mutate({ caption_style: { background: v as never } })} /></Field>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {([["color", "Text", "#FFFFFF"], ["highlight_color", "Spoken word", "#A78BFA"], ["emphasis_color", "Emphasis", "#FACC15"]] as const).map(([key, name, fallback]) => (
            <label key={key} className="grid gap-1 text-xs text-faint">
              {name}
              <input type="color" defaultValue={(cap[key] as string | undefined)?.slice(0, 7) ?? fallback} onBlur={(e) => update.mutate({ caption_style: { [key]: e.target.value.toUpperCase() } })} className="h-8 w-full cursor-pointer rounded border border-line bg-transparent" />
            </label>
          ))}
        </div>
        <Field label={`Size: ${Math.round((cap.size ?? 0.062) * 1000) / 10}% of width`}>
          <Slider min={0.04} max={0.1} step={0.002} defaultValue={[cap.size ?? 0.062]} onValueCommit={([v]) => update.mutate({ caption_style: { size: v } })} aria-label="Caption size" />
        </Field>
        <label className="flex items-center gap-3 text-sm">
          <Switch checked={cap.uppercase !== false} onCheckedChange={(v) => update.mutate({ caption_style: { uppercase: v } })} aria-label="Uppercase captions" /> Uppercase
        </label>
      </section>

      <section className="grid gap-4 border-t border-line pt-5">
        <h3 className="text-sm font-semibold">Music and sound</h3>
        <Field label="Score" htmlFor="ps-music">
          <Pick
            id="ps-music"
            value={s.music.enabled === false ? "none" : s.music.track_id ?? s.music.mood ?? "auto"}
            items={[{ value: "auto", label: "Match the story" }, { value: "none", label: "No music" }, ...tracks.map((t) => ({ value: t.id ?? t.mood, label: t.source === "upload" ? `${t.name} (yours)` : t.name }))]}
            onChange={(v) => {
              const track = tracks.find((t) => t.id === v);
              update.mutate({ music: v === "none" ? { enabled: false } : v === "auto" ? { enabled: true, mood: null, track_id: null } : track ? { enabled: true, track_id: v, mood: null } : { enabled: true, mood: v, track_id: null } });
            }}
          />
        </Field>
        <Field label={`Music level: ${s.music.volume_db ?? -20} dB`} hint="Music is automatically lowered under the narration.">
          <Slider min={-36} max={-8} step={1} defaultValue={[s.music.volume_db ?? -20]} onValueCommit={([v]) => update.mutate({ music: { volume_db: v } })} aria-label="Music volume" />
        </Field>
        <label className="flex items-center gap-3 text-sm">
          <Switch checked={s.sfx_enabled} onCheckedChange={(v) => update.mutate({ sfx_enabled: v })} aria-label="Sound effects" /> Sound effects
        </label>
      </section>

      <section className="grid gap-4 border-t border-line pt-5">
        <Field label="Watermark handle" htmlFor="ps-handle" hint="Shown small in the corner. Leave empty for none.">
          <Input id="ps-handle" defaultValue={s.brand.handle ?? ""} maxLength={40} placeholder="@yourchannel" onBlur={(e) => e.target.value !== (s.brand.handle ?? "") && update.mutate({ brand_handle: e.target.value })} />
        </Field>
      </section>
    </div>
  );
}
