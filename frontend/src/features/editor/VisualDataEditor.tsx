import { useEffect, useState } from "react";
import { Field } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { Scene, VisualData } from "@/types/api";

const lines = (s: string) => s.split("\n").map((l) => l.trim()).filter(Boolean);

/** Structured editors for procedural visuals (maps, timelines, infographics...). Plain text in, typed data out. */
export function VisualDataEditor({ scene, onSave }: { scene: Scene; onSave: (data: VisualData) => void }) {
  const d = scene.visual_data ?? {};
  const [text, setText] = useState("");
  const [extra, setExtra] = useState("");

  useEffect(() => {
    switch (scene.visual_type) {
      case "historical_map":
        setText((d.places ?? []).map((p) => p.name).join("\n"));
        break;
      case "timeline":
        setText((d.events ?? []).map((e) => `${e.date} | ${e.label}`).join("\n"));
        break;
      case "infographic":
        setText((d.stats ?? []).map((s) => `${s.label} | ${s.value} | ${s.unit ?? ""}`).join("\n"));
        break;
      case "kinetic_typography":
        setText((d.kinetic_lines ?? []).join("\n"));
        break;
      case "newspaper":
        setText(d.headline ?? "");
        setExtra(d.dateline ?? "");
        break;
      case "comparison":
        setText([d.left?.label ?? "", ...(d.left?.points ?? [])].join("\n"));
        setExtra([d.right?.label ?? "", ...(d.right?.points ?? [])].join("\n"));
        break;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene.id, scene.visual_type, scene.updated_at]);

  const build = (): VisualData => {
    switch (scene.visual_type) {
      case "historical_map":
        return { ...d, places: lines(text).slice(0, 6).map((name) => ({ name })) };
      case "timeline":
        return { ...d, events: lines(text).slice(0, 6).map((l) => { const [date, ...rest] = l.split("|"); return { date: date.trim(), label: rest.join("|").trim() || date.trim() }; }) };
      case "infographic":
        return {
          ...d,
          stats: lines(text).slice(0, 5).map((l) => { const [lbl, value, unit] = l.split("|").map((x) => x.trim()); return { label: lbl, value: Number.parseFloat(value) || 0, unit: unit ?? "" }; }),
        };
      case "kinetic_typography":
        return { ...d, kinetic_lines: lines(text).slice(0, 4) };
      case "newspaper":
        return { ...d, headline: text.trim(), dateline: extra.trim() };
      case "comparison": {
        const [l, ...lp] = lines(text);
        const [r, ...rp] = lines(extra);
        return { ...d, left: { label: l ?? "Before", points: lp.slice(0, 4) }, right: { label: r ?? "After", points: rp.slice(0, 4) } };
      }
      default:
        return d;
    }
  };

  const config: Record<string, { label: string; hint: string; second?: string }> = {
    historical_map: { label: "Places", hint: "One place per line, in travel order. Names are located offline." },
    timeline: { label: "Events", hint: "One per line: 1587 | Colony founded" },
    infographic: { label: "Figures", hint: "One per line: Colonists | 115 | people" },
    kinetic_typography: { label: "Lines on screen", hint: "Up to four short lines." },
    newspaper: { label: "Headline", hint: "Shown on the front page.", second: "Dateline" },
    comparison: { label: "Left side", hint: "First line is the label, then up to four points.", second: "Right side" },
  };
  const c = config[scene.visual_type];
  if (!c) return null;
  return (
    <section className="grid gap-3 rounded-lg border border-line p-3">
      <Field label={c.label} htmlFor="vd-main" hint={c.hint}>
        {scene.visual_type === "newspaper" ? (
          <Input id="vd-main" value={text} onChange={(e) => setText(e.target.value)} maxLength={90} />
        ) : (
          <Textarea id="vd-main" rows={4} value={text} onChange={(e) => setText(e.target.value)} />
        )}
      </Field>
      {c.second && (
        <Field label={c.second} htmlFor="vd-second">
          {scene.visual_type === "newspaper" ? (
            <Input id="vd-second" value={extra} onChange={(e) => setExtra(e.target.value)} maxLength={60} />
          ) : (
            <Textarea id="vd-second" rows={4} value={extra} onChange={(e) => setExtra(e.target.value)} />
          )}
        </Field>
      )}
      <Button size="sm" variant="outline" onClick={() => onSave(build())} className="justify-self-start">Apply to scene</Button>
    </section>
  );
}
