import { create } from "zustand";
import { authApi } from "@/services/endpoints";
import { configureAuth } from "@/services/http";
import type { User } from "@/types/api";

type Status = "unknown" | "authenticated" | "anonymous";

type AuthState = {
  user: User | null;
  token: string | null;
  status: Status;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
};

// supabase-js is only downloaded when Supabase auth is configured.
const supabaseReady = import.meta.env.VITE_AUTH_MODE === "supabase"
  ? import("@/services/supabase").then((m) => m.supabaseAdapter())
  : Promise.resolve(null);

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: null,
  status: "unknown",

  bootstrap: async () => {
    try {
    const supabase = await supabaseReady;
      const token = supabase ? await supabase.session() : (await authApi.refresh()).access_token;
      if (!token) throw new Error("no session");
      set({ token });
      set({ user: await authApi.me(), status: "authenticated" });
    } catch {
      set({ user: null, token: null, status: "anonymous" });
    }
  },

  login: async (email, password) => {
    const supabase = await supabaseReady;
    const token = supabase ? await supabase.signIn(email, password) : (await authApi.login({ email, password })).access_token;
    set({ token });
    set({ user: await authApi.me(), status: "authenticated" });
  },

  register: async (email, password, displayName) => {
    const supabase = await supabaseReady;
    const token = supabase
      ? await supabase.signUp(email, password, displayName)
      : (await authApi.register({ email, password, display_name: displayName })).access_token;
    set({ token });
    set({ user: await authApi.me(), status: "authenticated" });
  },

  logout: async () => {
    const supabase = await supabaseReady;
    try {
      if (supabase) await supabase.signOut();
      else await authApi.logout();
    } finally {
      set({ user: null, token: null, status: "anonymous" });
    }
  },

  setUser: (user) => set({ user }),
}));

configureAuth({
  getToken: () => useAuth.getState().token,
  refresh: async () => {
    const supabase = await supabaseReady;
    try {
      const token = supabase ? await supabase.session() : (await authApi.refresh()).access_token;
      useAuth.setState({ token });
      return token;
    } catch {
      return null;
    }
  },
  onUnauthenticated: () => useAuth.setState({ user: null, token: null, status: "anonymous" }),
});
