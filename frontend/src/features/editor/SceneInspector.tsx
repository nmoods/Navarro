import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImageUp, RefreshCw, Sparkles, Trash2, Wand2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Field, Swatch } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { keys, useOptions } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { scenesApi, type SceneUpdate } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Scene } from "@/types/api";
import { VisualDataEditor } from "./VisualDataEditor";

function Pick({ id, value, values, onChange }: { id: string; value: string; values: string[]; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{values.map((x) => <SelectItem key={x} value={x}>{label(x)}</SelectItem>)}</SelectContent>
    </Select>
  );
}

function Toggles({ values, selected, max, onChange }: { values: string[]; selected: string[]; max: number; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {values.map((x) => {
        const on = selected.includes(x);
        return (
          <button
            key={x}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(on ? selected.filter((s) => s !== x) : [...selected, x].slice(-max))}
            className={cn("rounded-md border px-2 py-1 text-xs", on ? "border-uv bg-uv/15 text-text" : "border-line text-subtle hover:text-text")}
          >
            {label(x)}
          </button>
        );
      })}
    </div>
  );
}

export function SceneInspector({ scene, projectId, index, busy, onJob }: { scene: Scene; projectId: string; index: number; busy: boolean; onJob: (jobId: string) => void }) {
  const qc = useQueryClient();
  const { data: o } = useOptions();
  const [narration, setNarration] = useState(scene.narration);
  const [prompt, setPrompt] = useState(scene.image_prompt);
  const [instruction, setInstruction] = useState("");
  const [saved, setSaved] = useState<"idle" | "saving" | "saved">("idle");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setNarration(scene.narration);
    setPrompt(scene.image_prompt);
  }, [scene.id, scene.narration, scene.image_prompt]);

  const refresh = () => qc.invalidateQueries({ queryKey: keys.storyboard(projectId) });
  const save = useMutation({
    mutationFn: (body: SceneUpdate) => scenesApi.update(scene.id, body),
    onMutate: () => setSaved("saving"),
    onSuccess: () => { setSaved("saved"); refresh(); },
    onError: (e) => { setSaved("idle"); toast.error(errorMessage(e)); },
  });
  const patch = (body: SceneUpdate) => save.mutate(body);

  const regenerate = useMutation({
    mutationFn: (parts: ("visual_plan" | "narration" | "image")[]) => scenesApi.regenerate(scene.id, parts, instruction),
    onSuccess: (job) => { onJob(job.id); toast("Regenerating this scene. Other scenes are untouched."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const upload = useMutation({
    mutationFn: (file: File) => scenesApi.uploadImage(scene.id, file),
    onSuccess: () => { refresh(); toast("Image replaced and pinned to this scene."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: () => scenesApi.remove(scene.id),
    onSuccess: refresh,
    onError: (e) => toast.error(errorMessage(e)),
  });
  const history = useQuery({ queryKey: ["scene-history", scene.id, scene.image?.id], queryFn: () => scenesApi.history(scene.id), enabled: Boolean(scene.image) });
  const restore = useMutation({
    mutationFn: (linkId: string) => scenesApi.restore(scene.id, linkId),
    onSuccess: refresh,
  });

  const caption = scene.caption_override ?? {};
  const textChanged = narration.trim() !== scene.narration;

  return (
    <div className="grid gap-6 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs text-faint">Scene {index + 1}</p>
          <Input
            key={scene.id}
            defaultValue={scene.title}
            onBlur={(e) => e.target.value.trim() && e.target.value !== scene.title && patch({ title: e.target.value.trim() })}
            className="mt-1 h-8 border-transparent bg-transparent px-0 font-heading text-lg font-semibold focus-visible:border-line"
            aria-label="Scene title"
          />
        </div>
        <span className="shrink-0 pt-6 text-xs text-faint" aria-live="polite">{saved === "saving" ? "Saving…" : saved === "saved" ? "Saved" : ""}</span>
      </div>

      <Field label="Narration" htmlFor="narration" hint="Changing the words re-voices only this scene on the next render.">
        <Textarea id="narration" rows={5} value={narration} onChange={(e) => setNarration(e.target.value)} />
        {textChanged && (
          <div className="flex gap-2">
            <Button size="sm" onClick={() => patch({ narration: narration.trim() })} disabled={!narration.trim()}>Save narration</Button>
            <Button size="sm" variant="ghost" onClick={() => setNarration(scene.narration)}>Discard</Button>
          </div>
        )}
      </Field>

      <section className="grid gap-3 rounded-lg border border-line p-3">
        <p className="text-sm font-medium">Regenerate this scene</p>
        <Input placeholder="Director note, e.g. “show the ships at night”" value={instruction} onChange={(e) => setInstruction(e.target.value)} aria-label="Director note" maxLength={400} />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={busy || regenerate.isPending} onClick={() => regenerate.mutate(["image"])}><RefreshCw className="size-3.5" /> New image</Button>
          <Button size="sm" variant="outline" disabled={busy || regenerate.isPending} onClick={() => regenerate.mutate(["visual_plan", "image"])}><Wand2 className="size-3.5" /> Re-direct visuals</Button>
          <Button size="sm" variant="outline" disabled={busy || regenerate.isPending} onClick={() => regenerate.mutate(["narration", "visual_plan", "image"])}><Sparkles className="size-3.5" /> Rewrite scene</Button>
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Visual" htmlFor="visual_type">
          <Pick id="visual_type" value={scene.visual_type} values={o?.visual_types ?? [scene.visual_type]} onChange={(v) => patch({ visual_type: v })} />
        </Field>
        <Field label="Camera" htmlFor="camera">
          <Pick id="camera" value={scene.camera_movement} values={o?.camera_moves ?? [scene.camera_movement]} onChange={(v) => patch({ camera_movement: v })} />
        </Field>
        <Field label="Transition in" htmlFor="transition" hint={index === 0 ? "The first scene always opens on a cut." : undefined}>
          <Pick id="transition" value={scene.transition} values={o?.transitions ?? [scene.transition]} onChange={(v) => patch({ transition: v })} />
        </Field>
        <Field label="Music cue" htmlFor="music_cue">
          <Pick id="music_cue" value={scene.music_cue} values={["build", "steady", "tension", "drop", "resolve", "calm"]} onChange={(v) => patch({ music_cue: v })} />
        </Field>
      </div>

      <Field label="Atmosphere" hint="Up to three effects layered over the image.">
        <Toggles values={o?.effects ?? []} selected={scene.effects} max={3} onChange={(v) => patch({ effects: v })} />
      </Field>
      <Field label="Sound effects">
        <Toggles values={o?.sound_effects ?? []} selected={scene.sound_effects} max={3} onChange={(v) => patch({ sound_effects: v })} />
      </Field>

      <VisualDataEditor scene={scene} onSave={(visual_data) => patch({ visual_data })} />

      <section className="grid gap-3">
        <p className="text-sm font-medium">Image</p>
        {scene.image && (
          <div className="flex flex-wrap gap-2">
            {(history.data ?? []).map((a) => (
              <button
                type="button"
                key={a.id}
                onClick={() => !a.is_current && restore.mutate(a.id)}
                className={cn("h-20 w-[45px] overflow-hidden rounded border", a.is_current ? "border-uv" : "border-line opacity-70 hover:opacity-100")}
                aria-label={a.is_current ? "Current image" : "Use this earlier image"}
              >
                <img src={a.url} alt="" className="size-full object-cover" />
              </button>
            ))}
          </div>
        )}
        <Field label="Image prompt" htmlFor="prompt">
          <Textarea id="prompt" rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} onBlur={() => prompt !== scene.image_prompt && patch({ image_prompt: prompt })} />
        </Field>
        <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])} />
        <Button size="sm" variant="outline" onClick={() => fileInput.current?.click()} disabled={upload.isPending}><ImageUp className="size-3.5" /> Use my own image</Button>
      </section>

      <section className="grid gap-4">
        <p className="text-sm font-medium">Captions for this scene</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Animation" htmlFor="cap_anim">
            <Pick id="cap_anim" value={caption.animation ?? "inherit"} values={["inherit", ...(o?.caption_animations ?? [])]} onChange={(v) => patch({ caption_override: v === "inherit" ? { ...caption, animation: undefined } : { ...caption, animation: v as never } })} />
          </Field>
          <Field label="Position" htmlFor="cap_pos">
            <Pick id="cap_pos" value={caption.position ?? "inherit"} values={["inherit", "top", "middle", "bottom"]} onChange={(v) => patch({ caption_override: { ...caption, position: v === "inherit" ? undefined : (v as never) } })} />
          </Field>
        </div>
        <Field label={`Timing offset: ${caption.offset_ms ?? 0} ms`} hint="Nudge captions earlier or later against the voice.">
          <Slider min={-600} max={600} step={20} value={[caption.offset_ms ?? 0]} onValueCommit={([v]) => patch({ caption_override: { ...caption, offset_ms: v } })} aria-label="Caption timing offset" />
        </Field>
        <Field label="Highlighted words" htmlFor="emph" hint="Comma separated. These get the emphasis colour.">
          <Input id="emph" key={scene.id + scene.emphasis_words.join()} defaultValue={scene.emphasis_words.join(", ")} onBlur={(e) => patch({ emphasis_words: e.target.value.split(",").map((w) => w.trim()).filter(Boolean).slice(0, 6) })} />
        </Field>
      </section>

      <Field label={`Minimum duration: ${scene.duration_override ? `${scene.duration_override.toFixed(1)} s` : "fit narration"}`}>
        <Slider min={0} max={20} step={0.5} value={[scene.duration_override ?? 0]} onValueCommit={([v]) => patch({ duration_override: v || null })} aria-label="Minimum scene duration" />
      </Field>

      {scene.color_palette.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-faint">Palette {scene.color_palette.map((c) => <Swatch key={c} color={c} />)}</div>
      )}

      <Button variant="ghost" className="justify-start text-bad hover:text-bad" onClick={() => remove.mutate()} disabled={remove.isPending}>
        <Trash2 className="size-4" /> Delete scene
      </Button>
    </div>
  );
}
