import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { EmptyState, ErrorNotice, Field, PageHeader, Swatch } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { keys, useOptions } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { creativeApi, type StoryDnaInput } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { StoryDna } from "@/types/api";

const BLANK: StoryDnaInput = {
  name: "", description: "", visual_style: "cinematic_documentary", style_prompt: "", color_palette: ["#120F1F", "#9D7BFF", "#6FB7FF"],
  typography: {}, voice_id: "am_michael", voice_speed: 1, caption_style: { animation: "karaoke", font: "Montserrat" },
  animation_preferences: { camera: [] }, music_preferences: { enabled: true, mood: "mystery", volume_db: -20 }, brand: {},
  visual_references: [], tone: "documentary",
};

function toInput(d: StoryDna): StoryDnaInput {
  const { id: _id, created_at: _c, updated_at: _u, ...rest } = d;
  return rest;
}

function Pick({ id, value, items, onChange }: { id: string; value: string; items: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full"><SelectValue /></SelectTrigger>
      <SelectContent>{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}</SelectContent>
    </Select>
  );
}

export default function StoryDnaPage() {
  const qc = useQueryClient();
  const { data: o } = useOptions();
  const list = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const voices = useQuery({ queryKey: keys.voices, queryFn: creativeApi.voices });
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState<StoryDnaInput>(BLANK);

  useEffect(() => {
    if (editing === "new") setForm(BLANK);
    else if (editing) { const d = list.data?.find((x) => x.id === editing); if (d) setForm(toInput(d)); }
  }, [editing, list.data]);

  const save = useMutation({
    mutationFn: () => (editing && editing !== "new" ? creativeApi.updateDna(editing, form) : creativeApi.createDna(form)),
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: keys.dna }); setEditing(d.id); toast("Story DNA saved. New videos using it inherit these settings."); },
  });
  const remove = useMutation({ mutationFn: creativeApi.removeDna, onSuccess: () => { setEditing(null); qc.invalidateQueries({ queryKey: keys.dna }); }, onError: (e) => toast.error(errorMessage(e)) });
  const set = <K extends keyof StoryDnaInput>(k: K, v: StoryDnaInput[K]) => setForm((f) => ({ ...f, [k]: v }));
  const opts = (xs?: string[]) => (xs ?? []).map((x) => ({ value: x, label: label(x) }));
  const camera = form.animation_preferences.camera ?? [];

  return (
    <Page wide>
      <PageHeader title="Story DNA" description="A reusable creative identity for a channel: how it looks, sounds and moves. Every video and series built on it stays on-brand." actions={<Button onClick={() => setEditing("new")}><Plus className="size-4" /> New profile</Button>} />
      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <nav aria-label="Profiles" className="grid content-start gap-1">
          {list.data?.map((d) => (
            <button key={d.id} type="button" onClick={() => setEditing(d.id)} className={cn("flex items-center gap-3 rounded-lg border p-3 text-left", editing === d.id ? "border-uv bg-uv/10" : "border-line hover:border-line-strong")}>
              <span className="flex">{d.color_palette.slice(0, 3).map((c) => <Swatch key={c} color={c} className="-mr-1 size-5 rounded-full" />)}</span>
              <span className="min-w-0"><span className="block truncate text-sm font-medium">{d.name}</span><span className="block truncate text-xs text-faint">{label(d.visual_style)}</span></span>
            </button>
          ))}
          {!list.data?.length && !editing && <EmptyState title="No profiles yet" body="Create one per channel or series so you never set up styles twice." />}
        </nav>

        {editing && (
          <form className="grid max-w-3xl gap-6" onSubmit={(e) => { e.preventDefault(); if (form.name.trim()) save.mutate(); }}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Profile name" htmlFor="dna-name"><Input id="dna-name" value={form.name} onChange={(e) => set("name", e.target.value)} maxLength={120} required /></Field>
              <Field label="Watermark handle" htmlFor="dna-handle"><Input id="dna-handle" value={form.brand.handle ?? ""} onChange={(e) => set("brand", { ...form.brand, handle: e.target.value })} placeholder="@channel" maxLength={40} /></Field>
            </div>
            <Field label="What is this channel about?" htmlFor="dna-desc" hint="The Story Director reads this when writing.">
              <Textarea id="dna-desc" rows={2} value={form.description} onChange={(e) => set("description", e.target.value)} maxLength={600} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Visual style" htmlFor="dna-style"><Pick id="dna-style" value={form.visual_style} items={opts(o?.visual_styles)} onChange={(v) => set("visual_style", v)} /></Field>
              <Field label="Story tone" htmlFor="dna-tone"><Pick id="dna-tone" value={form.tone} items={opts(o?.story_tones)} onChange={(v) => set("tone", v)} /></Field>
            </div>
            <Field label="Image style keywords" htmlFor="dna-prompt" hint="Added to every image prompt, e.g. “muted teal and amber, foggy, 35mm film”.">
              <Input id="dna-prompt" value={form.style_prompt} onChange={(e) => set("style_prompt", e.target.value)} maxLength={400} />
            </Field>
            <Field label="Palette" hint="Used by maps, timelines, infographics and procedural art.">
              <div className="flex flex-wrap items-center gap-2">
                {form.color_palette.map((c, i) => (
                  <input key={i} type="color" value={c} aria-label={`Palette colour ${i + 1}`} onChange={(e) => set("color_palette", form.color_palette.map((x, j) => (j === i ? e.target.value.toUpperCase() : x)))} className="h-9 w-12 cursor-pointer rounded border border-line bg-transparent" />
                ))}
                {form.color_palette.length < 5 && <Button type="button" size="sm" variant="ghost" onClick={() => set("color_palette", [...form.color_palette, "#FFFFFF"])}>Add colour</Button>}
              </div>
            </Field>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Narrator" htmlFor="dna-voice"><Pick id="dna-voice" value={form.voice_id} items={(voices.data ?? [{ id: form.voice_id, name: form.voice_id, accent: "", gender: "", language: "" }]).map((v) => ({ value: v.id, label: v.accent ? `${v.name} · ${v.accent}` : v.name }))} onChange={(v) => set("voice_id", v)} /></Field>
              <Field label="Caption animation" htmlFor="dna-cap"><Pick id="dna-cap" value={form.caption_style.animation ?? "karaoke"} items={opts(o?.caption_animations)} onChange={(v) => set("caption_style", { ...form.caption_style, animation: v as never })} /></Field>
              <Field label="Caption font" htmlFor="dna-font"><Pick id="dna-font" value={form.caption_style.font ?? "Montserrat"} items={(o?.fonts ?? []).map((f) => ({ value: f, label: f }))} onChange={(v) => set("caption_style", { ...form.caption_style, font: v })} /></Field>
            </div>
            <Field label="Music mood" htmlFor="dna-music"><Pick id="dna-music" value={form.music_preferences.mood ?? "mystery"} items={opts(o?.music_moods)} onChange={(v) => set("music_preferences", { ...form.music_preferences, mood: v })} /></Field>
            <Field label="Preferred camera moves" hint="The Story Director favours these when they fit the scene.">
              <div className="flex flex-wrap gap-1.5">
                {(o?.camera_moves ?? []).map((m) => {
                  const on = camera.includes(m);
                  return (
                    <button key={m} type="button" aria-pressed={on} onClick={() => set("animation_preferences", { ...form.animation_preferences, camera: on ? camera.filter((x) => x !== m) : [...camera, m] })}
                      className={cn("rounded-md border px-2 py-1 text-xs", on ? "border-uv bg-uv/15" : "border-line text-subtle")}>{label(m)}</button>
                  );
                })}
              </div>
            </Field>
            {save.error ? <ErrorNotice error={save.error} /> : null}
            <div className="flex gap-2">
              <Button type="submit" disabled={save.isPending || !form.name.trim()}>Save profile</Button>
              {editing !== "new" && <Button type="button" variant="ghost" className="text-bad hover:text-bad" onClick={() => remove.mutate(editing)}><Trash2 className="size-4" /> Delete</Button>}
            </div>
          </form>
        )}
      </div>
    </Page>
  );
}
