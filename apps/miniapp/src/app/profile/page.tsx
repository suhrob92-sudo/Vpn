"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { getTgUser } from "@/lib/telegram";

interface Sub {
  status: string;
  started_at: string;
  expires_at: string;
  plan: { name: string; device_hint: number; traffic_limit_gb: number };
}

export default function Profile() {
  const [sub, setSub] = useState<Sub | null | undefined>(undefined);
  const [renewing, setRenewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const user = typeof window !== "undefined" ? getTgUser() : null;

  useEffect(() => {
    apiFetch<Sub | null>("/subscriptions/me").then(setSub).catch((e) => setError(e.message));
  }, []);

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
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">👤 Profil</h1>

      <section className="card flex items-center gap-4">
        <div className="h-14 w-14 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-xl font-bold">
          {user?.first_name?.[0] ?? "?"}
        </div>
        <div>
          <p className="font-semibold">
            {user?.first_name} {user?.last_name ?? ""}
          </p>
          {user?.username && <p className="text-sm text-muted">@{user.username}</p>}
          <p className="text-xs text-muted">ID: {user?.id}</p>
        </div>
      </section>

      {error && <div className="card border-danger/40 text-danger text-sm">{error}</div>}
      {sub === undefined && !error && <div className="skeleton h-36" />}

      {sub !== undefined && (
        <section className="card">
          <h2 className="font-semibold mb-2">Obuna</h2>
          {sub && active ? (
            <div className="text-sm text-muted space-y-1">
              <p>
                Tarif: <span className="text-txt">{sub.plan.name}</span>
              </p>
              <p>
                Holat: <span className="text-success font-medium">FAOL</span>
              </p>
              <p>
                Boshlangan: <span className="text-txt">{new Date(sub.started_at).toLocaleDateString("uz-UZ")}</span>
              </p>
              <p>
                Tugaydi:{" "}
                <span className="text-txt">
                  {new Date(sub.expires_at).toLocaleDateString("uz-UZ")} ({daysLeft} kun qoldi)
                </span>
              </p>
              <p>
                Trafik limiti:{" "}
                <span className="text-txt">
                  {sub.plan.traffic_limit_gb > 0 ? `${sub.plan.traffic_limit_gb} GB` : "cheksiz"}
                </span>
              </p>
              <p>
                Qurilmalar: <span className="text-txt">{sub.plan.device_hint} tagacha tavsiya etiladi</span>
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted">Faol obuna yo'q.</p>
          )}
        </section>
      )}

      <div className="flex flex-col gap-3">
        {active && (
          <button className="btn-primary" onClick={renew} disabled={renewing}>
            {renewing ? "Invoice yaratilmoqda…" : "♻️ Obunani uzaytirish"}
          </button>
        )}
        <Link href="/connect" className="btn-ghost">
          🚀 VPN'ni qayta ulash
        </Link>
        {!active && (
          <Link href="/plans" className="btn-primary">
            💎 Tarif sotib olish
          </Link>
        )}
      </div>
    </div>
  );
}
