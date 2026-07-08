"use client";

import { waitForInitData } from "@/lib/telegram";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let accessToken: string | null = null;
let authPromise: Promise<void> | null = null;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function authenticate(): Promise<void> {
  const initData = await waitForInitData();
  if (!initData) throw new ApiError(401, "Telegram initData mavjud emas — Mini App'ni Telegram ichida oching");
  const resp = await fetch(`${API}/auth/telegram`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });
  const body = await resp.json();
  if (!resp.ok || !body.success) throw new ApiError(resp.status, body?.error?.message || "Auth failed");
  accessToken = body.data.access_token;
}

async function ensureAuth(): Promise<void> {
  if (accessToken) return;
  authPromise = authPromise ?? authenticate();
  try {
    await authPromise;
  } finally {
    authPromise = null;
  }
}

export async function apiFetch<T = any>(path: string, init?: RequestInit, retry = true): Promise<T> {
  await ensureAuth();
  const resp = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${accessToken}`,
      ...(init?.headers || {}),
    },
  });
  if (resp.status === 401 && retry) {
    accessToken = null; // expired JWT — re-auth once with fresh initData
    return apiFetch<T>(path, init, false);
  }
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok || body.success === false) {
    throw new ApiError(resp.status, body?.error?.message || `HTTP ${resp.status}`);
  }
  return body.data as T;
}

// Public endpoints (no auth needed)
export async function apiPublic<T = any>(path: string): Promise<T> {
  const resp = await fetch(`${API}${path}`);
  const body = await resp.json();
  if (!resp.ok || body.success === false) {
    throw new ApiError(resp.status, body?.error?.message || `HTTP ${resp.status}`);
  }
  return body.data as T;
}
