import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate, useLocation } from "react-router-dom";
import { AppShell } from "@/app/AppShell";
import { useAuth } from "@/stores/auth";

const Landing = lazy(() => import("@/features/landing/LandingPage"));
const Login = lazy(() => import("@/features/auth/AuthPages").then((m) => ({ default: m.LoginPage })));
const Register = lazy(() => import("@/features/auth/AuthPages").then((m) => ({ default: m.RegisterPage })));
const Dashboard = lazy(() => import("@/features/dashboard/DashboardPage"));
const Create = lazy(() => import("@/features/video-generator/CreateVideoPage"));
const Editor = lazy(() => import("@/features/editor/EditorPage"));
const Projects = lazy(() => import("@/features/projects/ProjectsPage"));
const Series = lazy(() => import("@/features/series/SeriesPage"));
const SeriesDetail = lazy(() => import("@/features/series/SeriesDetailPage"));
const Planner = lazy(() => import("@/features/content-planner/PlannerPage"));
const Media = lazy(() => import("@/features/media/MediaPage"));
const Voices = lazy(() => import("@/features/voice-studio/VoiceStudioPage"));
const StoryDna = lazy(() => import("@/features/story-dna/StoryDnaPage"));
const Settings = lazy(() => import("@/features/settings/SettingsPage"));

function Loading() {
  return <div className="flex min-h-[50dvh] items-center justify-center text-sm text-faint">Loading…</div>;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuth((s) => s.status);
  const location = useLocation();
  if (status === "unknown") return <Loading />;
  if (status === "anonymous") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

const s = (node: ReactNode) => <Suspense fallback={<Loading />}>{node}</Suspense>;

export const router = createBrowserRouter([
  { path: "/", element: s(<Landing />) },
  { path: "/login", element: s(<Login />) },
  { path: "/register", element: s(<Register />) },
  {
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { path: "/app", element: s(<Dashboard />) },
      { path: "/create", element: s(<Create />) },
      { path: "/projects", element: s(<Projects />) },
      { path: "/projects/:projectId", element: s(<Editor />) },
      { path: "/series", element: s(<Series />) },
      { path: "/series/:seriesId", element: s(<SeriesDetail />) },
      { path: "/planner", element: s(<Planner />) },
      { path: "/media", element: s(<Media />) },
      { path: "/voices", element: s(<Voices />) },
      { path: "/story-dna", element: s(<StoryDna />) },
      { path: "/settings", element: s(<Settings />) },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
