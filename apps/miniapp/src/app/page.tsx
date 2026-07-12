"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getTg, getTgUser, waitForInitData, type TgUser } from "@/lib/telegram";

interface Sub {
  status: string;
  expires_at: string;
  plan: { name: string; device_hint: number };
}

export default function Home() {
  const [sub, setSub] = useState<Sub | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<TgUser | null>(null);

  useEffect(() => {
    getTg()?.ready();
    getTg()?.expand();
    waitForInitData().then(() => setUser(getTgUser()));
    apiFetch<Sub | null>("/subscriptions/me")
      .then(setSub)
      .catch((e) => setError(e.message));
  }, []);

  const now = new Date();
  const active = sub && sub.status === "ACTIVE" && new Date(sub.expires_at) > now;
  const daysLeft = sub ? Math.max(0, Math.ceil((+new Date(sub.expires_at) - +now) / 86400000)) : 0;

  return (
    <div className="flex flex-col gap-6 animate-fade-up">
      {/* Greeting */}
      <header className="flex items-center gap-3">
        <div className="relative h-12 w-12 shrink-0">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary to-secondary blur-[6px] opacity-70" />
          {user?.photo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.photo_url} alt="" className="relative h-12 w-12 rounded-full object-cover ring-1 ring-white/15" />
          ) : (
            <div className="relative h-12 w-12 rounded-full bg-surface flex items-center justify-center text-lg font-bold ring-1 ring-white/15">
              {user?.first_name?.[0] ?? "🛡"}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-muted text-xs">Xush kelibsiz 👋</p>
          <h1 className="font-semibold text-lg leading-tight truncate">{user?.first_name ?? "Mehmon"}</h1>
        </div>
        <span className={`chip ${active ? "text-accent bg-accent/10" : "text-muted bg-white/5"}`}>
          {active ? "◆ PREMIUM" : "FREE"}
        </span>
      </header>

      {error && <div className="glass !border-danger/40 text-danger text-sm p-4">{error}</div>}

      {/* Subscription card */}
      {sub === undefined && !error ? (
        <div className="skeleton h-28" />
      ) : (
        <section className="glass-hi p-5 relative overflow-hidden">
          <div className="absolute -right-8 -top-10 h-32 w-32 rounded-full bg-primary/30 blur-3xl" />
          <div className="flex items-center justify-between relative">
            <p className="text-muted text-xs uppercase tracking-wider">Obuna</p>
            <span
              className={`chip ${active ? "text-accent bg-accent/10" : "text-danger bg-danger/10"}`}
            >
              {active ? "● FAOL" : sub ? "● TUGAGAN" : "● YO'Q"}
            </span>
          </div>
          {active && sub ? (
            <div className="mt-4 flex items-end justify-between relative">
              <div>
                <p className="text-3xl font-bold leading-none">
                  {daysLeft}
                  <span className="text-base font-medium text-muted"> kun</span>
                </p>
                <p className="text-xs text-muted mt-1">{sub.plan.name}</p>
              </div>
              <p className="text-xs text-muted text-right">
                {new Date(sub.expires_at).toLocaleDateString("uz-UZ")}
                <br />
                gacha
              </p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted relative">
              Faol obuna yo'q — tarif tanlab VPN'ni bir daqiqada ulang.
            </p>
          )}
        </section>
      )}

      {/* The giant connect / buy orb */}
      <section className="flex flex-col items-center py-4">
        <Link href={active ? "/connect" : "/plans"} className="relative active:scale-95 transition">
          <span className="ring" />
          <span className="ring ring-2" />
          <div
            className={`h-44 w-44 rounded-full flex flex-col items-center justify-center text-center animate-float ${
              active ? "orb" : "orb-idle"
            }`}
          >
            <span className="text-4xl mb-1">{active ? "🚀" : "💎"}</span>
            <span className="font-bold text-lg leading-tight text-white drop-shadow">
              {active ? "VPN'ni" : "Tarif"}
              <br />
              {active ? "ulash" : "olish"}
            </span>
          </div>
        </Link>
        <p className="text-muted text-xs mt-5">
          {active ? "Ulanish uchun bosing" : "Boshlash uchun tarif tanlang"}
        </p>
      </section>

      {/* Quick stat cards */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass p-4">
          <p className="text-muted text-[11px]">Tarmoq sifati</p>
          <p className="font-semibold mt-1 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-accent shadow-glow-accent" />
            {active ? "A'lo" : "—"}
          </p>
        </div>
        <div className="glass p-4">
          <p className="text-muted text-[11px]">Qurilmalar</p>
          <p className="font-semibold mt-1">{active && sub ? `${sub.plan.device_hint} tagacha` : "—"}</p>
        </div>
      </div>

      <Link href="/servers" className="glass p-4 flex items-center justify-between active:scale-[0.99] transition">
        <div className="flex items-center gap-3">
          <span className="h-9 w-9 rounded-xl bg-secondary/15 flex items-center justify-center text-secondary">🌍</span>
          <div>
            <p className="text-sm font-medium">Server lokatsiyalari</p>
            <p className="text-xs text-muted">Barcha serverlarni ko'rish</p>
          </div>
        </div>
        <span className="text-muted">›</span>
      </Link>
    </div>
  );
}
