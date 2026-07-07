import type { Platform } from "@/lib/telegram";

export type ImportVia = "v2rayng" | "happ" | "copy";

export interface ClientApp {
  name: string;
  url: string; // store / official download page (always-valid links)
  importVia: ImportVia;
  note?: string;
}

// Store *search* / official links are used where an exact store ID is uncertain,
// so links never break. Deep-link import uses the URLs the backend already returns.
export const APPS: Record<Exclude<Platform, "unknown">, ClientApp[]> = {
  android: [
    {
      name: "Happ",
      url: "https://play.google.com/store/search?q=happ%20proxy&c=apps",
      importVia: "happ",
      note: "Sodda, tavsiya etiladi",
    },
    {
      name: "v2rayNG",
      url: "https://play.google.com/store/apps/details?id=com.v2ray.ang",
      importVia: "v2rayng",
    },
    {
      name: "Hiddify",
      url: "https://play.google.com/store/search?q=hiddify&c=apps",
      importVia: "copy",
    },
  ],
  ios: [
    {
      name: "Happ",
      url: "https://apps.apple.com/search?term=happ%20proxy",
      importVia: "happ",
      note: "iPhone uchun tavsiya",
    },
    {
      name: "Streisand",
      url: "https://apps.apple.com/search?term=streisand",
      importVia: "copy",
    },
    {
      name: "V2Box",
      url: "https://apps.apple.com/search?term=v2box",
      importVia: "copy",
    },
  ],
  macos: [
    {
      name: "Happ",
      url: "https://apps.apple.com/search?term=happ%20proxy",
      importVia: "happ",
    },
    {
      name: "Streisand",
      url: "https://apps.apple.com/search?term=streisand",
      importVia: "copy",
    },
    {
      name: "V2Box",
      url: "https://apps.apple.com/search?term=v2box",
      importVia: "copy",
    },
  ],
  windows: [
    {
      name: "Hiddify",
      url: "https://hiddify.com/",
      importVia: "copy",
      note: "Sodda, tavsiya etiladi",
    },
    {
      name: "v2rayN",
      url: "https://github.com/2dust/v2rayN/releases",
      importVia: "copy",
    },
    {
      name: "Nekoray",
      url: "https://github.com/MatsuriDayo/nekoray/releases",
      importVia: "copy",
    },
  ],
};

export const PLATFORM_LABEL: Record<Platform, string> = {
  android: "Android",
  ios: "iPhone (iOS)",
  macos: "macOS",
  windows: "Windows",
  unknown: "Qurilma",
};
