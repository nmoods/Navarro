import { zodResolver } from "@hookform/resolvers/zod";
import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { ErrorNotice, Field } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/stores/auth";

export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

export const registerSchema = z.object({
  display_name: z.string().trim().min(1, "Tell us what to call you").max(80),
  email: z.email("Enter a valid email address"),
  password: z
    .string()
    .min(10, "Use at least 10 characters")
    .max(128)
    .refine(
      (v) => [/[a-z]/, /[A-Z]/, /\d/, /[^a-zA-Z0-9]/].filter((r) => r.test(v)).length >= 3,
      "Mix at least three of: lowercase, uppercase, numbers, symbols",
    ),
});

function AuthFrame({ title, children, footer }: { title: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh place-items-center px-4 py-10">
      <div className="beam-glow pointer-events-none fixed inset-0 -z-10 opacity-60" aria-hidden />
      <main id="main" className="w-full max-w-sm">
        <Link to="/" className="mb-10 flex items-center gap-2 font-heading text-lg font-semibold">
          <Clapperboard className="size-5 text-uv" aria-hidden /> NaRRAVO
        </Link>
        <h1 className="text-3xl font-semibold">{title}</h1>
        <div className="mt-8">{children}</div>
        <p className="mt-6 text-sm text-subtle">{footer}</p>
      </main>
    </div>
  );
}

export function LoginPage() {
  const login = useAuth((s) => s.login);
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/app";
  const [error, setError] = useState<unknown>(null);
  const form = useForm<z.infer<typeof loginSchema>>({ resolver: zodResolver(loginSchema) });
  const onSubmit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await login(v.email, v.password);
      navigate(from, { replace: true });
    } catch (e) {
      setError(e);
    }
  });
  const errs = form.formState.errors;
  return (
    <AuthFrame title="Sign in" footer={<>New here? <Link className="text-uv hover:underline" to="/register">Create an account</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {error ? <ErrorNotice error={error} /> : null}
        <Field label="Email" htmlFor="email" error={errs.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errs.email} {...form.register("email")} />
        </Field>
        <Field label="Password" htmlFor="password" error={errs.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errs.password} {...form.register("password")} />
        </Field>
        <Button type="submit" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Signing in…" : "Sign in"}</Button>
      </form>
    </AuthFrame>
  );
}

export function RegisterPage() {
  const register = useAuth((s) => s.register);
  const navigate = useNavigate();
  const [error, setError] = useState<unknown>(null);
  const form = useForm<z.infer<typeof registerSchema>>({ resolver: zodResolver(registerSchema) });
  const onSubmit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await register(v.email, v.password, v.display_name);
      navigate("/create", { replace: true });
    } catch (e) {
      setError(e);
    }
  });
  const errs = form.formState.errors;
  return (
    <AuthFrame title="Create your account" footer={<>Already have one? <Link className="text-uv hover:underline" to="/login">Sign in</Link></>}>
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {error ? <ErrorNotice error={error} /> : null}
        <Field label="Your name" htmlFor="display_name" error={errs.display_name?.message}>
          <Input id="display_name" autoComplete="name" aria-invalid={!!errs.display_name} {...form.register("display_name")} />
        </Field>
        <Field label="Email" htmlFor="email" error={errs.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errs.email} {...form.register("email")} />
        </Field>
        <Field label="Password" htmlFor="password" error={errs.password?.message} hint="At least 10 characters, mixing letters, numbers or symbols.">
          <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!errs.password} {...form.register("password")} />
        </Field>
        <Button type="submit" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? "Creating account…" : "Create account"}</Button>
      </form>
    </AuthFrame>
  );
}
