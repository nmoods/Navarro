import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, FlaskConical } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Page } from "@/app/AppShell";
import { ErrorNotice, Field, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { keys, useProviders } from "@/hooks/queries";
import { accountApi, creativeApi } from "@/services/endpoints";
import { errorMessage } from "@/services/http";
import { useAuth } from "@/stores/auth";

const KIND_LABEL: Record<string, string> = { llm: "Story Director", image: "Images", tts: "Voice", stt: "Caption timing", research: "Fact checking" };

export default function SettingsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuth();
  const providers = useProviders();
  const dna = useQuery({ queryKey: keys.dna, queryFn: creativeApi.dna });
  const [name, setName] = useState(user?.display_name ?? "");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [confirm, setConfirm] = useState("");

  const profile = useMutation({ mutationFn: accountApi.updateProfile, onSuccess: (u) => { setUser(u); toast("Profile updated"); }, onError: (e) => toast.error(errorMessage(e)) });
  const password = useMutation({ mutationFn: () => accountApi.changePassword(pw), onSuccess: () => { setPw({ current_password: "", new_password: "" }); toast("Password changed"); } });
  const remove = useMutation({ mutationFn: () => accountApi.deleteAccount(confirm), onSuccess: async () => { await logout(); navigate("/"); } });

  return (
    <Page>
      <PageHeader title="Settings" />
      <div className="grid gap-12">
        <section id="ai" className="grid gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">AI services</h2>
            <Button size="sm" variant="ghost" onClick={() => qc.invalidateQueries({ queryKey: keys.providers })}>Check again</Button>
          </div>
          <p className="-mt-2 text-sm text-subtle">All models run locally. Start them with <code className="rounded bg-raised px-1">infrastructure/scripts/start-ai</code>; see the installation guide.</p>
          <ul className="divide-y divide-line rounded-xl border border-line">
            {(providers.data ?? []).map((p) => (
              <li key={`${p.kind}-${p.name}`} className="flex items-start gap-3 p-4">
                {p.is_test_double ? <FlaskConical className="mt-0.5 size-4 text-warn" /> : p.available ? <CheckCircle2 className="mt-0.5 size-4 text-ok" /> : <CircleAlert className="mt-0.5 size-4 text-bad" />}
                <div className="min-w-0">
                  <p className="text-sm font-medium">{KIND_LABEL[p.kind] ?? p.kind} <span className="font-normal text-faint">· {p.name}</span></p>
                  <p className="text-sm text-subtle">{p.detail}</p>
                </div>
              </li>
            ))}
          </ul>
          {providers.error ? <ErrorNotice error={providers.error} /> : null}
        </section>

        <section className="grid max-w-lg gap-4">
          <h2 className="text-lg font-semibold">Profile</h2>
          <Field label="Display name" htmlFor="name"><Input id="name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} /></Field>
          <Field label="Default Story DNA" htmlFor="default-dna" hint="Used for ideas you turn into videos from the planner.">
            <Select value={user?.default_story_dna_id ?? "none"} onValueChange={(v) => profile.mutate({ default_story_dna_id: v === "none" ? null : v })}>
              <SelectTrigger id="default-dna" className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                {(dna.data ?? []).map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Button className="justify-self-start" onClick={() => profile.mutate({ display_name: name.trim() })} disabled={!name.trim()}>Save profile</Button>
        </section>

        {user?.auth_provider === "local" && (
          <form className="grid max-w-lg gap-4" onSubmit={(e) => { e.preventDefault(); password.mutate(); }}>
            <h2 className="text-lg font-semibold">Password</h2>
            <Field label="Current password" htmlFor="cur"><Input id="cur" type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
            <Field label="New password" htmlFor="new" hint="At least 10 characters, mixing letters, numbers or symbols."><Input id="new" type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field>
            {password.error ? <ErrorNotice error={password.error} /> : null}
            <Button type="submit" className="justify-self-start" disabled={!pw.current_password || pw.new_password.length < 10}>Change password</Button>
          </form>
        )}

        <section className="grid max-w-lg gap-3 rounded-xl border border-bad/30 p-5">
          <h2 className="text-lg font-semibold text-bad">Delete account</h2>
          <p className="text-sm text-subtle">Permanently deletes your account, every project and every generated or uploaded file. This cannot be undone.</p>
          <Field label={`Type ${user?.email} to confirm`} htmlFor="confirm"><Input id="confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></Field>
          {remove.error ? <ErrorNotice error={remove.error} /> : null}
          <Button variant="destructive" className="justify-self-start" disabled={confirm !== user?.email || remove.isPending} onClick={() => remove.mutate()}>Delete my account</Button>
        </section>
      </div>
    </Page>
  );
}
