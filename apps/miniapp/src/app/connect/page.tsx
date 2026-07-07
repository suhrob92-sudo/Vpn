"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { apiFetch, ApiError } from "@/lib/api";
import { openExternal, getPlatform, type Platform } from "@/lib/telegram";
import { APPS, PLATFORM_LABEL, type ImportVia } from "@/lib/apps";

interface ConnectInfo {
  subscription_url: string;
  deep_links: { v2rayng: string; happ: string };
  traffic: { up: number; down: number } | null;
}

const PLATFORMS: Platform[] = ["android", "ios", "windows", "macos"];

function formatBytes(n: number): string {
  if (n <= 0) return "0 MB";
  const gb = n / 1024 ** 3;
  return gb >= 1 ? `${gb.toFixed(2)} GB` : `${(n / 1024 ** 2).toFixed(0)} MB`;
}

export default function Connect() {
  const [info, setInfo] = useState<ConnectInfo | null>(null);
  const [noSub, setNoSub] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [platform, setPlatform] = useState<Platform>("unknown");

  useEffect(() => {
    setPlatform(getPlatform());
    apiFetch<ConnectInfo>("/users/me/connect")
      .then(setInfo)
      .catch((e) => (e instanceof ApiError && e.status === 404 ? setNoSub(true) : setError(e.message)));
  }, []);

  async function copyUrl() {
    if (!info) return;
    await navigator.clipboard.writeText(info.subscription_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function doImport(via: ImportVia) {
    if (!info) return;
    if (via === "v2rayng") openExternal(info.deep_links.v2rayng);
    else if (via === "happ") openExternal(info.deep_links.happ);
    else copyUrl();
  }

  const activePlatform: Platform = platform === "unknown" ? "android" : platform;

  if (noSub)
    return (
      <div className="flex flex-col gap-4 items-center pt-16 text-center">
        <p className="text-4xl">🔒</p>
        <h1 className="text-lg font-semibold">Faol obuna yo'q</h1>
        <p className="text-sm text-muted">VPN'ni ulash uchun avval tarif sotib oling.</p>
        <Link href="/plans" className="btn-primary max-w-xs">
          💎 Tariflarni ko'rish
        </Link>
      </div>
    );

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">🚀 VPN'ni ulash</h1>
      {error && <div className="card border-danger/40 text-danger text-sm">{error}</div>}
      {!info && !error && <div className="skeleton h-72" />}

      {info && (
        <>
          <section className="card">
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-semibold">📱 Sizning qurilmangiz</h2>
              <div className="flex gap-1">
                {PLATFORMS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlatform(p)}
                    className={`text-[11px] px-2 py-1 rounded-lg transition ${
                      activePlatform === p ? "bg-primary text-white" : "bg-white/5 text-muted"
                    }`}
                  >
                    {PLATFORM_LABEL[p]}
                  </button>
                ))}
              </div>
            </div>
            <p className="text-xs text-muted mb-3">
              {PLATFORM_LABEL[activePlatform]} uchun ilovani o'rnating, so'ng «Import» bosing
              (yoki URL'ni nusxalab ilovaga qo'ying).
            </p>
            <div className="flex flex-col gap-2">
              {APPS[activePlatform].map((app) => (
                <div
                  key={app.name}
                  className="flex items-center gap-2 bg-black/30 rounded-xl p-2.5"
                >
                  <div className="flex-1">
                    <p className="font-medium text-sm">
                      {app.name}
                      {app.note && <span className="text-secondary text-[11px] ml-2">{app.note}</span>}
                    </p>
                  </div>
                  <button className="btn-ghost !py-1.5 !px-3 !w-auto text-xs" onClick={() => openExternal(app.url)}>
                    O'rnatish
                  </button>
                  <button
                    className="btn-primary !py-1.5 !px-3 !w-auto text-xs"
                    onClick={() => doImport(app.importVia)}
                  >
                    {app.importVia === "copy" ? "URL nusxa" : "Import"}
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <h2 className="font-semibold mb-2">1. Universal URL</h2>
            <p className="text-xs text-muted mb-3">
              Har qanday kliyentda ishlaydi: Happ, v2rayNG, Streisand, sing-box.
            </p>
            <div className="bg-black/40 rounded-xl p-3 text-xs break-all font-mono text-muted">
              {info.subscription_url}
            </div>
            <button className="btn-primary mt-3" onClick={copyUrl}>
              {copied ? "✓ Nusxalandi" : "📋 URL'ni nusxalash"}
            </button>
          </section>

          <section className="card flex flex-col items-center">
            <h2 className="font-semibold mb-3 self-start">2. QR kod</h2>
            <div className="bg-white p-3 rounded-xl">
              <QRCodeSVG value={info.subscription_url} size={196} />
            </div>
            <p className="text-xs text-muted mt-2">Kliyent ilovasida QR orqali import qiling</p>
          </section>

          <section className="card">
            <h2 className="font-semibold mb-3">3. Bir bosishda ochish</h2>
            <div className="grid grid-cols-2 gap-3">
              <button className="btn-ghost" onClick={() => openExternal(info.deep_links.happ)}>
                Happ
              </button>
              <button className="btn-ghost" onClick={() => openExternal(info.deep_links.v2rayng)}>
                v2rayNG
              </button>
            </div>
          </section>

          {info.traffic && (
            <section className="card flex justify-around text-center">
              <div>
                <p className="text-xs text-muted">⬆️ Yuklangan</p>
                <p className="font-semibold">{formatBytes(info.traffic.up)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">⬇️ Yuklab olingan</p>
                <p className="font-semibold">{formatBytes(info.traffic.down)}</p>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
