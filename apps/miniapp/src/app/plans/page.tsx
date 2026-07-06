"use client";

import { useEffect, useState } from "react";
import { apiFetch, apiPublic } from "@/lib/api";
import { openExternal } from "@/lib/telegram";

interface Plan {
  id: number;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  duration_days: number;
  traffic_limit_gb: number;
  device_hint: number;
  discount_percent: number;
  is_popular: boolean;
}

export default function Plans() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [buying, setBuying] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiPublic<Plan[]>("/plans").then(setPlans).catch((e) => setError(e.message));
  }, []);

  async function buy(plan: Plan) {
    setBuying(plan.id);
    setError(null);
    try {
      const payment = await apiFetch<{ invoice_url: string }>("/payments/create", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }), // provider = backend default (YooKassa)
      });
      if (payment.invoice_url) openExternal(payment.invoice_url);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBuying(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">💎 Tariflar</h1>
      <p className="text-sm text-muted -mt-2">
        To'lov bank kartasi orqali (Sber, Mir, SBP va boshqalar). To'lov tasdiqlangach
        obuna avtomatik faollashadi.
      </p>

      {error && <div className="card border-danger/40 text-danger text-sm">{error}</div>}

      {!plans && !error && (
        <>
          <div className="skeleton h-32" />
          <div className="skeleton h-32" />
        </>
      )}

      {plans?.map((plan) => (
        <div
          key={plan.id}
          className={`card relative ${plan.is_popular ? "border-primary/60 shadow-glow" : ""}`}
        >
          {plan.is_popular && (
            <span className="absolute -top-2.5 right-4 text-[11px] font-bold bg-gradient-to-r from-primary to-secondary px-2.5 py-0.5 rounded-full">
              ENG MASHHUR
            </span>
          )}
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-lg">{plan.name}</h2>
              <p className="text-sm text-muted">{plan.description}</p>
            </div>
            <div className="text-right">
              <p className="font-bold text-lg">
                {parseFloat(plan.price)}{" "}
                <span className="text-sm">{plan.currency === "RUB" ? "₽" : plan.currency}</span>
              </p>
              {plan.discount_percent > 0 && (
                <p className="text-xs text-success">-{plan.discount_percent}% chegirma</p>
              )}
            </div>
          </div>
          <ul className="mt-3 text-sm text-muted space-y-1">
            <li>⏳ {plan.duration_days} kun</li>
            <li>📶 Trafik: {plan.traffic_limit_gb > 0 ? `${plan.traffic_limit_gb} GB` : "cheksiz"}</li>
            <li>📱 {plan.device_hint} qurilmagacha tavsiya etiladi</li>
          </ul>
          <button className="btn-primary mt-4" disabled={buying === plan.id} onClick={() => buy(plan)}>
            {buying === plan.id ? "Invoice yaratilmoqda…" : "Sotib olish"}
          </button>
        </div>
      ))}
    </div>
  );
}
