// Session handling against Azure Entra ID / backend JWT.
import { apiFetch, post, setAccessTokenProvider } from "@/lib/api/client";
import type { LoginRequest, RegisterRequest, TokenPair, User } from "@/types/api";

const SESSION_KEY = "rentflow.session";
const SESSION_COOKIE = "rentflow_session";
const SESSION_EVENT = "rentflow:session";

function tokenExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const unpadded = payload.replace(/-/g, "+").replace(/_/g, "/");
    const normalized = unpadded.padEnd(Math.ceil(unpadded.length / 4) * 4, "=");
    const decoded = JSON.parse(window.atob(normalized)) as { exp?: unknown };
    return typeof decoded.exp === "number" ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
}

function syncSessionCookie(tokens: TokenPair): void {
  const expiresAt = tokenExpiry(tokens.refresh_token);
  const maxAge = expiresAt ? Math.max(0, Math.floor((expiresAt - Date.now()) / 1000)) : 0;
  document.cookie = `${SESSION_COOKIE}=${expiresAt ?? ""}; Path=/; SameSite=Lax; Max-Age=${maxAge}`;
}
export function getSession(): TokenPair | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(SESSION_KEY);
    return value ? (JSON.parse(value) as TokenPair) : null;
  } catch {
    window.localStorage.removeItem(SESSION_KEY); return null;
  }
}
export function saveSession(tokens: TokenPair): void {
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(tokens));
  syncSessionCookie(tokens);
  window.dispatchEvent(new Event(SESSION_EVENT));
}
export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(SESSION_KEY);
  document.cookie = `${SESSION_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0`;
  window.dispatchEvent(new Event(SESSION_EVENT));
}

let refreshPromise: Promise<TokenPair> | null = null;
export async function refreshSession(): Promise<TokenPair | null> {
  const session = getSession();
  if (!session) return null;
  if (!refreshPromise) {
    refreshPromise = apiFetch<TokenPair>("/auth/refresh", {
      method: "POST",
      headers: { Authorization: "" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    }).then((tokens) => { saveSession(tokens); return tokens; })
      .catch(() => { clearSession(); throw new Error("Your session has expired. Please log in again."); })
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

export async function getValidAccessToken(): Promise<string | null> {
  const session = getSession();
  if (!session) return null;
  const expiresAt = tokenExpiry(session.access_token);
  if (expiresAt && expiresAt > Date.now() + 30_000) return session.access_token;
  return (await refreshSession())?.access_token ?? null;
}

export const sessionEventName = SESSION_EVENT;
setAccessTokenProvider(getValidAccessToken);

export async function login(credentials: LoginRequest): Promise<TokenPair> {
  const tokens = await post<TokenPair, LoginRequest>("/auth/login", credentials);
  saveSession(tokens); return tokens;
}
export function register(details: RegisterRequest): Promise<User> {
  return post<User, RegisterRequest>("/auth/register", { role: "landlord", ...details });
}
