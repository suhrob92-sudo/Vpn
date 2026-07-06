"use client";

// Thin typed access to the Telegram WebApp object injected by telegram-web-app.js
export interface TgUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TgUser; start_param?: string };
  ready: () => void;
  expand: () => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  openTelegramLink: (url: string) => void;
  HapticFeedback?: { notificationOccurred: (t: "error" | "success" | "warning") => void };
  colorScheme: "light" | "dark";
}

export function getTg(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  return (window as any).Telegram?.WebApp ?? null;
}

export function getInitData(): string {
  return getTg()?.initData ?? "";
}

export function getTgUser(): TgUser | null {
  return getTg()?.initDataUnsafe?.user ?? null;
}

export function openExternal(url: string) {
  const tg = getTg();
  if (tg) tg.openLink(url);
  else window.open(url, "_blank");
}
