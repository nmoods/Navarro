// Minimal typed HTTP client. Access tokens live in memory only (never localStorage);
// the refresh token is an httpOnly cookie handled by the browser.

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "http://127.0.0.1:8010";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type TokenSource = {
  getToken: () => string | null;
  refresh: () => Promise<string | null>;
  onUnauthenticated: () => void;
};

let tokens: TokenSource = { getToken: () => null, refresh: async () => null, onUnauthenticated: () => {} };

export function configureAuth(source: TokenSource) {
  tokens = source;
}

let refreshing: Promise<string | null> | null = null;

function refreshOnce(): Promise<string | null> {
  refreshing ??= tokens.refresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

export type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
  signal?: AbortSignal;
  auth?: boolean;
};

async function toError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json();
    const err = data?.error ?? {};
    return new ApiError(res.status, err.code ?? "error", err.message ?? res.statusText, err.details ?? {});
  } catch {
    return new ApiError(res.status, "error", res.statusText || "Request failed");
  }
}

async function send(path: string, opts: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { "X-Requested-With": "narravo" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  return fetch(`${API_URL}/api/v1${path}`, {
    method: opts.method ?? "GET",
    headers,
    body,
    signal: opts.signal,
    credentials: "include",
  });
}

export async function raw(path: string, opts: RequestOptions = {}): Promise<Response> {
  const useAuth = opts.auth !== false;
  let res = await send(path, opts, useAuth ? tokens.getToken() : null);
  if (res.status === 401 && useAuth) {
    const fresh = await refreshOnce();
    if (!fresh) {
      tokens.onUnauthenticated();
      throw await toError(res);
    }
    res = await send(path, opts, fresh);
  }
  if (!res.ok) throw await toError(res);
  return res;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await raw(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Fetch an authenticated binary (e.g. voice/music previews) and return an object URL. */
export async function blobUrl(path: string, opts: RequestOptions = {}): Promise<string> {
  const res = await raw(path, opts);
  return URL.createObjectURL(await res.blob());
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "Can't reach the NaRRAVO API. Check that the backend is running.";
  return error instanceof Error ? error.message : "Something went wrong";
}
