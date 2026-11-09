import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Page } from "@/app/AppShell";
import { EmptyState, ErrorNotice, Field, PageHeader, ProviderBanner, StatusDot } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { keys, useOptions } from "@/hooks/queries";
import { label, relativeTime } from "@/lib/format";
import { creativeApi, planningApi } from "@/services/endpoints";

export default function SeriesPage() {
  const navigate = useNavigate();
  const { data: o } = useOptions();
  const list = useQuery({ queryKey: keys.series, queryFn: planningApi.series });
  const dna = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const [theme, setTheme] = useState("");
  const [count, setCount] = useState(5);
  const [duration, setDuration] = useState(60);
  const [tone, setTone] = useState("documentary");
  const [dnaId, setDnaId] = useState("none");
  const create = useMutation({
    mutationFn: () => planningApi.createSeries({ theme, episode_count: count, duration_seconds: duration, story_tone: tone, story_dna_id: dnaId === "none" ? null : dnaId }),
    onSuccess: (s) => navigate(`/series/${s.id}`),
  });

  return (
    <Page>
      <PageHeader title="Series Factory" description="Plan connected episodes with a shared series bible, review them, then produce the whole run in a queue." />
      <ProviderBanner kinds={["llm"]} />
      <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr]">
        <form className="grid content-start gap-5" onSubmit={(e) => { e.preventDefault(); if (theme.trim().length >= 3) create.mutate(); }}>
          <h2 className="text-lg font-semibold">Plan a new series</h2>
          <Field label="Series theme" htmlFor="theme" hint="For example: “Unsolved disappearances at sea”.">
            <Textarea id="theme" rows={3} value={theme} onChange={(e) => setTheme(e.target.value)} />
          </Field>
          <Field label={`Episodes: ${count}`}>
            <Slider min={2} max={20} step={1} value={[count]} onValueChange={([v]) => setCount(v)} aria-label="Number of episodes" />
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Length" htmlFor="len">
              <Select value={String(duration)} onValueChange={(v) => setDuration(Number(v))}>
                <SelectTrigger id="len" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{[30, 45, 60, 90].map((d) => <SelectItem key={d} value={String(d)}>{d} s</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Tone" htmlFor="tone">
              <Select value={tone} onValueChange={setTone}>
                <SelectTrigger id="tone" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>{(o?.story_tones ?? []).map((t) => <SelectItem key={t} value={t}>{label(t)}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Story DNA" htmlFor="sdna">
              <Select value={dnaId} onValueChange={setDnaId}>
                <SelectTrigger id="sdna" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {(dna.data ?? []).map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
          </div>
          {create.error ? <ErrorNotice error={create.error} /> : null}
          <Button type="submit" className="justify-self-start" disabled={create.isPending || theme.trim().length < 3}>Plan episodes</Button>
        </form>

        <section>
          <h2 className="mb-4 text-lg font-semibold">Your series</h2>
          {list.data?.length ? (
            <ul className="divide-y divide-line rounded-xl border border-line">
              {list.data.map((s) => {
                const done = s.episodes.filter((e) => e.status === "completed").length;
                return (
                  <li key={s.id}>
                    <Link to={`/series/${s.id}`} className="flex items-center justify-between gap-4 p-4 hover:bg-raised/50">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{s.title}</p>
                        <p className="mt-0.5 text-xs text-faint">{done}/{s.episodes.length || s.episode_count} episodes produced · {relativeTime(s.created_at)}</p>
                      </div>
                      <StatusDot status={s.status === "planned" ? "storyboard_ready" : s.status === "completed" ? "ready" : s.status === "planning" ? "generating_story" : s.status} label={label(s.status)} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="No series yet" body="A series keeps characters, places and visual style consistent from one episode to the next." />
          )}
        </section>
      </div>
    </Page>
  );
}
