// Typed fetch wrapper for the FastAPI backend (base URL, auth header, error mapping).
import type { ApiErrorBody } from "@/types/api";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");
export type AccessTokenProvider = () => string | null | Promise<string | null>;
let accessTokenProvider: AccessTokenProvider | undefined;
export function setAccessTokenProvider(provider: AccessTokenProvider): void {
  accessTokenProvider = provider;
}

function storedAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const session = JSON.parse(
      window.localStorage.getItem("rentflow.session") ?? "null",
    ) as { access_token?: unknown } | null;
    return typeof session?.access_token === "string"
      ? session.access_token
      : null;
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly fieldErrors: Record<string, string>;
  constructor(status: number, body: ApiErrorBody) {
    super(body.detail);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.fieldErrors = body.field_errors ?? {};
  }
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as ApiErrorBody).detail === "string"
  );
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const providedToken = headers.has("Authorization")
    ? null
    : await accessTokenProvider?.();
  const token = providedToken ?? storedAccessToken();
  headers.set("Accept", "application/json");
  if (init.body != null && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");
  if (token && !headers.has("Authorization"))
    headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}/${path.replace(/^\//, "")}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(
      response.status,
      isErrorBody(body)
        ? body
        : { detail: response.statusText || "Request failed" },
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function post<TResponse, TBody>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  return apiFetch<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function get<TResponse>(
  path: string,
  params?: object,
): Promise<TResponse> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined) query.set(key, String(value));
  }
  const encoded = query.toString();
  const suffix = encoded ? `${path.includes("?") ? "&" : "?"}${encoded}` : "";
  return apiFetch<TResponse>(`${path}${suffix}`);
}

export function patch<TResponse, TBody>(
  path: string,
  body: TBody,
): Promise<TResponse> {
  return apiFetch<TResponse>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function del<TResponse = void>(path: string): Promise<TResponse> {
  return apiFetch<TResponse>(path, { method: "DELETE" });
}
