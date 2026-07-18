"use client";

/**
 * Browser API client. Reads the bearer token from localStorage (dev-login) or
 * falls back to the NextAuth session token injected on the window. Public
 * endpoints work without a token.
 */
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const TOKEN_KEY = "srx_token";
export const ROLE_KEY = "srx_role";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getRole(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ROLE_KEY);
}

export function setSession(token: string, role: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(ROLE_KEY, role);
}

export function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(ROLE_KEY);
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function devLogin(role: string): Promise<{ access_token: string; role: string }> {
  return api("/api/v1/auth/dev-login", {
    method: "POST",
    body: JSON.stringify({ role }),
  });
}
