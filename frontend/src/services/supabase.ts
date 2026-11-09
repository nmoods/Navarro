// Optional Supabase Auth adapter. Enabled when VITE_AUTH_MODE=supabase. Only the public anon key is used
// in the browser; the backend verifies Supabase JWTs via JWKS and never trusts the client.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

export type AuthAdapter = {
  session: () => Promise<string | null>;
  signIn: (email: string, password: string) => Promise<string>;
  signUp: (email: string, password: string, displayName: string) => Promise<string>;
  signOut: () => Promise<void>;
};

export function supabaseAdapter(): AuthAdapter | null {
  const env = import.meta.env;
  if (env.VITE_AUTH_MODE !== "supabase") return null;
  const url = env.VITE_SUPABASE_URL as string | undefined;
  const anon = env.VITE_SUPABASE_ANON_KEY as string | undefined;
  if (!url || !anon) {
    console.error("VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are required when VITE_AUTH_MODE=supabase");
    return null;
  }
  const client: SupabaseClient = createClient(url, anon, { auth: { persistSession: true, autoRefreshToken: true } });
  const token = (s: { access_token: string } | null) => {
    if (!s) throw new Error("Check your inbox to confirm your email, then sign in.");
    return s.access_token;
  };
  return {
    session: async () => (await client.auth.getSession()).data.session?.access_token ?? null,
    signIn: async (email, password) => {
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (error) throw error;
      return token(data.session);
    },
    signUp: async (email, password, displayName) => {
      const { data, error } = await client.auth.signUp({ email, password, options: { data: { display_name: displayName } } });
      if (error) throw error;
      return token(data.session);
    },
    signOut: async () => {
      await client.auth.signOut();
    },
  };
}
