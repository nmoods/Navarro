import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { AudioButton, ErrorNotice, Field, PageHeader, ProviderBanner } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { keys } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { creativeApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";

const SAMPLE = "In 1587, more than one hundred colonists landed on Roanoke Island. Three years later, every one of them was gone.";

export default function VoiceStudioPage() {
  const qc = useQueryClient();
  const voices = useQuery({ queryKey: keys.voices, queryFn: creativeApi.voices });
  const profiles = useQuery({ queryKey: keys.voiceProfiles, queryFn: creativeApi.voiceProfiles });
  const music = useQuery({ queryKey: keys.music, queryFn: creativeApi.music });
  const [lang, setLang] = useState("en");
  const [text, setText] = useState(SAMPLE);
  const [speed, setSpeed] = useState(1);
  const [primary, setPrimary] = useState("am_michael");
  const [blendWith, setBlendWith] = useState("none");
  const [mix, setMix] = useState(0.3);
  const [name, setName] = useState("");

  const voiceId = blendWith === "none" ? primary : `${primary}:${(1 - mix).toFixed(2)},${blendWith}:${mix.toFixed(2)}`;
  const languages = useMemo(() => [...new Set((voices.data ?? []).map((v) => v.language))], [voices.data]);
  const list = (voices.data ?? []).filter((v) => v.language === lang);

  const save = useMutation({
    mutationFn: () => creativeApi.createVoiceProfile({ name: name.trim(), voice_id: voiceId, speed }),
    onSuccess: () => { setName(""); qc.invalidateQueries({ queryKey: keys.voiceProfiles }); toast("Voice saved"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({ mutationFn: creativeApi.removeVoiceProfile, onSuccess: () => qc.invalidateQueries({ queryKey: keys.voiceProfiles }) });

  return (
    <Page wide>
      <PageHeader title="Voice studio" description="Audition every narrator, blend two voices into a signature sound and preview the royalty-free scores." />
      <ProviderBanner kinds={["tts"]} />
      {voices.error ? <ErrorNotice error={voices.error} className="mb-6" /> : null}
      <div className="grid gap-10 xl:grid-cols-[1.4fr_1fr]">
        <section className="grid content-start gap-6">
          <Field label="Test line" htmlFor="sample">
            <Textarea id="sample" rows={3} value={text} onChange={(e) => setText(e.target.value)} maxLength={300} />
          </Field>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Language">
            {languages.map((l) => (
              <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)} className={cn("rounded-md border px-2.5 py-1 text-xs uppercase", lang === l ? "border-uv text-text" : "border-line text-subtle")}>{l}</button>
            ))}
          </div>
          <ul className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
            {list.map((v) => (
              <li key={v.id} className={cn("flex items-center gap-3 rounded-lg border p-3", primary === v.id ? "border-uv bg-uv/10" : "border-line")}>
                <AudioButton label={`${v.name} sample`} load={() => creativeApi.previewVoice({ voice_id: v.id, text, speed, language: lang })} />
                <button type="button" className="min-w-0 flex-1 text-left" onClick={() => setPrimary(v.id)}>
                  <p className="truncate text-sm font-medium">{v.name}</p>
                  <p className="text-xs text-faint">{v.accent} · {v.gender}</p>
                </button>
              </li>
            ))}
          </ul>
          <p className="text-xs text-faint">Voices: Kokoro-82M (Apache-2.0), generated on this machine.</p>
        </section>

        <aside className="grid content-start gap-6 rounded-xl border border-line p-5">
          <h2 className="text-lg font-semibold">Build a signature voice</h2>
          <p className="-mt-4 text-sm text-subtle">Blending mixes the style of two narrators. Selected: <span className="text-text">{primary}</span></p>
          <Field label="Blend with" htmlFor="blend">
            <Select value={blendWith} onValueChange={setBlendWith}>
              <SelectTrigger id="blend" className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No blend</SelectItem>
                {list.filter((v) => v.id !== primary).map((v) => <SelectItem key={v.id} value={v.id}>{v.name} ({v.accent} {v.gender})</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          {blendWith !== "none" && (
            <Field label={`Mix: ${Math.round((1 - mix) * 100)}% / ${Math.round(mix * 100)}%`}>
              <Slider min={0.1} max={0.9} step={0.05} value={[mix]} onValueChange={([v]) => setMix(v)} aria-label="Blend amount" />
            </Field>
          )}
          <Field label={`Speed: ${speed.toFixed(2)}×`}>
            <Slider min={0.7} max={1.4} step={0.05} value={[speed]} onValueChange={([v]) => setSpeed(v)} aria-label="Speed" />
          </Field>
          <div className="flex items-center gap-3">
            <AudioButton label="signature voice" load={() => creativeApi.previewVoice({ voice_id: voiceId, text, speed, language: lang })} />
            <span className="text-sm text-subtle">Listen to the result</span>
          </div>
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) save.mutate(); }}>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name this voice" aria-label="Voice name" maxLength={80} />
            <Button type="submit" disabled={!name.trim() || save.isPending}>Save</Button>
          </form>
          {profiles.data?.length ? (
            <ul className="grid gap-2 border-t border-line pt-4">
              {profiles.data.map((p) => (
                <li key={p.id} className="flex items-center gap-3 text-sm">
                  <AudioButton label={p.name} load={() => creativeApi.previewVoice({ voice_id: p.voice_id, text, speed: p.speed, language: lang })} />
                  <div className="min-w-0 flex-1"><p className="truncate">{p.name}</p><p className="truncate text-xs text-faint">{p.voice_id} · {p.speed}×</p></div>
                  <Button size="sm" variant="ghost" className="text-faint" onClick={() => remove.mutate(p.id)}>Remove</Button>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="text-xs text-faint">Use a saved voice by entering its voice code in a project or Story DNA.</p>
        </aside>
      </div>

      <section className="mt-12">
        <h2 className="text-lg font-semibold">Music</h2>
        <p className="mt-1 text-sm text-subtle">Each video gets an original score composed to its scene cues: building, tension, drops and resolution.</p>
        <ul className="mt-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {(music.data ?? []).filter((t) => t.source === "procedural").map((t) => (
            <li key={t.mood} className="flex items-center gap-3 rounded-lg border border-line p-3">
              <AudioButton label={`${t.name} preview`} load={() => creativeApi.musicPreview(t.mood)} />
              <span className="text-sm">{label(t.mood)}</span>
            </li>
          ))}
        </ul>
      </section>
    </Page>
  );
}
