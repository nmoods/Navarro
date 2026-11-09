import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { JobProgress } from "@/components/JobProgress";
import { LoginPage } from "@/features/auth/AuthPages";
import { useEditor } from "@/features/editor/editorStore";
import { Timeline } from "@/features/editor/Timeline";
import type { Job } from "@/types/api";
import { scene } from "./fixtures";

function wrap(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

const job: Job = {
  id: "job-1", job_type: "production", status: "animation", progress: 62, stage_message: "Rendering scene 3/8", project_id: "p1",
  series_id: null, scene_id: null, parent_job_id: null, error: null, attempts: 1, result: {}, created_at: new Date().toISOString(),
  started_at: null, finished_at: null,
};

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn(async () => new Response(JSON.stringify({ ...job, status: "cancelled" }), { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

describe("JobProgress", () => {
  it("shows the stage, progress and the current step", () => {
    wrap(<JobProgress job={job} />);
    expect(screen.getByText("Rendering scene 3/8")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "62");
    expect(screen.getByText("Animating")).toHaveClass("text-beam");
  });

  it("cancels the job through the API", async () => {
    wrap(<JobProgress job={job} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel job/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/jobs\/job-1\/cancel$/);
    expect(init.method).toBe("POST");
  });

  it("shows the error of a failed job", () => {
    wrap(<JobProgress job={{ ...job, status: "failed", error: "ComfyUI unavailable" }} />);
    expect(screen.getByText("ComfyUI unavailable")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cancel/i })).not.toBeInTheDocument();
  });
});

describe("LoginPage", () => {
  it("validates before calling the API", async () => {
    wrap(<LoginPage />);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the API's error message", async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: "unauthenticated", message: "Invalid email or password" } }), { status: 401 }));
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 401 }));
    wrap(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.co");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });
});

describe("Timeline", () => {
  it("selects a scene when its block is clicked", async () => {
    const scenes = [scene({ title: "Opening", visual_type: "historical_map", transition: "cut" }), scene({ title: "Reveal", visual_type: "kinetic_typography" })];
    wrap(<Timeline scenes={scenes} />);
    await userEvent.click(screen.getByRole("button", { name: /2\. Kinetic typography/ }));
    expect(useEditor.getState().selectedId).toBe(scenes[1].id);
  });
});
