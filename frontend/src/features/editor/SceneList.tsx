import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GripVertical, Plus } from "lucide-react";
import { Reorder } from "motion/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { keys } from "@/hooks/queries";
import { label } from "@/lib/format";
import { cn } from "@/lib/utils";
import { scenesApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import type { Scene } from "@/types/api";
import { useEditor } from "./editorStore";

export function SceneList({ scenes, projectId }: { scenes: Scene[]; projectId: string }) {
  const qc = useQueryClient();
  const { selectedId, select } = useEditor();
  const [order, setOrder] = useState(scenes);
  useEffect(() => setOrder(scenes), [scenes]);

  const reorder = useMutation({
    mutationFn: (ids: string[]) => scenesApi.reorder(projectId, ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.storyboard(projectId) }),
    onError: (e) => { setOrder(scenes); toast.error(errorMessage(e)); },
  });
  const add = useMutation({
    mutationFn: () => scenesApi.add(projectId, { narration: "Write what the narrator says in this scene.", title: "New scene" }),
    onSuccess: (scene) => { qc.invalidateQueries({ queryKey: keys.storyboard(projectId) }); select(scene.id); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const commit = () => {
    const ids = order.map((s) => s.id);
    if (ids.join() !== scenes.map((s) => s.id).join()) reorder.mutate(ids);
  };

  return (
    <div className="p-2">
      <Reorder.Group axis="y" values={order} onReorder={setOrder} className="grid gap-1">
        {order.map((scene, i) => (
          <Reorder.Item key={scene.id} value={scene} onDragEnd={commit} className="list-none">
            <div
              role="button"
              tabIndex={0}
              onClick={() => select(scene.id)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && select(scene.id)}
              aria-current={selectedId === scene.id}
              className={cn(
                "group grid cursor-pointer grid-cols-[14px_40px_1fr] items-center gap-2 rounded-md p-1.5 text-left",
                selectedId === scene.id ? "bg-raised shadow-[inset_2px_0_0_var(--color-uv)]" : "hover:bg-raised/60",
              )}
            >
              <GripVertical className="size-3.5 cursor-grab text-faint opacity-0 group-hover:opacity-100" aria-label="Drag to reorder" />
              <div className="h-[71px] w-10 overflow-hidden rounded border border-line bg-ink">
                {scene.image ? <img src={scene.image.url} alt="" className="size-full object-cover" /> : <span className="flex size-full items-center justify-center text-[9px] text-faint">{label(scene.visual_type).split(" ")[0]}</span>}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm"><span className="timecode mr-1.5 text-xs">{String(i + 1).padStart(2, "0")}</span>{scene.title}</p>
                <p className="line-clamp-2 text-xs text-faint">{scene.narration}</p>
              </div>
            </div>
          </Reorder.Item>
        ))}
      </Reorder.Group>
      <Button variant="ghost" size="sm" className="mt-2 w-full justify-start text-subtle" onClick={() => add.mutate()} disabled={add.isPending}>
        <Plus className="size-4" /> Add scene
      </Button>
    </div>
  );
}
