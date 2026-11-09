import { AlertTriangle, Pause, Play } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useProviders } from "@/hooks/queries";
import { PROJECT_STATUS_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import { errorMessage } from "@/services/http";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold text-text md:text-4xl">{title}</h1>
        {description && <p className="mt-2 text-subtle">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-xl border border-dashed border-line-strong p-8">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-subtle">{body}</p>
      {action}
    </div>
  );
}

export function ErrorNotice({ error, className }: { error: unknown; className?: string }) {
  return (
    <div role="alert" className={cn("flex items-start gap-2 rounded-lg border border-bad/40 bg-bad/10 p-3 text-sm text-bad", className)}>
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{errorMessage(error)}</span>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  ready: "text-ok",
  completed: "text-ok",
  failed: "text-bad",
  producing: "text-beam",
  generating_story: "text-beam",
  storyboard_ready: "text-uv",
  draft: "text-faint",
};

export function StatusDot({ status, label }: { status: string; label?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs", STATUS_TONE[status] ?? "text-subtle")}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {label ?? PROJECT_STATUS_LABEL[status] ?? status}
    </span>
  );
}

/** Play/pause for a (possibly lazily fetched) audio URL. */
export function AudioButton({ load, label, className }: { load: () => Promise<string>; label: string; className?: string }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  useEffect(() => () => audio.current?.pause(), []);
  const toggle = async () => {
    if (state === "playing") {
      audio.current?.pause();
      setState("idle");
      return;
    }
    try {
      setState("loading");
      const src = await load();
      audio.current?.pause();
      audio.current = new Audio(src);
      audio.current.onended = () => setState("idle");
      await audio.current.play();
      setState("playing");
    } catch (e) {
      setState("idle");
      const { toast } = await import("sonner");
      toast.error(errorMessage(e));
    }
  };
  return (
    <button
      type="button"
      onClick={toggle}
      className={cn("inline-flex size-8 items-center justify-center rounded-full border border-line-strong text-text hover:border-uv hover:text-uv", className)}
      aria-label={state === "playing" ? `Stop ${label}` : `Play ${label}`}
    >
      {state === "playing" ? <Pause className="size-3.5" /> : <Play className={cn("size-3.5", state === "loading" && "animate-pulse")} />}
    </button>
  );
}

/** Names offline AI services in plain terms and says what still works. */
export function ProviderBanner({ kinds }: { kinds?: string[] }) {
  const { data } = useProviders();
  if (!data) return null;
  const down = data.filter((p) => !p.available && (!kinds || kinds.includes(p.kind)));
  const test = data.filter((p) => p.is_test_double);
  if (!down.length && !test.length) return null;
  const names: Record<string, string> = {
    llm: "Story Director (Ollama)",
    image: "image generation (ComfyUI)",
    tts: "voice (Kokoro)",
    stt: "caption timing (Whisper)",
    research: "fact checking (Wikipedia)",
  };
  return (
    <div className="mb-6 rounded-lg border border-warn/30 bg-warn/5 p-3 text-sm text-subtle">
      {down.length > 0 && (
        <p>
          <span className="text-warn">Offline: {down.map((p) => names[p.kind] ?? p.name).join(", ")}.</span>{" "}
          {down.some((p) => p.kind === "image") && "Scenes will use procedural art until ComfyUI is back. "}
          {down.some((p) => p.kind === "llm") && "You can still edit scenes by hand and render. "}
          <Link to="/settings#ai" className="text-uv underline-offset-4 hover:underline">
            See AI status
          </Link>
        </p>
      )}
      {test.length > 0 && <p className="mt-1">Test mode: deterministic stand-ins are active for {test.map((p) => names[p.kind] ?? p.name).join(", ")}.</p>}
    </div>
  );
}

export function Field({ label, hint, htmlFor, children }: { label: string; hint?: string; htmlFor?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-text">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-faint">{hint}</p>}
    </div>
  );
}

export function Swatch({ color, className }: { color: string; className?: string }) {
  return <span className={cn("inline-block size-4 rounded-sm border border-white/10", className)} style={{ background: color }} title={color} />;
}
