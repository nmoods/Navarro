import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { EmptyState, ErrorNotice, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { keys } from "@/hooks/queries";
import { bytes, label, relativeTime, timecode } from "@/lib/format";
import { cn } from "@/lib/utils";
import { jobsApi, mediaApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";

const KINDS = [
  { value: "video", label: "Exports" },
  { value: "image", label: "Images" },
  { value: "audio", label: "Audio" },
] as const;

export default function MediaPage() {
  const qc = useQueryClient();
  const [kind, setKind] = useState<(typeof KINDS)[number]["value"]>("video");
  const [offset, setOffset] = useState(0);
  const imageInput = useRef<HTMLInputElement>(null);
  const audioInput = useRef<HTMLInputElement>(null);
  const params = { kind, limit: 40, offset };
  const media = useQuery({ queryKey: keys.media(params), queryFn: () => mediaApi.list(params) });
  const exports = useQuery({ queryKey: keys.allExports, queryFn: jobsApi.exports, enabled: kind === "video" });

  const upload = useMutation({
    mutationFn: ({ file, purpose }: { file: File; purpose: "image" | "music" }) => mediaApi.upload(file, purpose, file.name.replace(/\.[^.]+$/, "")),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["media"] }); qc.invalidateQueries({ queryKey: keys.music }); toast("Uploaded"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: mediaApi.remove,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["media"] }),
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Page wide>
      <PageHeader
        title="Media library"
        description="Everything ReelForge generated for you, plus your own images and music. Files are private to your account."
        actions={
          <>
            <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => e.target.files?.[0] && upload.mutate({ file: e.target.files[0], purpose: "image" })} />
            <input ref={audioInput} type="file" accept="audio/wav,audio/mpeg,audio/ogg,audio/flac,.wav,.mp3,.ogg,.flac" hidden onChange={(e) => e.target.files?.[0] && upload.mutate({ file: e.target.files[0], purpose: "music" })} />
            <Button variant="outline" onClick={() => imageInput.current?.click()} disabled={upload.isPending}><Upload className="size-4" /> Upload image</Button>
            <Button variant="outline" onClick={() => audioInput.current?.click()} disabled={upload.isPending}><Upload className="size-4" /> Upload music</Button>
          </>
        }
      />
      <p className="-mt-4 mb-6 text-xs text-faint">Only upload music and images you have the rights to use. Max 25 MB. PNG, JPEG, WebP, WAV, MP3, OGG or FLAC.</p>
      <div className="mb-6 flex gap-1.5" role="tablist">
        {KINDS.map((k) => (
          <button key={k.value} role="tab" aria-selected={kind === k.value} onClick={() => { setKind(k.value); setOffset(0); }}
            className={cn("rounded-md border px-3 py-1 text-sm", kind === k.value ? "border-uv text-text" : "border-line text-subtle hover:text-text")}>
            {k.label}
          </button>
        ))}
      </div>
      {media.error ? <ErrorNotice error={media.error} /> : null}

      {kind === "video" ? (
        exports.data?.length ? (
          <ul className="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6">
            {exports.data.map((e) => (
              <li key={e.id}>
                <video src={e.video_url} poster={e.thumbnail_url ?? undefined} controls preload="none" className={cn("w-full rounded-lg border border-line bg-ink", e.aspect_ratio === "16:9" ? "aspect-video" : e.aspect_ratio === "1:1" ? "aspect-square" : "frame-916")} />
                <p className="mt-2 truncate text-sm">{e.project_title}</p>
                <p className="text-xs text-faint">{e.quality === "draft" ? "Draft" : "Final"} · <span className="timecode">{timecode(e.duration_seconds, false)}</span> · {relativeTime(e.created_at)}</p>
                <a href={e.download_url} className="text-xs text-uv hover:underline">Download MP4</a>
              </li>
            ))}
          </ul>
        ) : <EmptyState title="No exports yet" body="Rendered videos appear here, ready to download." />
      ) : media.data?.items.length ? (
        <>
          <ul className="grid grid-cols-3 gap-4 sm:grid-cols-5 lg:grid-cols-8">
            {media.data.items.map((m) => (
              <li key={m.id} className="group relative">
                {m.kind === "image" ? (
                  <img src={m.url} alt={m.original_name ?? ""} loading="lazy" className="frame-916 w-full rounded-lg border border-line object-cover" />
                ) : (
                  <div className="grid gap-2 rounded-lg border border-line p-2"><audio src={m.url} controls preload="none" className="w-full" /></div>
                )}
                <p className="mt-1 truncate text-xs text-subtle">{m.original_name ?? label(m.source)}</p>
                <p className="text-[11px] text-faint">{label(m.source)} · {bytes(m.size_bytes)}</p>
                <button type="button" onClick={() => remove.mutate(m.id)} aria-label="Delete file" className="absolute right-1 top-1 rounded bg-ink/80 p-1 text-subtle opacity-0 hover:text-bad focus:opacity-100 group-hover:opacity-100">
                  <Trash2 className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
          {media.data.total > 40 && (
            <div className="mt-6 flex gap-2">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(offset - 40)}>Previous</Button>
              <Button variant="outline" size="sm" disabled={offset + 40 >= media.data.total} onClick={() => setOffset(offset + 40)}>Next</Button>
            </div>
          )}
        </>
      ) : (
        <EmptyState title={kind === "image" ? "No images yet" : "No audio yet"} body={kind === "image" ? "Scene images are saved here as they are generated, with every earlier variant." : "Narration and your uploaded music appear here."} />
      )}
    </Page>
  );
}
