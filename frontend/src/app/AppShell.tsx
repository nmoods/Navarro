import { CalendarDays, Clapperboard, Dna, Film, FolderOpen, Images, LayoutGrid, LogOut, Menu, Mic, Plus, Settings } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { useAuth } from "@/stores/auth";

const NAV = [
  { group: "Studio", items: [
    { to: "/app", label: "Dashboard", icon: LayoutGrid, end: true },
    { to: "/projects", label: "Projects", icon: FolderOpen },
    { to: "/series", label: "Series Factory", icon: Film },
    { to: "/planner", label: "Content planner", icon: CalendarDays },
  ] },
  { group: "Identity", items: [
    { to: "/story-dna", label: "Story DNA", icon: Dna },
    { to: "/voices", label: "Voice studio", icon: Mic },
    { to: "/media", label: "Media library", icon: Images },
  ] },
] as const;

function Wordmark() {
  return (
    <span className="flex items-center gap-2 font-heading text-lg font-semibold tracking-tight">
      <Clapperboard className="size-5 text-uv" aria-hidden />
      NaRRAVO
    </span>
  );
}

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <Wordmark />
      <Button className="justify-start gap-2" onClick={() => { navigate("/create"); onNavigate?.(); }}>
        <Plus className="size-4" /> New video
      </Button>
      <nav className="grid gap-5" aria-label="Main">
        {NAV.map((section) => (
          <div key={section.group} className="grid gap-0.5">
            <p className="px-2 pb-1 text-xs text-faint">{section.group}</p>
            {section.items.map(({ to, label, icon: Icon, ...rest }) => (
              <NavLink
                key={to}
                to={to}
                end={"end" in rest}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-subtle hover:bg-raised hover:text-text",
                    isActive && "bg-raised text-text shadow-[inset_2px_0_0_var(--color-uv)]",
                  )
                }
              >
                <Icon className="size-4" aria-hidden />
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="mt-auto grid gap-0.5 border-t border-line pt-4">
        <NavLink to="/settings" onClick={onNavigate} className={({ isActive }) => cn("flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-subtle hover:bg-raised hover:text-text", isActive && "bg-raised text-text")}>
          <Settings className="size-4" aria-hidden /> Settings
        </NavLink>
        <button
          type="button"
          onClick={async () => { await logout(); navigate("/"); }}
          className="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-sm text-subtle hover:bg-raised hover:text-text"
        >
          <LogOut className="size-4" aria-hidden /> Sign out
        </button>
        <p className="truncate px-2 pt-2 text-xs text-faint">{user?.email}</p>
      </div>
    </div>
  );
}

export function AppShell() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="sticky top-0 hidden h-dvh border-r border-line bg-surface/60 lg:block">
        <NavContent />
      </aside>
      <div className="flex items-center justify-between border-b border-line px-4 py-3 lg:hidden">
        <Wordmark />
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Open navigation"><Menu className="size-5" /></Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 border-line bg-surface p-0">
            <SheetTitle className="sr-only">Navigation</SheetTitle>
            <NavContent onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>
      </div>
      <main id="main" className="min-w-0">
        <Outlet />
      </main>
    </div>
  );
}

export function Page({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return <div className={cn("mx-auto px-4 py-8 md:px-8 md:py-10", wide ? "max-w-[1600px]" : "max-w-6xl")}>{children}</div>;
}
