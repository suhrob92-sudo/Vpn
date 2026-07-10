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
    // telegram-web-app.js may fill user data slightly after mount — re-read once ready.
    waitForInitData().then(() => setUser(getTgUser()));
    apiFetch<Sub | null>("/subscriptions/me")
      .then(setSub)
      .catch((e) => setError(e.message));
  }, []);

  const now = new Date();
  const active = sub && sub.status === "ACTIVE" && new Date(sub.expires_at) > now;
  const daysLeft = sub ? Math.max(0, Math.ceil((+new Date(sub.expires_at) - +now) / 86400000)) : 0;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex items-center gap-3">
        <div className="h-11 w-11 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-lg font-bold">
          {user?.first_name?.[0] ?? "🛡"}
        </div>
        <div>
          <p className="text-muted text-sm">Xush kelibsiz</p>
          <h1 className="font-semibold text-lg leading-tight">{user?.first_name ?? "Mehmon"}</h1>
        </div>
      </header>

      {error && <div className="card border-danger/40 text-danger text-sm">{error}</div>}

      {sub === undefined && !error ? (
        <div className="skeleton h-28" />
      ) : (
        <section className="card">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Obuna</h2>
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                active ? "bg-success/15 text-success" : "bg-danger/15 text-danger"
              }`}
            >
              {active ? "● FAOL" : sub ? "● TUGAGAN" : "● YO'Q"}
            </span>
          </div>
          {active && sub ? (
            <div className="mt-3 text-sm text-muted space-y-1">
              <p>
                Tarif: <span className="text-txt font-medium">{sub.plan.name}</span>
              </p>
              <p>
                Qolgan: <span className="text-txt font-medium">{daysLeft} kun</span> (
                {new Date(sub.expires_at).toLocaleDateString("uz-UZ")} gacha)
              </p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted">
              Faol obuna yo'q — tarif tanlab VPN'ni bir daqiqada ulang.
            </p>
          )}
        </section>
      )}

      <section className="flex flex-col items-center py-6">
        {active ? (
          <Link
            href="/connect"
            className="pulse-ring h-40 w-40 rounded-full bg-gradient-to-br from-primary to-secondary shadow-glow
                       flex flex-col items-center justify-center text-center font-bold text-lg active:scale-95 transition"
          >
            <span className="text-3xl mb-1">🚀</span>
            VPN'ni
            <br />
            ulash
          </Link>
        ) : (
          <Link
            href="/plans"
            className="h-40 w-40 rounded-full bg-gradient-to-br from-primary to-secondary shadow-glow
                       flex flex-col items-center justify-center text-center font-bold text-lg active:scale-95 transition"
          >
            <span className="text-3xl mb-1">💎</span>
            Tarif sotib
            <br />
            olish
          </Link>
        )}
      </section>

      <Link href="/servers" className="card flex items-center justify-between">
        <div>
          <p className="text-sm text-muted">Server lokatsiyalari</p>
          <p className="font-medium">Barcha serverlarni ko'rish</p>
        </div>
        <span className="text-muted">›</span>
      </Link>
    </div>
  );
}
