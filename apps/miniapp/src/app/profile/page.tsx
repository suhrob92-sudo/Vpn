"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getTgUser } from "@/lib/telegram";
import { useI18n, LangSwitch } from "@/lib/i18n";

interface Sub {
  status: string;
  started_at: string;
  expires_at: string;
  plan: { name: string; device_hint: number; traffic_limit_gb: number };
}

export default function Profile() {
  const { t } = useI18n();
  const [sub, setSub] = useState<Sub | null | undefined>(undefined);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [renewing, setRenewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const user = typeof window !== "undefined" ? getTgUser() : null;

  useEffect(() => {
    apiFetch<Sub | null>("/subscriptions/me").then(setSub).catch((e) => setError(e.message));
    apiFetch<{ invite_link: string | null }>("/users/me")
      .then((me) => setInviteLink(me.invite_link))
      .catch(() => {});
  }, []);

  async function copyInvite() {
    if (!inviteLink) return;
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function renew() {
    setRenewing(true);
    setError(null);
    try {
      const payment = await apiFetch<{ invoice_url: string }>("/subscriptions/renew", {
        method: "POST",
      });
      if (payment.invoice_url) window.open(payment.invoice_url, "_blank");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRenewing(false);
    }
  }

  const active = sub && sub.status === "ACTIVE" && new Date(sub.expires_at) > new Date();
  const daysLeft = sub
    ? Math.max(0, Math.ceil((+new Date(sub.expires_at) - Date.now()) / 86400000))
    : 0;

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      <h1 className="text-2xl font-bold tracking-tight">{t("profile_title")}</h1>

      <section className="glass-hi p-5 flex items-center gap-4 relative overflow-hidden">
        <div className="absolute -left-6 -bottom-8 h-28 w-28 rounded-full bg-secondary/25 blur-3xl" />
        <div className="relative h-16 w-16 shrink-0">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-secondary blur-[6px] opacity-70" />
          {user?.photo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.photo_url} alt="" className="relative h-16 w-16 rounded-full object-cover ring-1 ring-white/15" />
          ) : (
            <div className="relative h-16 w-16 rounded-full bg-surface flex items-center justify-center text-2xl font-bold ring-1 ring-white/15">
              {user?.first_name?.[0] ?? "?"}
            </div>
          )}
        </div>
        <div className="relative min-w-0">
          <p className="font-semibold text-lg truncate">
            {user?.first_name} {user?.last_name ?? ""}
          </p>
          {user?.username && <p className="text-sm text-muted">@{user.username}</p>}
          <span className={`chip mt-1 inline-block ${active ? "text-accent bg-accent/10" : "text-muted bg-white/5"}`}>
            {active ? t("premium") : t("free")}
          </span>
        </div>
      </section>

      {/* Language */}
      <section className="glass p-4">
        <p className="text-muted text-[11px] uppercase tracking-wider mb-2">{t("language")}</p>
        <LangSwitch />
      </section>

      {error && <div className="glass !border-danger/40 text-danger text-sm p-4">{error}</div>}
      {sub === undefined && !error && <div className="skeleton h-36" />}

      {sub !== undefined && active && sub && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="glass p-4">
              <p className="text-muted text-[11px]">{t("remaining")}</p>
              <p className="text-2xl font-bold mt-1">
                {daysLeft}
                <span className="text-sm font-medium text-muted"> {t("days")}</span>
              </p>
            </div>
            <div className="glass p-4">
              <p className="text-muted text-[11px]">{t("plan")}</p>
              <p className="text-lg font-semibold mt-1 truncate">{sub.plan.name}</p>
            </div>
            <div className="glass p-4">
              <p className="text-muted text-[11px]">{t("traffic")}</p>
              <p className="text-lg font-semibold mt-1">
                {sub.plan.traffic_limit_gb > 0 ? `${sub.plan.traffic_limit_gb} GB` : t("unlimited")}
              </p>
            </div>
            <div className="glass p-4">
              <p className="text-muted text-[11px]">{t("devices")}</p>
              <p className="text-lg font-semibold mt-1">{sub.plan.device_hint} {t("up_to")}</p>
            </div>
          </div>
          <div className="glass p-4 flex items-center justify-between text-sm">
            <span className="text-muted">{t("valid")}</span>
            <span className="font-medium">
              {new Date(sub.started_at).toLocaleDateString()} — {new Date(sub.expires_at).toLocaleDateString()}
            </span>
          </div>
        </>
      )}
      {sub !== undefined && !active && (
        <div className="glass p-4 text-sm text-muted">{t("no_active_sub")}</div>
      )}

      {inviteLink && (
        <section className="glass p-5">
          <div className="flex items-center gap-2 mb-1">
            <span className="h-8 w-8 rounded-xl bg-primary/15 flex items-center justify-center">🎁</span>
            <h2 className="font-semibold">{t("invite_title")}</h2>
          </div>
          <p className="text-xs text-muted mb-3">{t("invite_desc")}</p>
          <div className="rounded-2xl bg-black/30 border border-white/5 p-3 text-xs break-all font-mono text-muted">
            {inviteLink}
          </div>
          <button className="btn-ghost mt-3" onClick={copyInvite}>
            {copied ? t("copied") : t("copy_link")}
          </button>
        </section>
      )}

      <div className="flex flex-col gap-3">
        {active && (
          <button className="btn-primary" onClick={renew} disabled={renewing}>
            {renewing ? t("renewing") : t("renew")}
          </button>
        )}
        <Link href="/connect" className="btn-ghost">{t("reconnect")}</Link>
        {!active && <Link href="/plans" className="btn-primary">{t("buy_plan")}</Link>}
      </div>
    </div>
  );
}
