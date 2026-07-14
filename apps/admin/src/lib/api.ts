"use client";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function getTokens() {
  if (typeof window === "undefined") return { access: null, refresh: null };
  return {
    access: sessionStorage.getItem("admin_access"),
    refresh: sessionStorage.getItem("admin_refresh"),
  };
}

export function setTokens(access: string, refresh: string) {
  sessionStorage.setItem("admin_access", access);
  sessionStorage.setItem("admin_refresh", refresh);
}

export function clearTokens() {
  sessionStorage.removeItem("admin_access");
  sessionStorage.removeItem("admin_refresh");
}

export function isLoggedIn(): boolean {
  return !!getTokens().access;
}

export async function login(username: string, password: string): Promise<void> {
  const resp = await fetch(`${API}/admin/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await resp.json();
  if (!resp.ok || !body.success) throw new ApiError(resp.status, body?.error?.message || "Login failed");
  setTokens(body.data.access_token, body.data.refresh_token);
}

async function refreshTokens(): Promise<boolean> {
  const { refresh } = getTokens();
  if (!refresh) return false;
  const resp = await fetch(`${API}/admin/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) {
    clearTokens();
    return false;
  }
  const body = await resp.json();
  setTokens(body.data.access_token, body.data.refresh_token);
  return true;
}

export async function adminFetch<T = any>(path: string, init?: RequestInit, retry = true): Promise<T> {
  const { access } = getTokens();
  const resp = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(access ? { authorization: `Bearer ${access}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (resp.status === 401 && retry && (await refreshTokens())) {
    return adminFetch<T>(path, init, false);
  }
  if (resp.status === 401) {
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/admin/login";
    throw new ApiError(401, "Session expired");
  }
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok || body.success === false) {
    throw new ApiError(resp.status, body?.error?.message || `HTTP ${resp.status}`);
  }
  return body.data as T;
}
