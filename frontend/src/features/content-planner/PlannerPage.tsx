import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Lightbulb, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { ErrorNotice, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { keys } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { planningApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Idea } from "@/types/api";

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const STATUSES: Idea["status"][] = ["idea", "planned", "in_production", "published", "archived"];

export default function PlannerPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [month, setMonth] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const [title, setTitle] = useState("");
  const [theme, setTheme] = useState("");
  const [dragging, setDragging] = useState<string | null>(null);
  const ideas = useQuery({ queryKey: keys.ideas(), queryFn: () => planningApi.ideas() });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["ideas"] });

  const add = useMutation({ mutationFn: (body: Partial<Idea>) => planningApi.createIdea(body), onSuccess: () => { setTitle(""); invalidate(); } });
  const update = useMutation({ mutationFn: ({ id, ...body }: Partial<Idea> & { id: string; clear_schedule?: boolean }) => planningApi.updateIdea(id, body), onSuccess: invalidate, onError: (e) => toast.error(errorMessage(e)) });
  const remove = useMutation({ mutationFn: planningApi.removeIdea, onSuccess: invalidate });
  const toProject = useMutation({ mutationFn: planningApi.ideaToProject, onSuccess: (p) => navigate(`/projects/${p.id}`), onError: (e) => toast.error(errorMessage(e)) });
  const suggest = useMutation({
    mutationFn: () => planningApi.suggest(theme, 6),
    onSuccess: async (list) => {
      await Promise.all(list.map((i) => planningApi.createIdea({ title: i.title, notes: i.notes, tags: [theme.slice(0, 30)] })));
      invalidate();
      toast(`${list.length} ideas added to your list`);
    },
  });

  const days = useMemo(() => {
    const first = new Date(month);
    const offset = (first.getDay() + 6) % 7; // Monday first
    return Array.from({ length: 42 }, (_, i) => new Date(month.getFullYear(), month.getMonth(), i - offset + 1));
  }, [month]);
  const byDay = useMemo(() => {
    const map = new Map<string, Idea[]>();
    for (const idea of ideas.data ?? []) if (idea.scheduled_for) map.set(idea.scheduled_for, [...(map.get(idea.scheduled_for) ?? []), idea]);
    return map;
  }, [ideas.data]);
  const unscheduled = (ideas.data ?? []).filter((i) => !i.scheduled_for && i.status !== "archived");
  const today = iso(new Date());

  return (
    <Page wide>
      <PageHeader title="Content planner" description="Collect ideas, ask the Story Director for more, and drag them onto the calendar." />
      <div className="grid gap-8 xl:grid-cols-[340px_1fr]">
        <aside className="grid content-start gap-6">
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (title.trim()) add.mutate({ title: title.trim() }); }}>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Add an idea" aria-label="New idea" />
            <Button type="submit" size="icon" aria-label="Add idea"><Plus className="size-4" /></Button>
          </form>
          <form className="grid gap-2 rounded-lg border border-line p-3" onSubmit={(e) => { e.preventDefault(); if (theme.trim().length >= 3) suggest.mutate(); }}>
            <p className="flex items-center gap-2 text-sm font-medium"><Lightbulb className="size-4 text-uv" /> Topic discovery</p>
            <Input value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="A theme, e.g. lost cities" aria-label="Theme for suggestions" />
            <Button type="submit" variant="outline" size="sm" disabled={suggest.isPending}>{suggest.isPending ? "Thinking… (up to a minute on CPU)" : "Suggest six topics"}</Button>
            {suggest.error ? <ErrorNotice error={suggest.error} /> : null}
          </form>
          <section>
            <h2 className="mb-2 text-sm font-semibold">Unscheduled ({unscheduled.length})</h2>
            <ul className="grid gap-2">
              {unscheduled.map((idea) => (
                <li key={idea.id} draggable onDragStart={() => setDragging(idea.id)} onDragEnd={() => setDragging(null)} className="cursor-grab rounded-lg border border-line bg-surface p-3">
                  <p className="text-sm">{idea.title}</p>
                  {idea.notes && <p className="mt-1 line-clamp-2 text-xs text-faint">{idea.notes}</p>}
                  <div className="mt-2 flex flex-wrap gap-1">
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-uv" onClick={() => toProject.mutate(idea.id)}>Make video</Button>
                    <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => update.mutate({ id: idea.id, scheduled_for: today })}>Schedule today</Button>
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-faint" onClick={() => remove.mutate(idea.id)}>Delete</Button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section aria-label="Calendar">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-heading text-xl font-semibold">{month.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</h2>
            <div className="flex gap-1">
              <Button size="icon" variant="ghost" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}><ChevronLeft className="size-4" /></Button>
              <Button size="icon" variant="ghost" aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}><ChevronRight className="size-4" /></Button>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-line bg-line text-xs">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => <div key={d} className="bg-surface px-2 py-1.5 text-faint">{d}</div>)}
            {days.map((d) => {
              const key = iso(d);
              const inMonth = d.getMonth() === month.getMonth();
              return (
                <div
                  key={key}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => dragging && update.mutate({ id: dragging, scheduled_for: key, status: "planned" })}
                  className={cn("min-h-24 bg-ink p-1.5", !inMonth && "opacity-40", dragging && "hover:bg-uv/10")}
                >
                  <span className={cn("timecode text-[11px]", key === today ? "text-uv" : "text-faint")}>{d.getDate()}</span>
                  <ul className="mt-1 grid gap-1">
                    {(byDay.get(key) ?? []).map((idea) => (
                      <li key={idea.id} draggable onDragStart={() => setDragging(idea.id)} onDragEnd={() => setDragging(null)}
                        className={cn("cursor-grab truncate rounded px-1.5 py-0.5", idea.status === "published" ? "bg-ok/15 text-ok" : idea.status === "in_production" ? "bg-beam/15 text-beam" : "bg-uv/15 text-text")}
                        title={`${idea.title} · ${label(idea.status)}`}>
                        {idea.title}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
          <div className="mt-6">
            <h2 className="mb-2 text-sm font-semibold">Scheduled this month</h2>
            <ul className="divide-y divide-line rounded-xl border border-line">
              {(ideas.data ?? []).filter((i) => i.scheduled_for?.startsWith(iso(month).slice(0, 7))).map((idea) => (
                <li key={idea.id} className="flex flex-wrap items-center justify-between gap-3 p-3 text-sm">
                  <span className="min-w-0 truncate"><span className="timecode mr-2 text-xs">{idea.scheduled_for}</span>{idea.title}</span>
                  <span className="flex items-center gap-2">
                    <select value={idea.status} onChange={(e) => update.mutate({ id: idea.id, status: e.target.value as Idea["status"] })} className="rounded border border-line bg-surface px-2 py-1 text-xs" aria-label={`Status of ${idea.title}`}>
                      {STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
                    </select>
                    {idea.project_id ? <Button size="sm" variant="ghost" className="h-7 px-2 text-uv" onClick={() => navigate(`/projects/${idea.project_id}`)}>Open</Button> : <Button size="sm" variant="ghost" className="h-7 px-2 text-uv" onClick={() => toProject.mutate(idea.id)}>Make video</Button>}
                    <Button size="sm" variant="ghost" className="h-7 px-2 text-faint" onClick={() => update.mutate({ id: idea.id, clear_schedule: true, status: "idea" })}>Unschedule</Button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </Page>
  );
}
