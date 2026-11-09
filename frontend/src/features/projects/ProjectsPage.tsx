import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Trash2 } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { EmptyState, ErrorNotice, PageHeader } from "@/components/common";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectTile } from "@/features/dashboard/DashboardPage";
import { keys } from "@/hooks/queries";
import { PROJECT_STATUS_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import { projectsApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";

const PAGE = 24;

export default function ProjectsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const query = useDeferredValue(q);
  const params = { q: query, status, limit: PAGE, offset };
  const { data, isLoading, error } = useQuery({ queryKey: keys.projects(params), queryFn: () => projectsApi.list(params) });
  const remove = useMutation({
    mutationFn: projectsApi.remove,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["projects"] }); toast("Project deleted"); },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Page wide>
      <PageHeader title="Projects" description="Every video you have started, with its storyboard, versions and exports." actions={<Button asChild><Link to="/create"><Plus className="size-4" /> New video</Link></Button>} />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-2.5 size-4 text-faint" aria-hidden />
          <Input className="pl-8" placeholder="Search titles and topics" value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} aria-label="Search projects" />
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
          {["", "storyboard_ready", "ready", "producing", "failed"].map((s) => (
            <button key={s} type="button" aria-pressed={status === s} onClick={() => { setStatus(s); setOffset(0); }}
              className={cn("rounded-md border px-2.5 py-1 text-xs", status === s ? "border-uv text-text" : "border-line text-subtle hover:text-text")}>
              {s ? PROJECT_STATUS_LABEL[s] : "All"}
            </button>
          ))}
        </div>
      </div>
      {error ? <ErrorNotice error={error} /> : null}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="frame-916 w-full" />)}</div>
      ) : data?.items.length ? (
        <>
          <ul className="grid grid-cols-2 gap-x-5 gap-y-8 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8">
            {data.items.map((p) => (
              <li key={p.id} className="group relative">
                <ProjectTile project={p} />
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <button type="button" aria-label={`Delete ${p.title}`} className="absolute right-1.5 top-1.5 rounded bg-ink/80 p-1.5 text-subtle opacity-0 hover:text-bad focus:opacity-100 group-hover:opacity-100">
                      <Trash2 className="size-3.5" />
                    </button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogTitle>Delete “{p.title}”?</AlertDialogTitle>
                    <AlertDialogDescription>The storyboard, scenes and exports of this project are deleted. Running jobs are cancelled.</AlertDialogDescription>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Keep project</AlertDialogCancel>
                      <AlertDialogAction onClick={() => remove.mutate(p.id)} className="bg-bad text-ink hover:bg-bad/90">Delete project</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </li>
            ))}
          </ul>
          {data.total > PAGE && (
            <div className="mt-8 flex items-center gap-3 text-sm text-subtle">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(offset - PAGE)}>Previous</Button>
              {offset + 1}–{Math.min(offset + PAGE, data.total)} of {data.total}
              <Button variant="outline" size="sm" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Next</Button>
            </div>
          )}
        </>
      ) : (
        <EmptyState title={q || status ? "No matching projects" : "No projects yet"} body={q || status ? "Try a different search or filter." : "Create a video from a single sentence."} action={!q && !status ? <Button asChild><Link to="/create">New video</Link></Button> : undefined} />
      )}
    </Page>
  );
}
