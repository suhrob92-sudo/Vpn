"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { apiFetch, ApiError } from "@/lib/api";
import { openExternal, getPlatform, type Platform } from "@/lib/telegram";
import { APPS, PLATFORM_LABEL, type ImportVia } from "@/lib/apps";
import { useI18n } from "@/lib/i18n";

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
  const { t } = useI18n();
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
        <div className="h-24 w-24 rounded-full glass-hi flex items-center justify-center text-4xl">🔒</div>
        <h1 className="text-lg font-semibold">{t("no_sub_title")}</h1>
        <p className="text-sm text-muted">{t("no_sub_desc")}</p>
        <Link href="/plans" className="btn-primary max-w-xs">{t("view_plans")}</Link>
      </div>
    );

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      <div className="flex flex-col items-center py-2">
        <div className="relative h-24 w-24 animate-float">
          <span className="ring" />
          <div className="h-24 w-24 rounded-full orb flex items-center justify-center text-3xl shadow-glow">🚀</div>
        </div>
        <h1 className="text-xl font-bold mt-4">{t("connect_title")}</h1>
        <p className="text-xs text-muted mt-1">{t("connect_sub")}</p>
      </div>
      {error && <div className="glass !border-danger/40 text-danger text-sm p-4">{error}</div>}
      {!info && !error && <div className="skeleton h-72" />}

      {info && (
        <>
          <section className="glass p-5">
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-semibold">{t("your_device")}</h2>
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
              {PLATFORM_LABEL[activePlatform]} {t("device_hint")}
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
                    {t("install")}
                  </button>
                  <button
                    className="btn-primary !py-1.5 !px-3 !w-auto text-xs"
                    onClick={() => doImport(app.importVia)}
                  >
                    {app.importVia === "copy" ? t("url_copy") : t("import")}
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="glass p-5">
            <h2 className="font-semibold mb-2">{t("universal_url")}</h2>
            <p className="text-xs text-muted mb-3">{t("universal_desc")}</p>
            <div className="bg-black/40 rounded-xl p-3 text-xs break-all font-mono text-muted">
              {info.subscription_url}
            </div>
            <button className="btn-primary mt-3" onClick={copyUrl}>
              {copied ? t("copied") : t("copy_url")}
            </button>
          </section>

          <section className="glass p-5 flex flex-col items-center">
            <h2 className="font-semibold mb-3 self-start">{t("qr_title")}</h2>
            <div className="bg-white p-3 rounded-xl">
              <QRCodeSVG value={info.subscription_url} size={196} />
            </div>
            <p className="text-xs text-muted mt-2">{t("qr_desc")}</p>
          </section>

          <section className="glass p-5">
            <h2 className="font-semibold mb-3">{t("one_tap")}</h2>
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
            <section className="glass p-4 flex justify-around text-center">
              <div>
                <p className="text-xs text-muted">{t("uploaded")}</p>
                <p className="font-semibold">{formatBytes(info.traffic.up)}</p>
              </div>
              <div>
                <p className="text-xs text-muted">{t("downloaded")}</p>
                <p className="font-semibold">{formatBytes(info.traffic.down)}</p>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
