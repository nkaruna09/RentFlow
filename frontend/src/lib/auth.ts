// Session handling against Azure Entra ID / backend JWT.
import { post, setAccessTokenProvider } from "@/lib/api/client";
import type { LoginRequest, RegisterRequest, TokenPair, User } from "@/types/api";

const SESSION_KEY = "rentflow.session";
export function getSession(): TokenPair | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(SESSION_KEY);
    return value ? (JSON.parse(value) as TokenPair) : null;
  } catch {
    window.localStorage.removeItem(SESSION_KEY); return null;
  }
}
export function saveSession(tokens: TokenPair): void { window.localStorage.setItem(SESSION_KEY, JSON.stringify(tokens)); }
export function clearSession(): void { if (typeof window !== "undefined") window.localStorage.removeItem(SESSION_KEY); }
setAccessTokenProvider(() => getSession()?.access_token ?? null);

export async function login(credentials: LoginRequest): Promise<TokenPair> {
  const tokens = await post<TokenPair, LoginRequest>("/auth/login", credentials);
  saveSession(tokens); return tokens;
}
export function register(details: RegisterRequest): Promise<User> {
  return post<User, RegisterRequest>("/auth/register", { role: "landlord", ...details });
}
