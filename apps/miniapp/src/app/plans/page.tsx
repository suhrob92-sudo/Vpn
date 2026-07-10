"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiPublic } from "@/lib/api";
import { openExternal, openInvoice } from "@/lib/telegram";

interface Plan {
  id: number;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  price_stars: number;
  duration_days: number;
  traffic_limit_gb: number;
  device_hint: number;
  discount_percent: number;
  is_popular: boolean;
}

export default function Plans() {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [balance, setBalance] = useState(0);
  const [buying, setBuying] = useState<string | null>(null); // `${id}:${method}`
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiPublic<Plan[]>("/plans").then(setPlans).catch((e) => setError(e.message));
    apiFetch<{ balance: string }>("/users/me")
      .then((d) => setBalance(parseFloat(d.balance ?? "0")))
      .catch(() => {});
  }, []);

  async function buyBalance(plan: Plan) {
    if (!confirm(`${plan.name} tarifini balansdan (${parseFloat(plan.price)} ₽) sotib olasizmi?`)) return;
    setBuying(`${plan.id}:balance`);
    setError(null);
    try {
      await apiFetch("/payments/balance/pay", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }),
      });
      router.push("/payment/success");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBuying(null);
    }
  }

  async function buyCard(plan: Plan) {
    setBuying(`${plan.id}:card`);
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

  async function buyStars(plan: Plan) {
    setBuying(`${plan.id}:stars`);
    setError(null);
    try {
      const { invoice_link } = await apiFetch<{ invoice_link: string }>("/payments/stars/create", {
        method: "POST",
        body: JSON.stringify({ plan_id: plan.id }),
      });
      const status = await openInvoice(invoice_link);
      if (status === "paid") router.push("/payment/success");
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
        To'lovni bank kartasi (Sber, Mir, СБП) yoki Telegram Stars orqali amalga oshiring.
        To'lov tasdiqlangach obuna avtomatik faollashadi.
      </p>

      {balance > 0 && (
        <div className="card flex items-center justify-between">
          <p className="text-sm text-muted">💰 Balansingiz</p>
          <p className="font-bold">{balance} ₽</p>
        </div>
      )}

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
          <div className="mt-4 flex flex-col gap-2">
            <button
              className="btn-primary"
              disabled={buying === `${plan.id}:card`}
              onClick={() => buyCard(plan)}
            >
              {buying === `${plan.id}:card`
                ? "Ochilmoqda…"
                : `💳 Karta bilan · ${parseFloat(plan.price)} ${plan.currency === "RUB" ? "₽" : plan.currency}`}
            </button>
            {plan.price_stars > 0 && (
              <button
                className="btn-ghost"
                disabled={buying === `${plan.id}:stars`}
                onClick={() => buyStars(plan)}
              >
                {buying === `${plan.id}:stars`
                  ? "Ochilmoqda…"
                  : `⭐ Telegram Stars · ${plan.price_stars}`}
              </button>
            )}
            {balance >= parseFloat(plan.price) && (
              <button
                className="btn-ghost"
                disabled={buying === `${plan.id}:balance`}
                onClick={() => buyBalance(plan)}
              >
                {buying === `${plan.id}:balance`
                  ? "To'lanmoqda…"
                  : `💰 Balansdan · ${parseFloat(plan.price)} ₽`}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
